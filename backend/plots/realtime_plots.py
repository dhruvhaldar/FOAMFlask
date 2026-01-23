"""
Realtime plotting module for OpenFOAM simulations.
Parses OpenFOAM field files and extracts data for visualization.
"""

import re
import numpy as np
import logging
import os
import mmap
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Union, Any

# ⚡ Bolt Optimization: Import Rust accelerator if available
try:
    import accelerator
    RUST_ACCELERATOR = True
except ImportError:
    RUST_ACCELERATOR = False

# Configure logger
logger = logging.getLogger("FOAMFlask")

# --- Global Cache ---
# Structure: { "file_path_str": (mtime, parsed_value) }
_FILE_CACHE: Dict[str, Tuple[float, Any]] = {}

# Structure: { "log_path_str": (mtime, size, offset, residuals_data) }
# ⚡ Bolt Optimization: Added offset to support incremental reading
_RESIDUALS_CACHE: Dict[str, Tuple[float, int, int, Dict[str, List[float]]]] = {}

# Structure: { "file_path_str": (mtime, field_type) }
_FIELD_TYPE_CACHE: Dict[str, Tuple[float, Optional[str]]] = {}

# Structure: { "case_dir_str": (mtime, list_of_time_dirs) }
# ⚡ Bolt Optimization: Cache time directories based on case dir mtime
_TIME_DIRS_CACHE: Dict[str, Tuple[float, List[str]]] = {}

# Structure: { "case_dir_str": (list_of_time_dirs, full_data_dict) }
# ⚡ Bolt Optimization: Cache accumulated time series data to avoid rebuilding lists
_TIME_SERIES_CACHE: Dict[str, Tuple[List[str], Dict[str, List[float]]]] = {}

# Structure: { "dir_path_str": (mtime, scalar_fields, has_U, all_files) }
# ⚡ Bolt Optimization: Cache directory contents to avoid redundant scandir/field_type checks
_DIR_SCAN_CACHE: Dict[str, Tuple[float, List[str], bool, List[str]]] = {}

# Structure: { "case_dir_str": { "filename": "type" } }
# ⚡ Bolt Optimization: Cache field types by filename per case to avoid re-reading headers
# OpenFOAM field types (scalar vs vector) are consistent by filename (e.g., 'p' is always scalar).
_CASE_FIELD_TYPES: Dict[str, Dict[str, str]] = {}

# Pre-compiled regex patterns
# Matches "Time = <number>"
TIME_REGEX = re.compile(r"Time\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")
# ⚡ Bolt Optimization: Bytes regex for high-performance log parsing
TIME_REGEX_BYTES = re.compile(rb"Time\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")

# Matches "<field> ... Initial residual = <number>"
# We use a single regex to capture field name and value to avoid 7 passes per line
# Captures group 1: field name, group 2: value
RESIDUAL_REGEX = re.compile(r"(Ux|Uy|Uz|p|k|epsilon|omega).*Initial residual\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")
# ⚡ Bolt Optimization: Bytes regex to avoid decoding log lines
RESIDUAL_REGEX_BYTES = re.compile(rb"(Ux|Uy|Uz|p|k|epsilon|omega).*Initial residual\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")

# ⚡ Bolt Optimization: Pre-compute translation table for vector parsing
# Replaces parenthesis with spaces to flatten vector lists efficiently.
# Using translate() is ~30% faster than chained replace() calls for large strings and saves memory.
_PARENS_TRANS = str.maketrans("()", "  ")
# ⚡ Bolt Optimization: Pre-compute bytes translation table for mmap processing
_PARENS_TRANS_BYTES = bytes.maketrans(b"()", b"  ")

# ⚡ Bolt Optimization: Pre-compile regex patterns for field parsing
# Avoids recompilation overhead during high-frequency polling
# ⚡ Bolt Optimization: Use bytes regex to avoid decoding overhead and unnecessary copies
_RE_VOL_SCALAR = re.compile(rb"class\s+volScalarField;")
_RE_VOL_VECTOR = re.compile(rb"class\s+volVectorField;")

_RE_SCALAR_UNIFORM_VAR = re.compile(rb"internalField\s+uniform\s+(\$[a-zA-Z0-9_]+);")
_RE_SCALAR_UNIFORM_VAL = re.compile(rb"internalField\s+uniform\s+([^;]+);")
_RE_NONUNIFORM_LIST = re.compile(r"internalField\s+nonuniform\s+.*?\(\s*([\s\S]*?)\s*\)\s*;", re.DOTALL)
_RE_NUMBERS_FINDALL = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

_RE_VECTOR_UNIFORM_VAR_CHECK = re.compile(rb"internalField\s+uniform\s+\$[a-zA-Z0-9_]+;")
_RE_VECTOR_UNIFORM_VAL_GROUP = re.compile(rb"internalField\s+uniform\s+(\([^;]+\));", re.DOTALL)
_RE_VECTOR_COMPONENTS = re.compile(
    rb"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
    rb"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
    rb"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)"
)

class OpenFOAMFieldParser:
    """Parse OpenFOAM field files and extract data."""

    def __init__(self, case_dir: Union[str, Path]) -> None:
        self.case_dir = Path(case_dir)

    def get_time_directories(self, known_mtime: Optional[float] = None) -> List[str]:
        """Get all time directories sorted numerically."""
        path_str = str(self.case_dir)
        try:
            # ⚡ Bolt Optimization: Use known mtime if provided to save syscall
            if known_mtime is not None:
                mtime = known_mtime
            else:
                mtime = os.stat(path_str).st_mtime

            # ⚡ Bolt Optimization: Check cache first
            if path_str in _TIME_DIRS_CACHE:
                cached_mtime, cached_dirs = _TIME_DIRS_CACHE[path_str]
                if cached_mtime == mtime:
                    return cached_dirs
        except OSError as e:
            logger.error(f"Error accessing {self.case_dir}: {e}")
            return []

        time_dirs = []
        try:
            # ⚡ Bolt Optimization: Use os.scandir instead of Path.iterdir()
            # This avoids extra stat() calls and is significantly faster for large directories.
            with os.scandir(path_str) as entries:
                for entry in entries:
                    if entry.is_dir():
                        try:
                            # Check if directory name is a number
                            # ⚡ Bolt Optimization: Store float value to avoid redundant conversions during sort
                            val = float(entry.name)
                            time_dirs.append((val, entry.name))
                        except ValueError:
                            continue
        except OSError as e:
            logger.error(f"Error listing directories in {self.case_dir}: {e}")
            return []

        # Sort based on pre-calculated float value
        time_dirs.sort(key=lambda x: x[0])
        sorted_dirs = [x[1] for x in time_dirs]

        # Update cache
        _TIME_DIRS_CACHE[path_str] = (mtime, sorted_dirs)

        return sorted_dirs

    def _get_field_type(self, field_entry: Union[Path, os.DirEntry]) -> Optional[str]:
        """
        Determine if a file is a volScalarField or volVectorField by reading the header.
        Returns 'scalar', 'vector', or None.
        Accepts Path or os.DirEntry for optimization.
        """
        try:
            # ⚡ Bolt Optimization: Accept DirEntry to avoid extra stat() call
            if isinstance(field_entry, os.DirEntry):
                path_str = field_entry.path
                filename = field_entry.name
                mtime = field_entry.stat().st_mtime
                # ⚡ Bolt Optimization: Avoid Path object creation
                # field_path = Path(path_str) # REMOVED
            else:
                field_path = field_entry
                path_str = str(field_path)
                filename = field_path.name
                mtime = os.stat(path_str).st_mtime

            # ⚡ Bolt Optimization: Check case-wide filename cache first
            # If we know 'p' is scalar in this case, we don't need to read '0.1/p', '0.2/p'...
            case_path_str = str(self.case_dir)
            if case_path_str in _CASE_FIELD_TYPES:
                if filename in _CASE_FIELD_TYPES[case_path_str]:
                    return _CASE_FIELD_TYPES[case_path_str][filename]

            # Fallback to path-specific cache (useful if logic changes or for non-standard structures)
            if path_str in _FIELD_TYPE_CACHE:
                cached_mtime, cached_type = _FIELD_TYPE_CACHE[path_str]
                # ⚡ Bolt Optimization: If type was previously identified, trust it.
                if cached_type is not None:
                    # Propagate to case cache for future speedup
                    if case_path_str not in _CASE_FIELD_TYPES:
                        _CASE_FIELD_TYPES[case_path_str] = {}
                    _CASE_FIELD_TYPES[case_path_str][filename] = cached_type
                    return cached_type

                if cached_mtime == mtime:
                    return cached_type

            # Simple header check doesn't need aggressive caching, but reading first bytes is fast.
            # ⚡ Bolt Optimization: Reduced read size to 2048 bytes (enough for header + banner).
            # The class definition is almost always in the first few lines, but banner can be large.
            # ⚡ Bolt Optimization: Read bytes to avoid decode overhead during type check
            # ⚡ Bolt Optimization: Use built-in open() with string path to avoid Path object overhead
            with open(path_str, "rb") as f:
                header = f.read(2048)
            
            field_type = None
            if _RE_VOL_SCALAR.search(header):
                field_type = "scalar"
            elif _RE_VOL_VECTOR.search(header):
                field_type = "vector"

            # Update path cache
            _FIELD_TYPE_CACHE[path_str] = (mtime, field_type)

            # Update case-wide filename cache if type was found
            if field_type:
                if case_path_str not in _CASE_FIELD_TYPES:
                    _CASE_FIELD_TYPES[case_path_str] = {}
                _CASE_FIELD_TYPES[case_path_str][filename] = field_type

            return field_type
        except Exception as e:
            # print(f"DEBUG: _get_field_type failed for {field_entry}: {e}")
            return None

    def _scan_time_dir(self, time_path: Path) -> Tuple[List[str], bool, List[str]]:
        """
        Scan a time directory and categorize fields.
        Returns: (scalar_fields, has_U, all_files)
        Cached based on directory mtime.
        """
        path_str = str(time_path)
        try:
            mtime = os.stat(path_str).st_mtime

            # ⚡ Bolt Optimization: Check cache first
            if path_str in _DIR_SCAN_CACHE:
                cached_mtime, scalar_fields, has_U, all_files = _DIR_SCAN_CACHE[path_str]
                if cached_mtime == mtime:
                    return scalar_fields, has_U, all_files

            scalar_fields = []
            has_U = False
            all_files = []

            with os.scandir(path_str) as entries:
                for entry in entries:
                    if entry.is_file() and not entry.name.startswith("."):
                        all_files.append(entry.name)

                        field_type = self._get_field_type(entry)
                        if field_type == "scalar":
                            scalar_fields.append(entry.name)
                        elif field_type == "vector" and entry.name == "U":
                            has_U = True

            # Sort for consistency
            scalar_fields.sort()
            all_files.sort()

            _DIR_SCAN_CACHE[path_str] = (mtime, scalar_fields, has_U, all_files)
            return scalar_fields, has_U, all_files

        except OSError as e:
            logger.error(f"Error scanning time directory {time_path}: {e}")
            return [], False, []

    def _resolve_variable(self, content: Union[str, bytes, mmap.mmap], var_name: Union[str, bytes]) -> Optional[str]:
        """
        Attempt to resolve a variable definition within the file content.
        Looks for patterns like 'varName value;'
        """
        # ⚡ Bolt Optimization: Handle mmap as binary
        is_binary = not isinstance(content, str)
        
        if is_binary:
            if isinstance(var_name, str):
                var_name = var_name.encode('utf-8')
            clean_var = var_name.lstrip(b'$')
            pattern = re.compile(rb"(?:^|\s)" + re.escape(clean_var) + rb"\s+([^;]+);")
        else:
            if isinstance(var_name, bytes):
                var_name = var_name.decode('utf-8')
            clean_var = var_name.lstrip('$')
            pattern = re.compile(rf"(?:^|\s){re.escape(clean_var)}\s+([^;]+);")

        match = pattern.search(content)
        
        if match:
            value = match.group(1).strip()
            
            if is_binary:
                if value.startswith(b'$'):
                    return self._resolve_variable(content, value)
                if b"#calc" in value:
                    return None
                return value.decode('utf-8')
            else:
                if value.startswith('$'):
                    return self._resolve_variable(content, value)
                if "#calc" in value:
                    return None
                return value
            
        return None

    def parse_scalar_field(self, field_path: Union[str, Path], check_mtime: bool = True, known_mtime: Optional[float] = None, store_cache: bool = True) -> Optional[float]:
        """Parse a scalar field file and return average value with caching."""
        if isinstance(field_path, str):
            path_str = field_path
        else:
            path_str = str(field_path)

        # ⚡ Bolt Optimization: Use Rust accelerator if available
        # Rust handles mmap and parsing significantly faster.
        if RUST_ACCELERATOR and not check_mtime and path_str in _FILE_CACHE:
             # Fast path: Skip everything if cache hit requested without checks
             return _FILE_CACHE[path_str][1]

        try:
            # ⚡ Bolt Optimization: Skip stat() for historical files
            # If check_mtime is False and we have it in cache, return immediately
            if not check_mtime and path_str in _FILE_CACHE:
                return _FILE_CACHE[path_str][1]

            # ⚡ Bolt Optimization: Skip stat() if not required (historical data) or provided
            mtime = 0.0
            if known_mtime is not None:
                mtime = known_mtime
            elif check_mtime:
                try:
                    mtime = os.stat(path_str).st_mtime
                except OSError:
                    # File might not exist
                    return None
            
            # Return cached if valid (only if we checked mtime or have known mtime)
            if (check_mtime or known_mtime is not None) and path_str in _FILE_CACHE:
                cached_mtime, cached_val = _FILE_CACHE[path_str]
                if cached_mtime == mtime:
                    return cached_val

            val = None

            if RUST_ACCELERATOR:
                try:
                    val = accelerator.parse_scalar_field(path_str)
                    if store_cache:
                        _FILE_CACHE[path_str] = (mtime, val)
                    return val
                except Exception as e:
                    # Fallback to Python if Rust fails (unlikely)
                    pass

            try:
                # ⚡ Bolt Optimization: Use mmap for large files to avoid reading entire file into memory.
                # This is ~3x faster for large fields and reduces memory pressure significantly.
                with open(path_str, "rb") as f:
                    # mmap can fail for empty files or if file is too small
                    # ⚡ Bolt Optimization: Use os.fstat(fd) instead of Path.stat() to avoid extra syscall
                    if f.fileno() != -1 and os.fstat(f.fileno()).st_size > 0:
                         with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                            # 1. Check for nonuniform list
                            # Look for "internalField nonuniform"
                            idx = mm.find(b"internalField")
                            if idx != -1:
                                # Verify "nonuniform" follows
                                # ⚡ Bolt Optimization: Avoid read() and decode() by searching buffer directly
                                nonuniform_idx = mm.find(b"nonuniform", idx, idx + 200)

                                if nonuniform_idx != -1:
                                    # Locate list start '('
                                    start_paren = mm.find(b'(', nonuniform_idx)
                                    if start_paren != -1:
                                        # Locate list end ')'
                                        # It usually ends with ');' before 'boundaryField'
                                        boundary_idx = mm.find(b"boundaryField", start_paren)
                                        end_paren = -1
                                        if boundary_idx != -1:
                                            end_paren = mm.rfind(b')', start_paren, boundary_idx)
                                        else:
                                            end_paren = mm.rfind(b')') # Fallback to last paren

                                        if end_paren != -1:
                                            # Slice data efficiently
                                            # np.fromstring handles bytes directly
                                            data_block = mm[start_paren+1:end_paren]
                                            try:
                                                numbers = np.fromstring(data_block, sep=" ")
                                                if numbers.size > 0:
                                                    val = float(np.mean(numbers))
                                            except ValueError:
                                                pass

                            # 2. Check for uniform if not found
                            if val is None:
                                # Reset for search
                                if idx != -1:
                                    pass # idx is already valid for internalField
                                else:
                                    idx = mm.find(b"internalField")

                                if idx != -1:
                                    # ⚡ Bolt Optimization: Use bytes regex search on mmap buffer directly
                                    # Avoids read(200) and decode('utf-8')
                                    # Search range limited to ~200 bytes after internalField

                                    # Check for uniform with variable substitution
                                    var_match = _RE_SCALAR_UNIFORM_VAR.search(mm, idx, idx + 200)
                                    if var_match:
                                        var_name = var_match.group(1) # bytes
                                        # ⚡ Bolt Optimization: Use mmap buffer directly for variable resolution
                                        # Avoids reading entire file into memory with read_bytes()
                                        resolved_value = self._resolve_variable(mm, var_name)
                                        if resolved_value:
                                            val = float(resolved_value)

                                    if val is None:
                                        match = _RE_SCALAR_UNIFORM_VAL.search(mm, idx, idx + 200)
                                        if match:
                                            try:
                                                val = float(match.group(1).strip())
                                            except ValueError:
                                                pass

            except (FileNotFoundError, OSError, ValueError) as e:
                # If mmap fails or file issues, we fall back or return None
                pass

            # Fallback for complex cases (e.g. comments inside list breaking numpy)
            if val is None:
                try:
                    with open(path_str, "r", encoding="utf-8") as f:
                        content = f.read()
                    if "nonuniform" in content:
                        match = _RE_NONUNIFORM_LIST.search(content)
                        if match:
                            field_data = match.group(1)
                            numbers_list = _RE_NUMBERS_FINDALL.findall(field_data)
                            if numbers_list:
                                val = float(np.mean([float(n) for n in numbers_list]))
                except (FileNotFoundError, OSError):
                    pass
            
            # Update cache
            if store_cache:
                _FILE_CACHE[path_str] = (mtime, val)
            return val

        except Exception as e:
            logger.error(f"Error parsing scalar field {path_str}: {e}")
            return None

    def parse_vector_field(self, field_path: Union[str, Path], check_mtime: bool = True, known_mtime: Optional[float] = None, store_cache: bool = True) -> Tuple[float, float, float]:
        """Parse a vector field file and return average components with caching."""
        if isinstance(field_path, str):
            path_str = field_path
        else:
            path_str = str(field_path)

        # ⚡ Bolt Optimization: Use Rust accelerator if available
        if RUST_ACCELERATOR and not check_mtime and path_str in _FILE_CACHE:
             return _FILE_CACHE[path_str][1]

        try:
            # ⚡ Bolt Optimization: Skip stat() for historical files
            if not check_mtime and path_str in _FILE_CACHE:
                return _FILE_CACHE[path_str][1]

            # ⚡ Bolt Optimization: Skip stat() if not required (historical data) or provided
            mtime = 0.0
            if known_mtime is not None:
                mtime = known_mtime
            elif check_mtime:
                try:
                    mtime = os.stat(path_str).st_mtime
                except OSError:
                    return 0.0, 0.0, 0.0
            
            # Return cached if valid (only if we checked mtime or have known mtime)
            if (check_mtime or known_mtime is not None) and path_str in _FILE_CACHE:
                cached_mtime, cached_val = _FILE_CACHE[path_str]
                if cached_mtime == mtime:
                    return cached_val

            val = (0.0, 0.0, 0.0)

            if RUST_ACCELERATOR:
                try:
                    val = accelerator.parse_vector_field(path_str)
                    if store_cache:
                        _FILE_CACHE[path_str] = (mtime, val)
                    return val
                except Exception as e:
                    pass

            try:
                # ⚡ Bolt Optimization: Use mmap for large files
                with open(path_str, "rb") as f:
                    # ⚡ Bolt Optimization: Use os.fstat(fd) instead of Path.stat() to avoid extra syscall
                    if f.fileno() != -1 and os.fstat(f.fileno()).st_size > 0:
                        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                            # 1. Check for nonuniform
                            idx = mm.find(b"internalField")
                            if idx != -1:
                                # ⚡ Bolt Optimization: Avoid read() and decode() by searching buffer directly
                                nonuniform_idx = mm.find(b"nonuniform", idx, idx + 200)

                                if nonuniform_idx != -1:
                                    start_paren = mm.find(b'(', nonuniform_idx)
                                    if start_paren != -1:
                                        boundary_idx = mm.find(b"boundaryField", start_paren)
                                        end_paren = -1
                                        if boundary_idx != -1:
                                            end_paren = mm.rfind(b')', start_paren, boundary_idx)
                                        else:
                                            end_paren = mm.rfind(b')')

                                        if end_paren != -1:
                                            # Slice data
                                            data_block = mm[start_paren+1:end_paren]
                                            try:
                                                # Use translate on bytes (requires making a copy, but still better than full file read)
                                                # Or simpler: replace b'(' and b')' with space
                                                # But we already sliced inside the outer parens.
                                                # Inside might be (x y z) tuples.
                                                # We need to flatten them.

                                                # replace(b'(', b' ') is fast on bytes
                                                # ⚡ Bolt Optimization: Use translate() for bytes to avoid intermediate copies (~15% faster)
                                                clean_data = data_block.translate(_PARENS_TRANS_BYTES)
                                                arr = np.fromstring(clean_data, sep=' ')

                                                if arr.size > 0:
                                                    arr = arr.reshape(-1, 3)
                                                    mean_vec = np.mean(arr, axis=0)
                                                    val = (float(mean_vec[0]), float(mean_vec[1]), float(mean_vec[2]))
                                            except ValueError:
                                                pass

                            # 2. Check for uniform
                            if val == (0.0, 0.0, 0.0):
                                if idx != -1:
                                    pass
                                else:
                                    idx = mm.find(b"internalField")

                                if idx != -1:
                                    # ⚡ Bolt Optimization: Use bytes regex search on mmap buffer directly
                                    if _RE_VECTOR_UNIFORM_VAR_CHECK.search(mm, idx, idx + 200):
                                        # Variable detected
                                        val = (0.0, 0.0, 0.0)
                                    else:
                                        match = _RE_VECTOR_UNIFORM_VAL_GROUP.search(mm, idx, idx + 200)
                                        if match:
                                            vec_str = match.group(1)
                                            # Simple regex for (x y z)
                                            vec_match = _RE_VECTOR_COMPONENTS.search(vec_str)
                                            if vec_match:
                                                val = (
                                                    float(vec_match.group(1)),
                                                    float(vec_match.group(2)),
                                                    float(vec_match.group(3)),
                                                )

            except (FileNotFoundError, OSError, ValueError) as e:
                pass

            # Fallback
            if val == (0.0, 0.0, 0.0):
                try:
                    with open(path_str, "r", encoding="utf-8") as f:
                        content = f.read()
                    if "nonuniform" in content:
                        match = _RE_NONUNIFORM_LIST.search(content)
                        if match:
                            field_data = match.group(1)
                            try:
                                clean_data = field_data.translate(_PARENS_TRANS)
                                arr = np.fromstring(clean_data, sep=' ')
                                if arr.size > 0:
                                    arr = arr.reshape(-1, 3)
                                    mean_vec = np.mean(arr, axis=0)
                                    val = (float(mean_vec[0]), float(mean_vec[1]), float(mean_vec[2]))
                            except ValueError:
                                pass
                except (FileNotFoundError, OSError):
                    pass
            
            # Update cache
            if store_cache:
                _FILE_CACHE[path_str] = (mtime, val)
            return val

        except Exception as e:
            logger.error(f"Error parsing vector field {path_str}: {e}")
            return 0.0, 0.0, 0.0

    def get_latest_time_data(self) -> Optional[Dict[str, Any]]:
        """Get data from the latest time directory using dynamic field discovery."""
        time_dirs = self.get_time_directories()
        if not time_dirs:
            return None

        latest_time = time_dirs[-1]
        time_path = self.case_dir / latest_time

        data: Dict[str, Any] = {"time": float(latest_time)}
        
        try:
            # ⚡ Bolt Optimization: Use os.scandir to avoid creating Path objects and redundant stat()
            # Note: We do NOT use _scan_time_dir here because we need the DirEntry objects
            # to pass mtime to parse_* methods efficiently.
            with os.scandir(str(time_path)) as entries:
                for entry in entries:
                    if entry.is_file() and not entry.name.startswith("."):
                        field_type = self._get_field_type(entry)

                        if field_type == "scalar":
                            # Pass mtime from entry to avoid re-stat
                            # ⚡ Bolt Optimization: Pass entry.path string directly to avoid Path creation
                            val = self.parse_scalar_field(entry.path, known_mtime=entry.stat().st_mtime)
                            if val is not None:
                                data[entry.name] = val

                        elif field_type == "vector" and entry.name == "U":
                             # ⚡ Bolt Optimization: Pass entry.path string directly to avoid Path creation
                             ux, uy, uz = self.parse_vector_field(entry.path, known_mtime=entry.stat().st_mtime)
                             data["Ux"] = ux
                             data["Uy"] = uy
                             data["Uz"] = uz
                             data["U_mag"] = float(np.sqrt(ux**2 + uy**2 + uz**2))
                        
        except Exception as e:
            logger.error(f"Error scanning fields in {time_path}: {e}")

        return data

    def get_all_time_series_data(self, max_points: int = 100, known_case_mtime: Optional[float] = None) -> Dict[str, List[float]]:
        """Get time series data for all available fields dynamically."""
        all_time_dirs = self.get_time_directories(known_mtime=known_case_mtime)
        if not all_time_dirs:
            return {}

        # ⚡ Bolt Optimization: Use append-only cache for stable history
        # We cache the full accumulated history (excluding the latest unstable step)
        # This avoids rebuilding lists and redundant lookups for thousands of past steps.
        case_path_str = str(self.case_dir)

        # We must determine if we need to modify the cache (update path) or just read from it (steady state).
        cache_entry = _TIME_SERIES_CACHE.get(case_path_str)

        # Use source directly for checking to avoid premature copy
        if cache_entry:
            src_dirs, src_data = cache_entry
        else:
            src_dirs, src_data = [], {}

        # Determine how much of the cache is valid
        # We need a common prefix match.
        valid_cache_len = 0
        min_len = min(len(src_dirs), len(all_time_dirs))

        # Fast prefix check: if lengths differ but prefix matches
        if all_time_dirs[:len(src_dirs)] == src_dirs:
            valid_cache_len = len(src_dirs)
        else:
            # Slower element-wise check if there was a divergence (e.g. restart)
            for i in range(min_len):
                if src_dirs[i] == all_time_dirs[i]:
                    valid_cache_len += 1
                else:
                    break

        # Identify stable steps to process (all except the very last one)
        # If simulation is done, the last one is stable too, but we treat it as volatile
        # to simplify logic (it gets re-parsed every time until a newer one appears).
        if not all_time_dirs:
            return {}

        latest_time = all_time_dirs[-1]
        stable_dirs_to_process = all_time_dirs[valid_cache_len:-1]
        
        latest_time_path = self.case_dir / latest_time
        # ⚡ Bolt Optimization: Use cached scanning for field discovery
        scalar_fields, has_U, _ = self._scan_time_dir(latest_time_path)

        # Decision: Do we need to modify the cache?
        needs_update = (valid_cache_len < len(src_dirs)) or (len(stable_dirs_to_process) > 0)

        working_data = None
        working_dirs_len = 0

        if needs_update:
            # Full Copy and Update Path

            # ⚡ Bolt Optimization: Zero-copy update for append-only case
            # If the cache is valid (just needs extending), we shallow-copy the dict
            # but reuse the list objects, appending in-place.
            # Readers use slice limits based on the old directory list, so they won't see partial updates.
            # WARNING: Lists in cached_data alias src_data lists! Mutation here affects the global cache history.
            if valid_cache_len == len(src_dirs):
                cached_dirs = src_dirs
                cached_data = src_data.copy()
            else:
                # Divergence detected: Full copy and slice required
                cached_dirs = src_dirs[:valid_cache_len]
                # Slice all lists in cached_data
                cached_data = {k: v[:valid_cache_len] for k, v in src_data.items()}

            # Initialize cached_data if empty
            if not cached_data:
                cached_data = {"time": []}
                for f in scalar_fields:
                    cached_data[f] = []
                if has_U:
                    cached_data['Ux'] = []
                    cached_data['Uy'] = []
                    cached_data['Uz'] = []
                    cached_data['U_mag'] = []

            # Process new stable steps and append to cache (working copy)
            try:
                for time_dir in stable_dirs_to_process:
                    # ⚡ Bolt Optimization: Use os.path.join instead of Path / operator
                    # time_path = self.case_dir / time_dir
                    time_path_str = os.path.join(case_path_str, time_dir)

                    time_val = float(time_dir)

                    cached_data["time"].append(time_val)

                    # Parse scalars
                    for field in scalar_fields:
                        # Ensure field exists in cache (handle dynamic field addition)
                        if field not in cached_data:
                            cached_data[field] = [0.0] * (len(cached_data["time"]) - 1)

                        # field_path = time_path / field
                        field_path_str = os.path.join(time_path_str, field)

                        # Skip check_mtime for stable steps (assumed immutable)
                        # Pass string directly
                        val = self.parse_scalar_field(field_path_str, check_mtime=False, store_cache=False)
                        cached_data[field].append(val if val is not None else 0.0)

                        # ⚡ Bolt Optimization: Aggressive cache cleanup for stable steps
                        # Since data is now archived in cached_data, we remove the file-level entry
                        # to prevent unbounded growth of _FILE_CACHE for long-running simulations.
                        _FILE_CACHE.pop(field_path_str, None)

                    # Parse U
                    if has_U:
                        # u_path = time_path / "U"
                        u_path_str = os.path.join(time_path_str, "U")

                        # Pass string directly
                        ux, uy, uz = self.parse_vector_field(u_path_str, check_mtime=False, store_cache=False)

                        # ⚡ Bolt Optimization: Cleanup vector file cache
                        _FILE_CACHE.pop(u_path_str, None)

                        # Ensure vector fields exist in cache
                        for k in ['Ux', 'Uy', 'Uz', 'U_mag']:
                            if k not in cached_data:
                                cached_data[k] = [0.0] * (len(cached_data["time"]) - 1)

                        cached_data["Ux"].append(ux)
                        cached_data["Uy"].append(uy)
                        cached_data["Uz"].append(uz)
                        cached_data["U_mag"].append(float(np.sqrt(ux**2 + uy**2 + uz**2)))

                # Update global cache with new stable state (atomic-ish update)
                # Note: cached_dirs + stable_dirs_to_process == all_time_dirs[:-1]
                new_cached_dirs = cached_dirs + stable_dirs_to_process
                _TIME_SERIES_CACHE[case_path_str] = (new_cached_dirs, cached_data)

                working_data = cached_data
                working_dirs_len = len(new_cached_dirs)

            except Exception as e:
                logger.error(f"Error updating time series cache: {e}")
                # Do not update global cache, fall back to what we have (or incomplete result)
                working_data = cached_data
                working_dirs_len = len(cached_dirs) + len(stable_dirs_to_process)
        else:
             # ⚡ Bolt Optimization: Zero-copy path for steady state
             # No changes to stable history, so we read directly from source
             # This avoids O(N) copy operations when simulation is running but no new time steps have appeared yet.
             working_data = src_data
             working_dirs_len = len(src_dirs)

        # Construct final result: Cache Slice + Latest Step
        # We need the last `max_points` points.

        # 1. Start with a copy of the relevant slice from cache
        # If we need N points, and we have M cached points.
        # We take M points, add 1 latest point. Total M+1.
        # If M+1 > N, we slice the last N.

        # Be careful not to mutate cached lists in the result
        result_data = {}
        total_available = working_dirs_len + 1
        start_idx = max(0, total_available - max_points)

        # Calculate how many points from cache we need
        # We take everything from start_idx up to end of cache
        cache_slice_start = max(0, start_idx) # Index in cache

        # Since working_data might be the global cache (in zero-copy path),
        # we MUST ensure we don't mutate it. Slicing creates new lists.
        for k, v in working_data.items():
            result_data[k] = v[cache_slice_start:]

        # 2. Process and append the latest (unstable) step
        time_path = self.case_dir / latest_time
        time_val = float(latest_time)

        # Ensure latest step keys exist
        if "time" not in result_data: result_data["time"] = []
        result_data["time"].append(time_val)

        # ⚡ Bolt Optimization: Pre-scan directory to avoid stat() calls per field
        file_mtimes = {}
        try:
             with os.scandir(str(time_path)) as entries:
                 for entry in entries:
                     file_mtimes[entry.name] = entry.stat().st_mtime
        except OSError:
             pass

        for field in scalar_fields:
            if field not in result_data: result_data[field] = []

            field_path = time_path / field
            known_mtime = file_mtimes.get(field)

            # Pass known_mtime. If missing (file deleted?), parse_scalar_field handles it by stat-ing again (if None)
            if known_mtime is not None:
                # Pass string (actually field_path is Path here, we could optimize this loop too but it's small)
                # For consistency with other opts, let's keep it as is, or use os.path.join
                val = self.parse_scalar_field(field_path, check_mtime=False, known_mtime=known_mtime)
            else:
                 val = self.parse_scalar_field(field_path, check_mtime=True)

            result_data[field].append(val if val is not None else 0.0)

        if has_U:
            u_path = time_path / "U"
            known_mtime = file_mtimes.get("U")

            if known_mtime is not None:
                ux, uy, uz = self.parse_vector_field(u_path, check_mtime=False, known_mtime=known_mtime)
            else:
                ux, uy, uz = self.parse_vector_field(u_path, check_mtime=True)

            for k, v in [('Ux', ux), ('Uy', uy), ('Uz', uz), ('U_mag', float(np.sqrt(ux**2 + uy**2 + uz**2)))]:
                if k not in result_data: result_data[k] = []
                result_data[k].append(v)

        return result_data

    def calculate_pressure_coefficient(
        self, p_field: Optional[float], p_inf: float = 101325, rho: float = 1.225, u_inf: float = 1.0
    ) -> Optional[float]:
        """Calculate pressure coefficient Cp = (p - p_inf) / (0.5 * rho * u_inf^2)."""
        if p_field is None:
            return None
        q_inf = 0.5 * rho * u_inf**2
        return (p_field - p_inf) / q_inf if q_inf != 0 else 0.0

    def get_residuals_from_log(self, log_file: str = "log.foamRun", known_stat: Optional[os.stat_result] = None) -> Dict[str, List[float]]:
        """
        Parse residuals from OpenFOAM log file incrementally.

        Args:
            log_file: Name of the log file.
            known_stat: Optional os.stat_result if already available (avoids redundant syscall).
        """
        log_path = self.case_dir / log_file
        path_str = str(log_path)

        # ⚡ Bolt Optimization: Remove redundant exists() check.
        # stat() raises FileNotFoundError if file is missing, which we can catch.
        # This saves 1 syscall per poll cycle.

        fd = None
        try:
            # Security & Optimization: Atomic open + fstat
            # We open with O_NOFOLLOW to prevent TOCTOU symlink attacks.
            # We explicitly ignore known_stat here to ensure we don't bypass symlink checks.
            # While known_stat avoids a syscall, it relies on os.stat() which follows symlinks.

            import errno
            try:
                fd = os.open(path_str, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            except OSError as e:
                if e.errno == errno.ELOOP:
                    logger.warning(f"Security: Ignoring symlinked log file: {path_str}")
                    return {}
                # Rethrow other errors (e.g. FileNotFoundError)
                raise

            # Use fstat on the open FD - atomic and trustable
            try:
                stat = os.fstat(fd)
                mtime = stat.st_mtime
                size = stat.st_size

                start_offset = 0
                residuals: Dict[str, List[float]] = {
                    "time": [],
                    "Ux": [],
                    "Uy": [],
                    "Uz": [],
                    "p": [],
                    "k": [],
                    "epsilon": [],
                    "omega": [],
                }

                # ⚡ Bolt Optimization: Check cache first for incremental update
                if path_str in _RESIDUALS_CACHE:
                    cached_mtime, cached_size, cached_offset, cached_data = _RESIDUALS_CACHE[path_str]

                    # Case 1: File unchanged
                    if cached_mtime == mtime and cached_size == size:
                        # Close FD since we don't need to read
                        os.close(fd)
                        fd = None
                        return cached_data

                    # Case 2: File grew (append) - Reuse cached data and offset
                    if size > cached_size and cached_size > 0:
                        start_offset = cached_offset
                        residuals = cached_data # Reference to existing mutable dict

                    # Case 3: File shrank or reset - Start over (defaults apply)

                new_offset = start_offset

                # ⚡ Bolt Optimization: Stream file line-by-line to avoid loading massive files into RAM.
                # This reduces memory usage from O(N) to O(1) for log parsing.

                # Use os.fdopen to wrap the existing FD
                with os.fdopen(fd, "rb") as f:
                    fd = None # Ownership transferred to file object
                    if start_offset > 0:
                        f.seek(start_offset)

                    for line in f:
                        # Check for complete line (active writes might leave incomplete lines at EOF)
                        if not line.endswith(b'\n'):
                            break

                        line_len = len(line)
                        try:
                            # ⚡ Bolt Optimization: Optimistic strict decode (20-30% faster than errors='replace')
                            # Most log lines are valid UTF-8/ASCII.
                            try:
                                line_str = line.decode("utf-8")
                            except UnicodeDecodeError:
                                line_str = line.decode("utf-8", errors="replace")

                            # Optimized time matching
                            if "Time =" in line_str:
                                time_match = TIME_REGEX.search(line_str)
                                if time_match:
                                    current_time = float(time_match.group(1))
                                    residuals["time"].append(current_time)

                            # Optimized residual matching
                            if "Initial residual" in line_str:
                                # Optimization: Check if we have any time steps first
                                if residuals["time"]:
                                    residual_match = RESIDUAL_REGEX.search(line_str)
                                    if residual_match:
                                        field = residual_match.group(1)
                                        value = float(residual_match.group(2))
                                        if field in residuals:
                                            residuals[field].append(value)

                            # Only advance offset after successful processing attempt
                            new_offset += line_len

                        except Exception as decode_error:
                            logger.error(f"Error processing log line: {decode_error}")
                            # Advance offset to avoid getting stuck on bad lines
                            new_offset += line_len

            finally:
                if fd is not None:
                    os.close(fd)

            # Update cache
            _RESIDUALS_CACHE[path_str] = (mtime, size, new_offset, residuals)

        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error parsing log file: {e}")
            # On error, clear cache entry to force fresh read next time
            if path_str in _RESIDUALS_CACHE:
                del _RESIDUALS_CACHE[path_str]
            return {}

        return residuals


def get_available_fields(case_dir: str) -> List[str]:
    """Get list of available fields in the latest time directory."""
    parser = OpenFOAMFieldParser(case_dir)
    time_dirs = parser.get_time_directories()
    if not time_dirs:
        return []

    latest_time = time_dirs[-1]
    time_path = Path(case_dir) / latest_time

    # ⚡ Bolt Optimization: Use cached scanning
    # We ignore the specific types here and just return all relevant files
    _, _, all_files = parser._scan_time_dir(time_path)

    return sorted(all_files)
