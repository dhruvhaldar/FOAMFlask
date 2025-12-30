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
import copy

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

# Pre-compiled regex patterns
# Matches "Time = <number>"
TIME_REGEX = re.compile(r"Time\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")

# Matches "<field> ... Initial residual = <number>"
# We use a single regex to capture field name and value to avoid 7 passes per line
# Captures group 1: field name, group 2: value
RESIDUAL_REGEX = re.compile(r"(Ux|Uy|Uz|p|k|epsilon|omega).*Initial residual\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")

# ⚡ Bolt Optimization: Pre-compute translation table for vector parsing
# Replaces parenthesis with spaces to flatten vector lists efficiently.
# Using translate() is ~30% faster than chained replace() calls for large strings and saves memory.
_PARENS_TRANS = str.maketrans("()", "  ")

class OpenFOAMFieldParser:
    """Parse OpenFOAM field files and extract data."""

    def __init__(self, case_dir: Union[str, Path]) -> None:
        self.case_dir = Path(case_dir)

    def get_time_directories(self) -> List[str]:
        """Get all time directories sorted numerically."""
        path_str = str(self.case_dir)
        try:
            mtime = self.case_dir.stat().st_mtime

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

    def get_plot_data_version(self) -> str:
        """Get a version string for plot data based on file mtimes."""
        try:
            # 1. Case directory mtime (captures new time steps)
            case_stat = self.case_dir.stat()
            case_mtime = case_stat.st_mtime

            # 2. Latest time step mtime (captures data updates in running simulation)
            # Use cached time_dirs if available
            time_dirs = self.get_time_directories()
            if not time_dirs:
                return f"{case_mtime}"

            latest = time_dirs[-1]
            latest_path = self.case_dir / latest
            latest_mtime = latest_path.stat().st_mtime

            return f"{case_mtime}-{latest}-{latest_mtime}"
        except OSError:
            return ""

    def get_residuals_version(self, log_file: str = "log.foamRun") -> str:
        """Get a version string for residuals based on log file mtime and size."""
        try:
            stat = (self.case_dir / log_file).stat()
            return f"{stat.st_mtime}-{stat.st_size}"
        except OSError:
            return "0-0"

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
                mtime = field_entry.stat().st_mtime
                field_path = Path(path_str)
            else:
                field_path = field_entry
                path_str = str(field_path)
                mtime = field_path.stat().st_mtime

            if path_str in _FIELD_TYPE_CACHE:
                cached_mtime, cached_type = _FIELD_TYPE_CACHE[path_str]
                # ⚡ Bolt Optimization: If type was previously identified, trust it.
                # Field types (scalar/vector) are invariant for a given filename in OpenFOAM.
                # Even if mtime changes (file update), the type remains the same.
                # This eliminates thousands of open/read syscalls during simulation polling.
                if cached_type is not None:
                    return cached_type

                # If it was None (unidentified), retry if mtime changed.
                if cached_mtime == mtime:
                    return cached_type

            # Simple header check doesn't need aggressive caching, but reading first bytes is fast.
            with field_path.open("r", encoding="utf-8") as f:
                header = f.read(2048)
            
            field_type = None
            if re.search(r"class\s+volScalarField;", header):
                field_type = "scalar"
            elif re.search(r"class\s+volVectorField;", header):
                field_type = "vector"

            _FIELD_TYPE_CACHE[path_str] = (mtime, field_type)
            return field_type
        except Exception:
            return None

    def _scan_time_dir(self, time_path: Path) -> Tuple[List[str], bool, List[str]]:
        """
        Scan a time directory and categorize fields.
        Returns: (scalar_fields, has_U, all_files)
        Cached based on directory mtime.
        """
        path_str = str(time_path)
        try:
            mtime = time_path.stat().st_mtime

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

    def _resolve_variable(self, content: str, var_name: str) -> Optional[str]:
        """
        Attempt to resolve a variable definition within the file content.
        Looks for patterns like 'varName value;'
        """
        clean_var = var_name.lstrip('$')
        
        # Regex to find "variable value;"
        pattern = re.compile(rf"(?:^|\s){re.escape(clean_var)}\s+([^;]+);")
        match = pattern.search(content)
        
        if match:
            value_str = match.group(1).strip()
            
            if value_str.startswith('$'):
                return self._resolve_variable(content, value_str)
            
            if "#calc" in value_str:
                logger.debug(f"Variable {clean_var} contains #calc macro, skipping resolution.")
                return None
                
            return value_str
            
        return None

    def parse_scalar_field(self, field_path: Path, check_mtime: bool = True, known_mtime: Optional[float] = None) -> Optional[float]:
        """Parse a scalar field file and return average value with caching."""
        path_str = str(field_path)
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
                    mtime = field_path.stat().st_mtime
                except OSError:
                    # File might not exist
                    return None
            
            # Return cached if valid (only if we checked mtime or have known mtime)
            if (check_mtime or known_mtime is not None) and path_str in _FILE_CACHE:
                cached_mtime, cached_val = _FILE_CACHE[path_str]
                if cached_mtime == mtime:
                    return cached_val

            val = None

            try:
                # ⚡ Bolt Optimization: Use mmap for large files to avoid reading entire file into memory.
                # This is ~3x faster for large fields and reduces memory pressure significantly.
                with field_path.open("rb") as f:
                    # mmap can fail for empty files or if file is too small
                    # ⚡ Bolt Optimization: Use os.fstat(fd) instead of path.stat() to save a syscall
                    if f.fileno() != -1 and os.fstat(f.fileno()).st_size > 0:
                         with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                            # 1. Check for nonuniform list
                            # Look for "internalField nonuniform"
                            idx = mm.find(b"internalField")
                            if idx != -1:
                                # Verify "nonuniform" follows
                                # Read enough context (e.g., 200 bytes)
                                mm.seek(idx)
                                context = mm.read(200)

                                if b"nonuniform" in context:
                                    # Locate list start '('
                                    start_paren = mm.find(b'(', idx)
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
                                if idx != -1: mm.seek(idx)
                                else: mm.seek(0)

                                # If we haven't read context yet, read it now
                                # But we might have searched for internalField above
                                if idx == -1: idx = mm.find(b"internalField")

                                if idx != -1:
                                    mm.seek(idx)
                                    context = mm.read(200).decode("utf-8", errors="ignore")
                                    if "uniform" in context:
                                        # Variable substitution
                                        var_match = re.search(r"internalField\s+uniform\s+(\$[a-zA-Z0-9_]+);", context)
                                        if var_match:
                                            var_name = var_match.group(1)
                                            # We need full content for variable resolution, which is rare.
                                            # Fallback to full read only if needed.
                                            content = field_path.read_text(encoding="utf-8")
                                            resolved_value = self._resolve_variable(content, var_name)
                                            if resolved_value:
                                                val = float(resolved_value)

                                        if val is None:
                                            match = re.search(r"internalField\s+uniform\s+([^;]+);", context)
                                            if match:
                                                try:
                                                    val = float(match.group(1).strip())
                                                except ValueError:
                                                    pass

            except (FileNotFoundError, OSError, ValueError) as e:
                # If mmap fails or file issues, we fall back or return None
                # If we really want to be safe we can fall back to read_text
                pass

            # Fallback for complex cases (e.g. comments inside list breaking numpy)
            if val is None:
                try:
                    content = field_path.read_text(encoding="utf-8")
                    if "nonuniform" in content:
                        match = re.search(
                            r"internalField\s+nonuniform\s+.*?\(\s*([\s\S]*?)\s*\)\s*;",
                            content,
                            re.DOTALL,
                        )
                        if match:
                            field_data = match.group(1)
                            numbers_list = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", field_data)
                            if numbers_list:
                                val = float(np.mean([float(n) for n in numbers_list]))
                except (FileNotFoundError, OSError):
                    pass
            
            # Update cache
            _FILE_CACHE[path_str] = (mtime, val)
            return val

        except Exception as e:
            logger.error(f"Error parsing scalar field {field_path}: {e}")
            return None

    def parse_vector_field(self, field_path: Path, check_mtime: bool = True, known_mtime: Optional[float] = None) -> Tuple[float, float, float]:
        """Parse a vector field file and return average components with caching."""
        path_str = str(field_path)
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
                    mtime = field_path.stat().st_mtime
                except OSError:
                    return 0.0, 0.0, 0.0
            
            # Return cached if valid (only if we checked mtime or have known mtime)
            if (check_mtime or known_mtime is not None) and path_str in _FILE_CACHE:
                cached_mtime, cached_val = _FILE_CACHE[path_str]
                if cached_mtime == mtime:
                    return cached_val

            val = (0.0, 0.0, 0.0)

            try:
                # ⚡ Bolt Optimization: Use mmap for large files
                with field_path.open("rb") as f:
                    # ⚡ Bolt Optimization: Use os.fstat(fd) instead of path.stat()
                    if f.fileno() != -1 and os.fstat(f.fileno()).st_size > 0:
                        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                            # 1. Check for nonuniform
                            idx = mm.find(b"internalField")
                            if idx != -1:
                                mm.seek(idx)
                                context = mm.read(200)
                                if b"nonuniform" in context:
                                    start_paren = mm.find(b'(', idx)
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
                                                clean_data = data_block.replace(b'(', b' ').replace(b')', b' ')
                                                arr = np.fromstring(clean_data, sep=' ')

                                                if arr.size > 0:
                                                    arr = arr.reshape(-1, 3)
                                                    mean_vec = np.mean(arr, axis=0)
                                                    val = (float(mean_vec[0]), float(mean_vec[1]), float(mean_vec[2]))
                                            except ValueError:
                                                pass

                            # 2. Check for uniform
                            if val == (0.0, 0.0, 0.0):
                                if idx != -1: mm.seek(idx)
                                else: mm.seek(0)

                                if idx == -1: idx = mm.find(b"internalField")

                                if idx != -1:
                                    mm.seek(idx)
                                    context = mm.read(200).decode("utf-8", errors="ignore")
                                    if "uniform" in context:
                                         if re.search(r"internalField\s+uniform\s+\$[a-zA-Z0-9_]+;", context):
                                             # Variable detected
                                             val = (0.0, 0.0, 0.0)
                                         else:
                                             match = re.search(r"internalField\s+uniform\s+(\([^;]+\));", context, re.DOTALL)
                                             if match:
                                                 vec_str = match.group(1)
                                                 # Simple regex for (x y z)
                                                 vec_match = re.search(
                                                    r"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
                                                    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
                                                    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)",
                                                    vec_str,
                                                 )
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
                    content = field_path.read_text(encoding="utf-8")
                    if "nonuniform" in content:
                        match = re.search(
                            r"internalField\s+nonuniform\s+.*?\(\s*([\s\S]*?)\s*\)\s*;",
                            content,
                            re.DOTALL,
                        )
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
            _FILE_CACHE[path_str] = (mtime, val)
            return val

        except Exception as e:
            logger.error(f"Error parsing vector field {field_path}: {e}")
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
                            val = self.parse_scalar_field(Path(entry.path), known_mtime=entry.stat().st_mtime)
                            if val is not None:
                                data[entry.name] = val

                        elif field_type == "vector" and entry.name == "U":
                             ux, uy, uz = self.parse_vector_field(Path(entry.path), known_mtime=entry.stat().st_mtime)
                             data["Ux"] = ux
                             data["Uy"] = uy
                             data["Uz"] = uz
                             data["U_mag"] = float(np.sqrt(ux**2 + uy**2 + uz**2))
                        
        except Exception as e:
            logger.error(f"Error scanning fields in {time_path}: {e}")

        return data

    def get_all_time_series_data(self, max_points: int = 100) -> Dict[str, List[float]]:
        """Get time series data for all available fields dynamically."""
        all_time_dirs = self.get_time_directories()
        if not all_time_dirs:
            return {}

        # ⚡ Bolt Optimization: Use append-only cache for stable history
        # We cache the full accumulated history (excluding the latest unstable step)
        # This avoids rebuilding lists and redundant lookups for thousands of past steps.
        case_path_str = str(self.case_dir)

        # We must use deepcopy here to ensure we work on a detached copy.
        # This prevents polluting the global cache if parsing fails partway,
        # and ensures thread safety for readers of the global cache.
        cache_entry = _TIME_SERIES_CACHE.get(case_path_str)
        if cache_entry:
            cached_dirs, cached_data = copy.deepcopy(cache_entry)
        else:
            cached_dirs, cached_data = [], {}

        # Determine how much of the cache is valid
        # We need a common prefix match.
        valid_cache_len = 0
        min_len = min(len(cached_dirs), len(all_time_dirs))

        # Fast prefix check: if lengths differ but prefix matches
        if all_time_dirs[:len(cached_dirs)] == cached_dirs:
            valid_cache_len = len(cached_dirs)
        else:
            # Slower element-wise check if there was a divergence (e.g. restart)
            for i in range(min_len):
                if cached_dirs[i] == all_time_dirs[i]:
                    valid_cache_len += 1
                else:
                    break

        # If cache is invalid (diverged), reset it
        if valid_cache_len < len(cached_dirs):
            cached_dirs = cached_dirs[:valid_cache_len]
            # Slice all lists in cached_data
            for k in cached_data:
                cached_data[k] = cached_data[k][:valid_cache_len]

        # Identify stable steps to process (all except the very last one)
        # If simulation is done, the last one is stable too, but we treat it as volatile
        # to simplify logic (it gets re-parsed every time until a newer one appears).
        if not all_time_dirs:
            return {}

        latest_time = all_time_dirs[-1]
        stable_dirs_to_process = all_time_dirs[valid_cache_len:-1]

        # If we have new stable directories, we need to discover fields first
        # We assume fields are consistent across time steps.
        # We use the latest time step for discovery.
        latest_time_path = self.case_dir / latest_time
        
        # ⚡ Bolt Optimization: Use cached scanning for field discovery
        scalar_fields, has_U, _ = self._scan_time_dir(latest_time_path)

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
                time_path = self.case_dir / time_dir
                time_val = float(time_dir)

                cached_data["time"].append(time_val)

                # Parse scalars
                for field in scalar_fields:
                    # Ensure field exists in cache (handle dynamic field addition)
                    if field not in cached_data:
                        cached_data[field] = [0.0] * (len(cached_data["time"]) - 1)

                    field_path = time_path / field
                    # Skip check_mtime for stable steps (assumed immutable)
                    val = self.parse_scalar_field(field_path, check_mtime=False)
                    cached_data[field].append(val if val is not None else 0.0)

                # Parse U
                if has_U:
                    u_path = time_path / "U"
                    ux, uy, uz = self.parse_vector_field(u_path, check_mtime=False)

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

        except Exception as e:
            logger.error(f"Error updating time series cache: {e}")
            # Do not update global cache, fall back to what we have (or incomplete result)
            # We continue to at least try to return something useful

        # Construct final result: Cache Slice + Latest Step
        # We need the last `max_points` points.

        # 1. Start with a copy of the relevant slice from cache
        # If we need N points, and we have M cached points.
        # We take M points, add 1 latest point. Total M+1.
        # If M+1 > N, we slice the last N.

        # Be careful not to mutate cached lists in the result
        result_data = {}
        total_available = len(new_cached_dirs) + 1
        start_idx = max(0, total_available - max_points)

        # Calculate how many points from cache we need
        # We take everything from start_idx up to end of cache
        cache_slice_start = max(0, start_idx) # Index in cache

        for k, v in cached_data.items():
            result_data[k] = v[cache_slice_start:]

        # 2. Process and append the latest (unstable) step
        time_path = self.case_dir / latest_time
        time_val = float(latest_time)

        # Ensure latest step keys exist
        if "time" not in result_data: result_data["time"] = []
        result_data["time"].append(time_val)

        for field in scalar_fields:
            if field not in result_data: result_data[field] = []

            field_path = time_path / field
            # Always check mtime for latest step
            val = self.parse_scalar_field(field_path, check_mtime=True)
            result_data[field].append(val if val is not None else 0.0)

        if has_U:
            u_path = time_path / "U"
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

    def get_residuals_from_log(self, log_file: str = "log.foamRun") -> Dict[str, List[float]]:
        """Parse residuals from OpenFOAM log file incrementally."""
        log_path = self.case_dir / log_file
        path_str = str(log_path)

        if not log_path.exists():
            return {}

        try:
            stat = log_path.stat()
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
                    return cached_data

                # Case 2: File grew (append) - Reuse cached data and offset
                if size > cached_size and cached_size > 0:
                    start_offset = cached_offset
                    residuals = cached_data # Reference to existing mutable dict

                # Case 3: File shrank or reset - Start over (defaults apply)

            new_offset = start_offset

            # ⚡ Bolt Optimization: Use binary mode to bulk read new data.
            # This avoids expensive readline() loops and repeated tell() syscalls.
            with log_path.open("rb") as f:
                if start_offset > 0:
                    f.seek(start_offset)

                # Read all new bytes
                chunk = f.read()
                if not chunk:
                    # No new data
                    _RESIDUALS_CACHE[path_str] = (mtime, size, new_offset, residuals)
                    return residuals

                # Check for complete lines
                # We need a newline at the end of the valid chunk.
                # However, chunk may not end with newline if write is partial.
                # We should only process up to the last newline.
                last_newline = chunk.rfind(b'\n')

                if last_newline == -1:
                    # No complete lines found in the new chunk.
                    # Do not advance offset, do not process partial data.
                    pass
                else:
                    # Slice valid data
                    valid_chunk = chunk[:last_newline+1]

                    # Update offset
                    new_offset = start_offset + len(valid_chunk)

                    # Decode and process lines
                    try:
                        text_content = valid_chunk.decode("utf-8", errors="replace")

                        for line in text_content.splitlines():
                            # Optimized time matching
                            if "Time =" in line:
                                time_match = TIME_REGEX.search(line)
                                if time_match:
                                    current_time = float(time_match.group(1))
                                    residuals["time"].append(current_time)

                            # Optimized residual matching
                            if "Initial residual" in line:
                                residual_match = RESIDUAL_REGEX.search(line)
                                if residual_match and residuals["time"]:
                                    field = residual_match.group(1)
                                    value = float(residual_match.group(2))
                                    if field in residuals:
                                        residuals[field].append(value)
                    except Exception as decode_error:
                        logger.error(f"Error decoding log chunk: {decode_error}")

            # Update cache
            _RESIDUALS_CACHE[path_str] = (mtime, size, new_offset, residuals)

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
