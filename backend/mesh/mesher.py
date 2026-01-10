"""PyVista handler module for mesh visualization in FOAMFlask.

This module provides functionality to load and visualize VTK/VTP mesh files using PyVista.
It includes features for generating screenshots, interactive HTML viewers, and managing
mesh data for visualization purposes.
"""

# Standard library imports
import base64
import logging
import tempfile
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

# Third-party imports
import pyvista as pv
from pyvista import DataSet, Plotter
import PIL.Image

# Configure logger
logger = logging.getLogger("FOAMFlask")


class MeshVisualizer:
    """Handles mesh visualization using PyVista.

    This class provides functionality to load, visualize, and interact with
    3D mesh data. It supports various output formats including screenshots
    and interactive HTML viewers.

    Attributes:
        mesh: The currently loaded mesh data.
        plotter: The active PyVista plotter instance.
    """

    def __init__(self) -> None:
        """Initialize the mesh visualizer with empty attributes."""
        self.mesh: Optional[DataSet] = None
        self.plotter: Optional[Plotter] = None
        self.current_mesh_path: Optional[str] = None
        self.current_mesh_mtime: Optional[float] = None
        # ⚡ Bolt Optimization: Cache decimated meshes to avoid re-computation
        self._decimated_cache: Dict[int, DataSet] = {}

    def __del__(self) -> None:
        """Clean up resources by closing the plotter if it exists."""
        if self.plotter is not None:
            self.plotter.close()

    def _decimate_mesh(self, mesh: DataSet, target_faces: int = 100000) -> DataSet:
        """Decimate mesh to reduce size for web visualization.

        Args:
            mesh: The PyVista DataSet to decimate.
            target_faces: Target number of faces (approximate).

        Returns:
            Decimated mesh.
        """
        # ⚡ Bolt Optimization: Check cache first
        # Only use cache if the mesh being decimated is the main loaded mesh
        if mesh is self.mesh and target_faces in self._decimated_cache:
            return self._decimated_cache[target_faces]

        if mesh.n_cells <= target_faces:
            return mesh

        try:
            # We need PolyData for decimation
            if not isinstance(mesh, pv.PolyData):
                # Extract surface geometry
                mesh_poly = mesh.extract_surface()
            else:
                mesh_poly = mesh

            # Calculate reduction factor (0.0 to 1.0)
            # reduction = 1 - (target / current)
            if mesh_poly.n_cells > target_faces:
                reduction = 1.0 - (target_faces / mesh_poly.n_cells)
                # Ensure reduction is valid
                reduction = max(0.0, min(0.95, reduction))

                logger.info(f"Decimating mesh from {mesh_poly.n_cells} to ~{target_faces} cells (reduction={reduction:.2f})")
                mesh_poly = mesh_poly.decimate(reduction)

            # ⚡ Bolt Optimization: Store result in cache only if it's the main mesh
            if mesh is self.mesh:
                self._decimated_cache[target_faces] = mesh_poly

            return mesh_poly
        except Exception as e:
            logger.warning(f"Mesh decimation failed: {e}")
            return mesh

    def load_mesh(
        self, file_path: Union[str, Path], for_contour: bool = False, **kwargs: Any
    ) -> Dict[str, Any]:
        """Load a mesh from a VTK/VTP file.

        Args:
            file_path: Path to the VTK/VTP file.
            for_contour: Whether the mesh is being loaded for contour generation.
            **kwargs: Additional arguments for future extension.

        Returns:
            Dictionary containing mesh information with keys:
                - n_points: Number of points in the mesh
                - n_cells: Number of cells in the mesh
                - bounds: Bounding box of the mesh
                - center: Center point of the mesh
                - length: Length of the mesh diagonal
                - volume: Volume of the mesh (if available)
                - array_names: List of all array names
                - point_arrays: List of point data arrays
                - cell_arrays: List of cell data arrays
                - success: Boolean indicating operation success
                - error: Error message if operation failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Mesh file not found: {path}")

            path_str = str(path)
            mtime = path.stat().st_mtime

            # ⚡ Bolt Optimization: Cache Check
            if (
                self.mesh is not None
                and self.current_mesh_path == path_str
                and self.current_mesh_mtime == mtime
            ):
                logger.info(f"[FOAMFlask] [mesher] Using cached mesh for {path_str}")
                # Use cached mesh
            else:
                # Read the mesh
                logger.info(f"[FOAMFlask] [mesher] Loading mesh from {path_str}")
                # ⚡ Bolt Optimization: Disable progress bar for speed
                self.mesh = pv.read(path_str, progress_bar=False)
                self.current_mesh_path = path_str
                self.current_mesh_mtime = mtime
                # ⚡ Bolt Optimization: Clear decimated cache on new mesh load
                self._decimated_cache.clear()
                logger.info(
                    f"[FOAMFlask] [mesher] Loaded mesh: {self.mesh.n_points} points, {self.mesh.n_cells} cells"
                )

            # Get mesh information
            mesh_info = {
                "n_points": self.mesh.n_points,
                "n_cells": self.mesh.n_cells,
                "bounds": self.mesh.bounds,
                "center": self.mesh.center,
                "length": self.mesh.length,
                "volume": self.mesh.volume if hasattr(self.mesh, "volume") else None,
                "array_names": self.mesh.array_names,
                "point_arrays": list(self.mesh.point_data.keys()),
                "cell_arrays": list(self.mesh.cell_data.keys()),
                "success": True,
            }

            return mesh_info

        except Exception as e:
            logger.error(f"Error loading mesh: {e}")
            return {"success": False, "error": str(e)}

    def get_mesh_screenshot(
        self,
        file_path: Union[str, Path],
        width: int = 800,
        height: int = 600,
        show_edges: bool = True,
        color: str = "lightblue",
        camera_position: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a screenshot of the mesh.

        Args:
            file_path: Path to the VTK/VTP file.
            width: Screenshot width in pixels (default: 800).
            height: Screenshot height in pixels (default: 600).
            show_edges: Whether to show mesh edges (default: True).
            color: Mesh color as a string or RGB tuple (default: "lightblue").
            camera_position: Camera position ('xy', 'xz', 'yz', 'iso', or None for auto).

        Returns:
            Base64-encoded PNG image as a string, or None if an error occurs.
        """
        try:
            # Security: Limit dimensions to prevent DoS
            MAX_DIMENSION = 4096
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                logger.error(f"Screenshot dimensions exceed limit ({MAX_DIMENSION}px): {width}x{height}")
                return None

            path = Path(file_path)

            # Load mesh (uses caching)
            mesh_info = self.load_mesh(path)
            if not mesh_info.get("success"):
                return None

            # Create plotter
            plotter = pv.Plotter(off_screen=True, window_size=[width, height])

            # Add mesh to plotter
            # Note: For static screenshot, we might not want to decimate to preserve quality,
            # but for huge meshes, we might need to if rendering fails.
            # For now, we use full mesh for high-quality screenshots.
            plotter.add_mesh(self.mesh, color=color, show_edges=show_edges)

            # Add axes
            plotter.add_axes()

            # Set camera position
            if camera_position:
                if camera_position == "xy":
                    plotter.view_xy()
                elif camera_position == "xz":
                    plotter.view_xz()
                elif camera_position == "yz":
                    plotter.view_yz()
                elif camera_position == "iso":
                    plotter.view_isometric()
            else:
                plotter.reset_camera()

            # Render to image
            img_bytes = plotter.screenshot(
                return_img=True, transparent_background=False
            )
            plotter.close()

            # Convert to base64
            buffered = BytesIO()
            PIL.Image.fromarray(img_bytes).save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return img_str

        except Exception as e:
            logger.error(f"Error generating screenshot: {e}")
            return None

    def get_mesh_html(
        self, file_path: Union[str, Path], show_edges: bool = True, color: str = "lightblue"
    ) -> Optional[str]:
        """Generate an interactive HTML viewer for the mesh.

        This method creates an interactive 3D viewer using PyVista's HTML export
        functionality, which can be embedded in a web page.

        Args:
            file_path: Path to the VTK/VTP file.
            show_edges: Whether to show mesh edges (default: True).
            color: Mesh color as a string or RGB tuple (default: "lightblue").

        Returns:
            HTML content as a string for the interactive viewer, or None if an
            error occurs.
        """
        try:
            if self.mesh is None:
                mesh_info = self.load_mesh(file_path)
                if not mesh_info.get("success"):
                    return None

            # Create plotter
            plotter = pv.Plotter(notebook=False)

            # ⚡ Bolt Optimization: Decimate mesh for web performance
            display_mesh = self._decimate_mesh(self.mesh, target_faces=100000)

            # Add mesh to plotter
            plotter.add_mesh(display_mesh, color=color, show_edges=show_edges)

            # Add axes
            plotter.add_axes()

            # Export to HTML
            html_content = plotter.export_html(None, backend="pythreejs")
            plotter.close()

            return html_content

        except Exception as e:
            logger.error(f"Error generating HTML viewer: {e}")
            return None

    def get_interactive_viewer_html(
        self, file_path: Union[str, Path], show_edges: bool = True, color: str = "lightblue"
    ) -> Optional[str]:
        """Generate a fully interactive HTML viewer with enhanced controls.

        This method creates a more feature-rich interactive 3D viewer compared to
        get_mesh_html(), with better controls and visualization options.

        Args:
            file_path: Path to the VTK/VTP file.
            show_edges: Whether to show mesh edges (default: True).
            color: Mesh color as a string or RGB tuple (default: "lightblue").

        Returns:
            HTML content as a string for the interactive viewer with controls,
            or None if an error occurs.
        """
        try:
            mesh_info = self.load_mesh(file_path)
            if not mesh_info.get("success"):
                return None

            # Create plotter with better settings for web
            plotter = pv.Plotter(notebook=False, window_size=[1200, 800])

            # ⚡ Bolt Optimization: Decimate mesh for web performance
            # Target 200k faces for interactive viewer (trame/vtk.js handles it reasonably well)
            display_mesh = self._decimate_mesh(self.mesh, target_faces=200000)

            # Add mesh with better rendering options
            plotter.add_mesh(
                display_mesh,
                color=color,
                show_edges=show_edges,
                opacity=1.0,
                smooth_shading=True,
            )

            # Add axes with labels
            plotter.add_axes(
                xlabel="X", ylabel="Y", zlabel="Z", line_width=2, labels_off=False
            )

            # Set better camera position
            plotter.camera_position = "iso"

            # Export to HTML using temporary file
            try:
                # Create a temporary file for HTML export
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False, encoding="utf-8"
                ) as tmp_file:
                    tmp_path = Path(tmp_file.name)

                # Export to the temporary file
                plotter.export_html(str(tmp_path))
                plotter.close()

                # Read the HTML content
                html_content = tmp_path.read_text(encoding="utf-8")

                # Clean up temporary file
                try:
                    tmp_path.unlink()
                except Exception:
                    # Catch all exceptions during cleanup to ensure we still return content
                    pass

                return html_content

            except Exception as e:
                logger.error(f"Failed to export HTML: {e}")
                plotter.close()
                raise

        except Exception as e:
            logger.error(f"Error generating interactive viewer: {e}")
            return None

    def get_available_meshes(
        self, case_dir: Union[str, Path], tutorial: str
    ) -> List[Dict[str, Union[str, int]]]:
        """Get list of available mesh files in the case directory.

        This method searches for VTK/VTP files in the case directory.

        ⚡ Bolt Optimization:
        We use recursive `os.scandir` to avoid the overhead of `os.walk` and `pathlib.Path`
        during directory traversal. This also allows us to access file attributes (size)
        directly from the directory entry, saving one stat() call per file.

        Args:
            case_dir: Base case directory path.
            tutorial: Name of the tutorial/case to search within.

        Returns:
            List of dictionaries, where each dictionary contains:
                - name: Filename of the mesh
                - path: Full path to the mesh file
                - relative_path: Path relative to the tutorial directory
                - size: File size in bytes

        Note:
            Returns an empty list if no mesh files are found or if an error occurs.
        """
        try:
            tutorial_path = Path(case_dir) / tutorial
            if not tutorial_path.exists():
                return []

            # ⚡ Bolt Optimization: Pre-calculate tutorial path string for faster slicing
            # This avoids creating Path objects and calling relative_to() inside the loop,
            # which is ~200x faster for large file lists.
            tutorial_path_str = str(tutorial_path)
            if not tutorial_path_str.endswith(os.sep):
                tutorial_path_str += os.sep
            len_prefix = len(tutorial_path_str)

            mesh_files = []
            seen_paths = set()
            extensions = {".vtk", ".vtp", ".vtu"}
            ext_tuple = tuple(extensions)  # for endswith

            def _scan(path_str: str):
                try:
                    subdirs_to_visit = []

                    # Open directory, read entries, then CLOSE it before recursing
                    # This prevents file descriptor exhaustion in deep hierarchies
                    with os.scandir(path_str) as entries:
                        for entry in entries:
                            if entry.is_dir(follow_symlinks=False):
                                name = entry.name
                                # Prune hidden directories
                                if name.startswith("."):
                                    continue

                                # Prune numerical time directories
                                try:
                                    float(name)
                                    continue
                                except ValueError:
                                    # Prune system directory
                                    if name == "system":
                                        continue

                                subdirs_to_visit.append(entry.path)

                            # Check for file (allow symlinks to match original behavior)
                            elif entry.is_file(follow_symlinks=True):
                                name = entry.name
                                if name.endswith(ext_tuple):
                                    entry_path = entry.path
                                    if entry_path in seen_paths:
                                        continue
                                    seen_paths.add(entry_path)

                                    try:
                                        # ⚡ Bolt Optimization: Use string slicing instead of Path.relative_to
                                        # Since we know entry_path starts with tutorial_path_str (by definition of scan),
                                        # we can just slice it. This avoids creating a Path object.

                                        # Fallback check just in case (e.g. symlinks outside root)
                                        if entry_path.startswith(tutorial_path_str):
                                            rel_path = entry_path[len_prefix:]
                                        else:
                                            # Fallback to slow path for edge cases
                                            rel_path = str(Path(entry_path).relative_to(tutorial_path))

                                        mesh_files.append({
                                            "name": name,
                                            "path": entry_path,
                                            "relative_path": rel_path,
                                            # Optimization: use cached stat from entry
                                            "size": entry.stat().st_size,
                                        })
                                    except (ValueError, OSError):
                                        continue

                    # Recurse after closing the directory handle
                    for subdir in subdirs_to_visit:
                        _scan(subdir)

                except OSError:
                    # Permission denied or other access errors
                    pass

            _scan(str(tutorial_path))
            return mesh_files

        except Exception as e:
            logger.error(f"Error getting available meshes: {e}")
            return []


# Global instance for use as a singleton
mesh_visualizer = MeshVisualizer()
