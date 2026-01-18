import logging
import pyvista as pv
from pathlib import Path
from typing import Optional, Union, Dict, Any
import multiprocessing
import tempfile
import os
import gzip
import shutil
import hashlib

logger = logging.getLogger("FOAMFlask")

ALLOWED_EXTENSIONS = {'.stl', '.obj', '.obj.gz', '.ply', '.vtp', '.vtu', '.g'}

def _get_cache_dir() -> Path:
    """Get the cache directory, creating it if it doesn't exist."""
    cache_dir = Path(tempfile.gettempdir()) / "foamflask_geometry_cache"
    cache_dir.mkdir(exist_ok=True, parents=True)
    return cache_dir

CACHE_SIZE_LIMIT_MB = 500  # Limit cache to 500MB

def _cleanup_cache():
    """
    Maintain cache size within limits by deleting oldest files.
    """
    try:
        cache_dir = _get_cache_dir()
        limit_bytes = CACHE_SIZE_LIMIT_MB * 1024 * 1024

        files = []
        total_size = 0

        # ⚡ Bolt Optimization: Use os.scandir to avoid redundant stat calls
        # Gather all file stats in a single pass instead of iterating twice (sum + sort)
        try:
            with os.scandir(str(cache_dir)) as entries:
                for entry in entries:
                    if entry.is_file():
                        stat = entry.stat()
                        total_size += stat.st_size
                        files.append((entry.path, stat.st_mtime, stat.st_size))
        except OSError:
            # Cache directory might have issues, skip cleanup
            return

        if total_size > limit_bytes:
            # Sort by mtime (oldest first)
            files.sort(key=lambda x: x[1])

            for path, _, size in files:
                try:
                    os.unlink(path)
                    total_size -= size
                    logger.debug(f"Deleted cache file {path} to free space")
                    if total_size <= limit_bytes:
                        break
                except OSError:
                    pass
    except Exception as e:
        logger.warning(f"Error during cache cleanup: {e}")

def _generate_html_process(file_path: str, output_path: str, color: str, opacity: float):
    """
    Helper function to be run in a separate process to generate the HTML.
    This avoids signal handling issues with trame/aiohttp in Flask threads.
    """
    temp_read_path = None
    try:
        read_path = file_path
        if file_path.lower().endswith(".gz"):
             # Decompress to temporary file
             suffix = ".obj" if ".obj" in file_path.lower() else ".stl" # Simple heuristic
             with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                 with gzip.open(file_path, "rb") as f_in:
                     shutil.copyfileobj(f_in, tmp)
                 temp_read_path = tmp.name
                 read_path = temp_read_path

        # ⚡ Bolt Optimization: Disable progress bar
        mesh = pv.read(read_path, progress_bar=False)

        # ⚡ Bolt Optimization: Decimate mesh if needed
        # Increased target faces for better visual quality on modern browsers
        TARGET_FACES = 500000
        if mesh.n_cells > TARGET_FACES:
            try:
                # Assuming mesh is likely PolyData for STL/OBJ
                if not isinstance(mesh, pv.PolyData):
                    mesh = mesh.extract_surface()

                reduction = 1.0 - (TARGET_FACES / mesh.n_cells)
                reduction = max(0.0, min(0.95, reduction))
                if reduction > 0.05: # Only decimate if reduction is significant
                    print(f"Decimating geometry from {mesh.n_cells} to ~{TARGET_FACES} cells")

                    # ⚡ Bolt Optimization: Use fast decimate_pro if available (topology preserving, faster)
                    if hasattr(mesh, "decimate_pro"):
                         try:
                             mesh = mesh.decimate_pro(reduction, preserve_topology=True)
                         except Exception as e:
                             print(f"decimate_pro failed ({e}), falling back to standard decimate")
                             mesh = mesh.decimate(reduction)
                    else:
                         mesh = mesh.decimate(reduction)

            except Exception as e:
                print(f"Decimation failed, using full mesh: {e}")

        plotter = pv.Plotter(notebook=False, off_screen=True)
        plotter.add_mesh(mesh, color=color, opacity=opacity, show_edges=False)
        plotter.show_grid()
        plotter.show_axes()
        plotter.camera_position = 'iso'
        plotter.export_html(output_path)
        plotter.close()
    except Exception as e:
        # We can't easily log to the main logger from here, but we can print or write to a file
        print(f"Error in subprocess: {e}")
        # Ensure failure is detectable
        if os.path.exists(output_path):
            os.remove(output_path)
    finally:
        if temp_read_path and os.path.exists(temp_read_path):
            try:
                os.remove(temp_read_path)
            except OSError:
                pass

class GeometryVisualizer:
    """Visualizes geometry files (STL) using PyVista."""

    @staticmethod
    def get_interactive_html(file_path: Union[str, Path], color: str = "lightblue", opacity: float = 1.0) -> Optional[str]:
        """
        Generates an interactive HTML representation of the STL file.

        Args:
            file_path: Path to the STL file.
            color: Color of the mesh.
            opacity: Opacity of the mesh.

        Returns:
            HTML string content or None on error.
        """
        try:
            path = Path(file_path).resolve()
            
            # Security check: Ensure file extension is allowed
            suffixes = path.suffixes
            # Handle .obj.gz case
            if len(suffixes) >= 2 and suffixes[-2] + suffixes[-1] == '.obj.gz':
                ext = '.obj.gz'
            else:
                ext = path.suffix.lower()

            if ext not in ALLOWED_EXTENSIONS:
                logger.error(f"Security: Invalid file extension for geometry visualizer: {ext}")
                return None

            if not path.exists():
                logger.error(f"STL file not found: {path}")
                return None

            # ⚡ Bolt Optimization: Caching
            # Check cache based on file path, mtime, and visualization parameters
            try:
                mtime = path.stat().st_mtime
                cache_key_str = f"{str(path)}_{mtime}_{color}_{opacity}"
                cache_key = hashlib.sha256(cache_key_str.encode()).hexdigest()

                cache_dir = _get_cache_dir()
                cache_path = cache_dir / f"{cache_key}.html"

                if cache_path.exists():
                    logger.debug(f"Serving geometry from cache: {cache_path}")
                    # Update access time? Not strictly necessary for tmp cache but good practice
                    # cache_path.touch()
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return f.read()
            except Exception as e:
                logger.warning(f"Cache check failed: {e}")

            # Create a temp file for the output
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                temp_output_path = tmp.name

            # Run generation in a separate process
            p = multiprocessing.Process(
                target=_generate_html_process,
                args=(str(path), temp_output_path, color, opacity)
            )
            p.start()
            p.join(timeout=120) # Increased timeout for large meshes/high res

            if p.is_alive():
                p.terminate()
                p.join()
                logger.error("HTML generation timed out")
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                return None

            if p.exitcode != 0:
                logger.error("HTML generation process failed")
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                return None

            if not os.path.exists(temp_output_path) or os.path.getsize(temp_output_path) == 0:
                 logger.error("HTML output file is empty or missing")
                 if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                 return None

            with open(temp_output_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # ⚡ Bolt Optimization: Save to cache
            try:
                # Perform cleanup if needed
                _cleanup_cache()

                # Move temp file to cache path (atomic on same filesystem)
                # If cache dir is on different FS, shutil.move handles copy-delete
                shutil.move(temp_output_path, cache_path)
            except Exception as e:
                logger.warning(f"Failed to save to cache: {e}")
                # If move failed, temp_output_path might still exist or be half-moved
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)

            return html_content

        except Exception as e:
            logger.error(f"Error generating interactive geometry view: {e}")
            return None

    @staticmethod
    def get_mesh_info(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get basic information about the STL mesh (bounds, center, etc.)
        """
        try:
            path = Path(file_path).resolve()

            # Security check: Ensure file extension is allowed
            suffixes = path.suffixes
            # Handle .obj.gz case
            if len(suffixes) >= 2 and suffixes[-2] + suffixes[-1] == '.obj.gz':
                ext = '.obj.gz'
            else:
                ext = path.suffix.lower()

            if ext not in ALLOWED_EXTENSIONS:
                 return {"success": False, "error": "Invalid file extension"}

            if not path.exists():
                return {"success": False, "error": "File not found"}

            read_path = str(path)
            temp_read_path = None
            
            try:
                if read_path.lower().endswith(".gz"):
                    suffix = ".obj" if ".obj" in read_path.lower() else ".stl"
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                        with gzip.open(read_path, "rb") as f_in:
                            shutil.copyfileobj(f_in, tmp)
                        temp_read_path = tmp.name
                        read_path = temp_read_path

                # ⚡ Bolt Optimization: Disable progress bar
                mesh = pv.read(read_path, progress_bar=False)
                bounds = mesh.bounds
                center = mesh.center

                return {
                    "success": True,
                    "bounds": bounds,
                    "center": center,
                    "n_points": mesh.n_points,
                    "n_cells": mesh.n_cells
                }
            finally:
                if temp_read_path and os.path.exists(temp_read_path):
                    try:
                        os.remove(temp_read_path)
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"Error getting mesh info: {e}")
            return {"success": False, "error": str(e)}
