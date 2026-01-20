"""Isosurface visualization module for FOAMFlask.

This module provides functionality for generating and visualizing isosurfaces
from VTK mesh data using PyVista. It supports both static and interactive
visualizations with various customization options.
"""

# Standard library imports
import logging
import os
import tempfile
import multiprocessing
import hashlib
import shutil
import stat
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Third-party imports
import numpy as np
import pyvista as pv
from pyvista import DataSet, PolyData, Plotter

# Configure logger
logger = logging.getLogger("FOAMFlask")

CACHE_SIZE_LIMIT_MB = 500  # Limit cache to 500MB

def _get_cache_dir() -> Path:
    """Get the cache directory, creating it if it doesn't exist."""
    cache_dir = Path(tempfile.gettempdir()) / "foamflask_isosurface_cache"

    # Security: Ensure directory exists with secure permissions (0700)
    if not cache_dir.exists():
        try:
            cache_dir.mkdir(parents=True, mode=0o700)
        except OSError:
            # If mkdir fails (e.g. race condition), check permissions below
            pass

    # Ensure permissions are set (mkdir mode might be ignored or modified by umask)
    # We do this always to ensure security even if directory already existed
    try:
        os.chmod(cache_dir, 0o700)
    except OSError as e:
        # If we can't chmod (e.g. not owner), we'll catch it in the ownership check below
        logger.debug(f"Security: Failed to set permissions on cache dir: {e}")

    # Check permissions and ownership
    try:
        st = cache_dir.stat()

        # Check if owned by current user (POSIX only)
        if hasattr(os, "getuid"):
            if st.st_uid != os.getuid():
                logger.warning(
                    f"Security: Cache directory {cache_dir} is not owned by current user. "
                    "Using a temporary directory instead."
                )
                return Path(tempfile.mkdtemp(prefix="foamflask_iso_"))

        # Check permissions (rwx------) (POSIX only)
        # On Windows, these constants might technically exist in stat module but logic differs.
        # However, checking them on Windows usually doesn't hurt (returns 0 or irrelevant).
        # We focus on POSIX for the 0700 requirement.
        if os.name == "posix":
            if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                logger.warning(
                    f"Security: Cache directory {cache_dir} has insecure permissions. "
                    "Attempting to fix."
                )
                try:
                    os.chmod(cache_dir, 0o700)
                except OSError as e:
                    logger.warning(f"Security: Failed to fix permissions: {e}")
                    return Path(tempfile.mkdtemp(prefix="foamflask_iso_"))
    except OSError as e:
        logger.warning(f"Security: Error checking cache dir permissions: {e}")
        return Path(tempfile.mkdtemp(prefix="foamflask_iso_"))

    return cache_dir

def _cleanup_cache():
    """
    Maintain cache size within limits by deleting oldest files.
    """
    try:
        # ⚡ Bolt Optimization: Probabilistic cleanup
        # Scanning the directory is expensive (O(N) syscalls).
        # We only run cleanup 10% of the time to amortize the cost.
        if random.random() > 0.1:
            return

        cache_dir = _get_cache_dir()
        limit_bytes = CACHE_SIZE_LIMIT_MB * 1024 * 1024

        files = []
        total_size = 0

        # ⚡ Bolt Optimization: Use os.scandir to avoid redundant stat calls
        try:
            with os.scandir(str(cache_dir)) as entries:
                for entry in entries:
                    if entry.is_file():
                        stat = entry.stat()
                        total_size += stat.st_size
                        files.append((entry.path, stat.st_mtime, stat.st_size))
        except OSError:
            return

        if total_size > limit_bytes:
            # Sort by mtime (oldest first)
            files.sort(key=lambda x: x[1])

            for path, _, size in files:
                try:
                    os.unlink(path)
                    total_size -= size
                    if total_size <= limit_bytes:
                        break
                except OSError:
                    pass
    except Exception as e:
        logger.warning(f"Error during cache cleanup: {e}")

def _decimate_mesh_helper(mesh: DataSet, target_faces: int = 100000) -> DataSet:
    """Decimate mesh helper for subprocess."""
    if mesh.n_cells <= target_faces:
        return mesh

    try:
        if not isinstance(mesh, pv.PolyData):
            mesh_poly = mesh.extract_surface()
        else:
            mesh_poly = mesh

        if mesh_poly.n_cells > target_faces:
            reduction = 1.0 - (target_faces / mesh_poly.n_cells)
            reduction = max(0.0, min(0.95, reduction))

            if reduction > 0.05:
                # ⚡ Bolt Optimization: Use fast decimate_pro if available
                if hasattr(mesh_poly, "decimate_pro"):
                    try:
                        return mesh_poly.decimate_pro(reduction, preserve_topology=True)
                    except Exception:
                        return mesh_poly.decimate(reduction)
                else:
                    return mesh_poly.decimate(reduction)

        return mesh_poly
    except Exception as e:
        print(f"Mesh decimation failed: {e}")
        return mesh

def _generate_isosurface_html_process(
    file_path: str,
    output_path: str,
    params: Dict[str, Any]
):
    """
    Helper function to be run in a separate process to generate the HTML.

    Args:
        file_path: Path to the VTK file.
        output_path: Path to write the HTML output.
        params: Dictionary containing visualization parameters.
    """
    try:
        scalar_field = params.get("scalar_field", "U_Magnitude")
        show_base_mesh = params.get("show_base_mesh", True)
        base_mesh_opacity = params.get("base_mesh_opacity", 0.25)
        contour_opacity = params.get("contour_opacity", 0.8)
        contour_color = params.get("contour_color", "red")
        colormap = params.get("colormap", "viridis")
        show_isovalue_slider = params.get("show_isovalue_slider", True)
        window_size = params.get("window_size", (1200, 800))

        # Load mesh
        # ⚡ Bolt Optimization: Disable progress bar
        mesh = pv.read(file_path, progress_bar=False)

        # Compute scalar field if needed (e.g. U_Magnitude)
        if scalar_field == "U_Magnitude" and "U_Magnitude" not in mesh.point_data and "U" in mesh.point_data:
            mesh.point_data["U_Magnitude"] = np.linalg.norm(mesh.point_data["U"], axis=1)

        if scalar_field not in mesh.point_data:
            raise ValueError(f"Scalar field '{scalar_field}' not found")

        # Create plotter
        plotter = pv.Plotter(notebook=False, off_screen=True, window_size=list(window_size))

        # Add base mesh
        if show_base_mesh:
            display_mesh = _decimate_mesh_helper(mesh, target_faces=100000)
            plotter.add_mesh(
                display_mesh,
                opacity=base_mesh_opacity,
                scalars=scalar_field,
                show_scalar_bar=True,
                cmap=colormap,
                label="Base Mesh",
                 scalar_bar_args={
                        "title": scalar_field,
                        "title_font_size": 20,
                        "label_font_size": 16,
                        "shadow": True,
                        "n_labels": 5,
                        "fmt": "%.2f",
                        "position_x": 0.85,
                        "position_y": 0.05,
                    },
            )

        # Add isosurfaces
        if show_isovalue_slider:
             widget_mesh = _decimate_mesh_helper(mesh, target_faces=200000)
             plotter.add_mesh_isovalue(
                widget_mesh,
                scalars=scalar_field,
                compute_normals=True,
                compute_gradients=False,
                compute_scalars=True,
                opacity=contour_opacity,
                color=contour_color,
                show_scalar_bar=False,
            )
        else:
            # Static contours logic re-implementation for subprocess
            isovalues = params.get("isovalues")
            custom_range = params.get("custom_range")
            num_isosurfaces = params.get("num_isosurfaces", 5)

            scalars = mesh.point_data[scalar_field]
            min_val = float(np.min(scalars))
            max_val = float(np.max(scalars))

            if isovalues is not None:
                values = np.array(isovalues)
            elif custom_range is not None:
                values = np.linspace(custom_range[0], custom_range[1], num_isosurfaces)
            else:
                values = np.linspace(min_val, max_val, num_isosurfaces + 2)[1:-1]

            contours = mesh.contour(isosurfaces=values.tolist(), scalars=scalar_field)
            if contours.n_points > 0:
                display_contours = _decimate_mesh_helper(contours, target_faces=100000)
                plotter.add_mesh(
                    display_contours,
                    opacity=contour_opacity,
                    show_scalar_bar=False,
                    color=contour_color,
                    label="Isosurfaces",
                )

        plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z", line_width=2, labels_off=False)
        plotter.camera_position = "iso"

        plotter.export_html(output_path)
        plotter.close()

    except Exception as e:
        print(f"Error in subprocess: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)


class IsosurfaceVisualizer:
    """Handles isosurface visualization from VTK mesh data using PyVista.

    This class provides functionality to:
    - Load VTK mesh files with scalar fields
    - Generate static isosurfaces at specified values
    - Create interactive HTML visualizations with isovalue sliders
    - Export visualization data and metadata

    Attributes:
        mesh: The loaded mesh with scalar data.
        contours: Generated isosurface contours.
        plotter: Active plotter instance (if any).
    """

    def __init__(self) -> None:
        """Initialize the isosurface visualizer with empty attributes."""
        self.mesh: Optional[DataSet] = None
        self.contours: Optional[PolyData] = None
        self.plotter: Optional[Plotter] = None
        self.current_mesh_path: Optional[str] = None
        self.current_mesh_mtime: Optional[float] = None
        logger.info("[FOAMFlask] [IsosurfaceVisualizer] Initialized")

    def _decimate_mesh(self, mesh: DataSet, target_faces: int = 100000) -> DataSet:
        """Decimate mesh to reduce size for web visualization."""
        # Kept for in-process usage if needed, though subprocess uses helper
        return _decimate_mesh_helper(mesh, target_faces)

    def load_mesh(
        self, file_path: str
    ) -> Dict[str, Union[bool, int, List[str], str, Dict]]:
        """Load a mesh from a VTK file and compute derived scalar fields.

        Automatically computes velocity magnitude (U_Magnitude) if a velocity
        vector field (U) exists in the point data.

        Args:
            file_path: Path to the VTK/VTP/VTU file.

        Returns:
            Dictionary containing mesh information.
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Mesh file not found: {file_path}")

            mtime = os.path.getmtime(file_path)

            # ⚡ Bolt Optimization: Cache Check
            if (
                self.mesh is not None
                and self.current_mesh_path == file_path
                and self.current_mesh_mtime == mtime
            ):
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Using cached mesh for {file_path}")
            else:
                logger.info(
                    f"[FOAMFlask] [IsosurfaceVisualizer] " f"Loading mesh from: {file_path}"
                )

                # Read the mesh with progress bar using PyVista
                # ⚡ Bolt Optimization: Disable progress bar
                self.mesh = pv.read(file_path, progress_bar=False)
                self.current_mesh_path = file_path
                self.current_mesh_mtime = mtime

                logger.info(
                    f"[FOAMFlask] [IsosurfaceVisualizer] "
                    f"Successfully loaded mesh: {self.mesh.n_points} points, "
                    f"{self.mesh.n_cells} cells"
                )

                # Compute velocity magnitude if U vector field exists
                if "U" in self.mesh.point_data:
                    self.mesh.point_data["U_Magnitude"] = np.linalg.norm(
                        self.mesh.point_data["U"], axis=1
                    )
                    logger.info(
                        "[FOAMFlask] [IsosurfaceVisualizer] "
                        "Computed U_Magnitude from U field"
                    )

            # Get mesh information
            mesh_info = {
                "success": True,
                "n_points": int(self.mesh.n_points),
                "n_cells": int(self.mesh.n_cells),
                "bounds": tuple(float(b) for b in self.mesh.bounds),
                "point_arrays": list(self.mesh.point_data.keys()),
                "cell_arrays": list(self.mesh.cell_data.keys()),
            }

            # Add velocity magnitude statistics if available
            if "U_Magnitude" in self.mesh.point_data:
                u_mag = self.mesh.point_data["U_Magnitude"]
                mesh_info["u_magnitude"] = {
                    "min": float(np.min(u_mag)),
                    "max": float(np.max(u_mag)),
                    "mean": float(np.mean(u_mag)),
                    "std": float(np.std(u_mag)),
                    "percentiles": {
                        "0": float(np.percentile(u_mag, 0)),
                        "25": float(np.percentile(u_mag, 25)),
                        "50": float(np.percentile(u_mag, 50)),
                        "75": float(np.percentile(u_mag, 75)),
                        "100": float(np.percentile(u_mag, 100)),
                    },
                }

            return mesh_info

        except Exception as e:
            logger.error(
                f"[FOAMFlask] [IsosurfaceVisualizer] " f"Error loading mesh: {e}"
            )
            return {"success": False, "error": str(e)}

    def generate_isosurfaces(
        self,
        scalar_field: str = "U_Magnitude",
        num_isosurfaces: int = 5,
        custom_range: Optional[List[float]] = None,
        isovalues: Optional[List[float]] = None,
    ) -> Dict[str, Union[bool, int, List[float], str]]:
        """Generate isosurfaces for the specified scalar field.

        Args:
            scalar_field: Name of the scalar field to create isosurfaces for.
            num_isosurfaces: Number of evenly-spaced isosurfaces.
            custom_range: Custom [min, max] range.
            isovalues: Explicit list of isovalues.

        Returns:
            Dictionary containing information about the generated isosurfaces.
        """
        try:
            if self.mesh is None:
                raise ValueError("No mesh loaded. Call load_mesh() first.")

            if scalar_field not in self.mesh.point_data:
                raise ValueError(
                    f"Scalar field '{scalar_field}' not found in point data. "
                    f"Available fields: {list(self.mesh.point_data.keys())}"
                )

            logger.info(
                f"[FOAMFlask] [IsosurfaceVisualizer] "
                f"Generating isosurfaces for field: {scalar_field}"
            )

            # Get the scalar data
            scalars = self.mesh.point_data[scalar_field]
            min_val = float(np.min(scalars))
            max_val = float(np.max(scalars))

            # Determine isovalues to use
            if isovalues is not None:
                values = np.array(isovalues)
            elif custom_range is not None:
                if len(custom_range) != 2:
                    raise ValueError(
                        "custom_range must be a list of [min, max] values."
                    )
                values = np.linspace(custom_range[0], custom_range[1], num_isosurfaces)
            else:
                values = np.linspace(min_val, max_val, num_isosurfaces + 2)[1:-1]

            # Generate isosurfaces using contour filter
            self.contours = self.mesh.contour(
                isosurfaces=values.tolist(), scalars=scalar_field
            )

            result = {
                "success": True,
                "scalar_field": scalar_field,
                "num_isosurfaces": len(values),
                "isovalues": [float(v) for v in values],
                "range": [min_val, max_val],
                "n_points": int(self.contours.n_points),
                "n_cells": int(self.contours.n_cells),
                "bounds": tuple(float(b) for b in self.contours.bounds),
            }

            return result

        except Exception as e:
            logger.error(
                f"[FOAMFlask] [IsosurfaceVisualizer] "
                f"Error generating isosurfaces: {e}"
            )
            return {"success": False, "error": str(e)}

    def get_scalar_field_info(
        self, scalar_field: Optional[str] = None
    ) -> Dict[str, Dict[str, Union[str, float, Dict[str, float]]]]:
        """Get statistical information about scalar fields in the mesh."""
        try:
            if self.mesh is None:
                raise ValueError("No mesh loaded. Call load_mesh() first.")

            result = {}

            # Determine which fields to process
            if scalar_field:
                if scalar_field not in self.mesh.point_data:
                    raise ValueError(
                        f"Scalar field '{scalar_field}' " f"not found in point data."
                    )
                fields = [scalar_field]
            else:
                fields = list(self.mesh.point_data.keys())

            # Compute statistics for each field
            for field in fields:
                data = self.mesh.point_data[field]

                # Handle vector fields vs scalar fields
                if len(data.shape) > 1:
                    magnitude = np.linalg.norm(data, axis=1)
                    result[field] = {
                        "type": "vector",
                        "shape": data.shape,
                        "magnitude_stats": {
                            "min": float(np.min(magnitude)),
                            "max": float(np.max(magnitude)),
                            "mean": float(np.mean(magnitude)),
                            "std": float(np.std(magnitude)),
                        },
                    }
                else:
                    result[field] = {
                        "type": "scalar",
                        "min": float(np.min(data)),
                        "max": float(np.max(data)),
                        "mean": float(np.mean(data)),
                        "std": float(np.std(data)),
                        "percentiles": {
                            "0": float(np.percentile(data, 0)),
                            "25": float(np.percentile(data, 25)),
                            "50": float(np.percentile(data, 50)),
                            "75": float(np.percentile(data, 75)),
                            "100": float(np.percentile(data, 100)),
                        },
                    }

            return result

        except Exception as e:
            logger.error(
                f"[FOAMFlask] [IsosurfaceVisualizer] " f"Error getting field info: {e}"
            )
            return {"error": str(e)}

    def get_interactive_html(
        self,
        scalar_field: str = "U_Magnitude",
        show_base_mesh: bool = True,
        base_mesh_opacity: float = 0.25,
        contour_opacity: float = 0.8,
        contour_color: str = "red",
        colormap: str = "viridis",
        show_isovalue_slider: bool = True,
        custom_range: Optional[Tuple[float, float]] = None,
        num_isosurfaces: int = 5,
        isovalues: Optional[List[float]] = None,
        window_size: Tuple[int, int] = (1200, 800),
    ) -> str:
        """Generate an interactive HTML visualization of mesh and isosurfaces.

        ⚡ Bolt Optimization: Uses subprocess and caching to prevent blocking the main thread.
        """
        try:
            # Validate that mesh is loaded or path is known
            if self.current_mesh_path is None:
                raise ValueError("No mesh loaded. Call load_mesh() first.")

            path = Path(self.current_mesh_path).resolve()

            if not path.exists():
                raise ValueError(f"Mesh file no longer exists: {path}")

            mtime = path.stat().st_mtime

            # ⚡ Bolt Optimization: Caching logic
            # Create a cache key based on all parameters
            params = {
                "scalar_field": scalar_field,
                "show_base_mesh": show_base_mesh,
                "base_mesh_opacity": base_mesh_opacity,
                "contour_opacity": contour_opacity,
                "contour_color": contour_color,
                "colormap": colormap,
                "show_isovalue_slider": show_isovalue_slider,
                "custom_range": custom_range,
                "num_isosurfaces": num_isosurfaces,
                "isovalues": isovalues,
                "window_size": window_size,
                "file_path": str(path),
                "mtime": mtime
            }

            try:
                # Deterministic JSON representation for hashing
                import json
                # Handle types that might not be JSON serializable (like tuple)
                cache_str = json.dumps(params, sort_keys=True, default=str)
                cache_key = hashlib.sha256(cache_str.encode()).hexdigest()

                cache_dir = _get_cache_dir()
                cache_path = cache_dir / f"{cache_key}.html"

                if cache_path.exists():
                    logger.debug(f"Serving isosurface from cache: {cache_path}")
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return f.read()
            except Exception as e:
                logger.warning(f"Cache check failed: {e}")

            # Create a temp file for the output
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                temp_output_path = tmp.name

            # Run generation in a separate process
            # ⚡ Bolt Optimization: Offload blocking VTK/serialization work
            p = multiprocessing.Process(
                target=_generate_isosurface_html_process,
                args=(str(path), temp_output_path, params)
            )
            p.start()
            p.join(timeout=300) # Give it reasonable time for large meshes

            if p.is_alive():
                p.terminate()
                p.join()
                logger.error("Isosurface HTML generation timed out")
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                return self._generate_error_html("Generation timed out", scalar_field)

            if p.exitcode != 0:
                logger.error("Isosurface HTML generation process failed")
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                return self._generate_error_html("Generation process failed", scalar_field)

            if not os.path.exists(temp_output_path) or os.path.getsize(temp_output_path) == 0:
                 logger.error("Isosurface HTML output file is empty or missing")
                 if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                 return self._generate_error_html("Generation failed (empty output)", scalar_field)

            with open(temp_output_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # ⚡ Bolt Optimization: Save to cache
            try:
                _cleanup_cache()
                shutil.move(temp_output_path, cache_path)
            except Exception as e:
                logger.warning(f"Failed to save to cache: {e}")
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)

            return html_content

        except Exception as e:
            logger.error(
                f"[FOAMFlask] [IsosurfaceVisualizer] "
                f"[get_interactive_html] "
                f"Failed to generate HTML viewer: {e}"
            )
            return self._generate_error_html(str(e), scalar_field)

    def _generate_error_html(self, error_message, scalar_field=""):
        """Generate a user-friendly HTML error page."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Visualization Error</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            padding: 40px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .error-container {{
            max-width: 800px;
            width: 100%;
            padding: 40px;
            background-color: #fff;
            border-left: 6px solid #dc3545;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        h2 {{
            color: #dc3545;
            margin-top: 0;
            font-size: 28px;
        }}
        .error-message {{
            color: #721c24;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            font-size: 14px;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h2>⚠️ Error Generating 3D Visualization</h2>
        <div class="error-message">
            <strong>Error:</strong><br>
            {error_message}
        </div>
        <p>Scalar field: <code>{scalar_field}</code></p>
    </div>
</body>
</html>
"""

    def export_contours(self, output_path, file_format="vtk"):
        """Export generated contours to a file."""
        try:
            if self.contours is None:
                raise ValueError(
                    "No contours generated. " "Call generate_isosurfaces() first."
                )

            if not output_path.endswith(f".{file_format}"):
                output_path = f"{output_path}.{file_format}"

            self.contours.save(output_path)

            logger.info(
                f"[FOAMFlask] [IsosurfaceVisualizer] "
                f"Exported contours to: {output_path}"
            )

            return {
                "success": True,
                "output_path": output_path,
                "file_size": os.path.getsize(output_path),
                "format": file_format,
            }

        except Exception as e:
            logger.error(
                f"[FOAMFlask] [IsosurfaceVisualizer] " f"Error exporting contours: {e}"
            )
            return {"success": False, "error": str(e)}

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, "plotter") and self.plotter is not None:
            try:
                self.plotter.close()
            except Exception:
                pass


# Global instance for use as a singleton
isosurface_visualizer = IsosurfaceVisualizer()
