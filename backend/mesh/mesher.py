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

    def __del__(self) -> None:
        """Clean up resources by closing the plotter if it exists."""
        if self.plotter is not None:
            self.plotter.close()

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

            # Read the mesh
            logger.info("[FOAMFlask] [backend] [mesh] [mesher.py] [load_mesh]")
            self.mesh = pv.read(str(path), progress_bar=True)
            logger.info(
                f"[FOAMFlask] [backend] [mesh] [mesher.py] [load_mesh] Loaded mesh from {path}"
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
            path = Path(file_path)

            # Load mesh if not already loaded or if a different file is requested
            # Note: Checking path equality naively; in a robust system we might want to track current path
            if self.mesh is None or not path.exists():
                # We reuse load_mesh logic, though technically if self.mesh is None we load it.
                # If path exists but self.mesh corresponds to another file, we rely on caller or just reload.
                # For simplicity, let's just reload if needed.
                mesh_info = self.load_mesh(path)
                if not mesh_info.get("success"):
                    return None

            # Create plotter
            plotter = pv.Plotter(off_screen=True, window_size=[width, height])

            # Add mesh to plotter
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

            # Add mesh to plotter
            plotter.add_mesh(self.mesh, color=color, show_edges=show_edges)

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
            if self.mesh is None:
                mesh_info = self.load_mesh(file_path)
                if not mesh_info.get("success"):
                    return None

            # Create plotter with better settings for web
            plotter = pv.Plotter(notebook=False, window_size=[1200, 800])

            # Add mesh with better rendering options
            plotter.add_mesh(
                self.mesh,
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
        We use `os.walk` with directory pruning to avoid scanning the thousands of time
        directories common in OpenFOAM cases (e.g., 0, 0.1, 100, etc.).
        This allows us to find meshes in nested folders (e.g. `VTK/`, `postProcessing/`, `custom/subdir`)
        without paying the penalty of visiting every single time step directory.

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

            mesh_files = []
            seen_paths = set()
            # Use a set for faster lookup
            extensions = {".vtk", ".vtp", ".vtu"}

            # Walk the directory tree
            for root, dirs, files in os.walk(str(tutorial_path)):
                # Prune directories in-place to optimize scan
                # We iterate a copy of dirs to allow modification
                for d in list(dirs):
                    # Skip hidden directories
                    if d.startswith("."):
                        dirs.remove(d)
                        continue

                    # ⚡ Bolt Optimization: Skip time directories
                    # OpenFOAM time directories are numeric (e.g., "0", "0.1", "100")
                    # We prune them to avoid scanning thousands of field files.
                    try:
                        float(d)
                        # It's a number, likely a time directory. Prune it.
                        dirs.remove(d)
                    except ValueError:
                        # Not a number. Keep it, unless it's a known non-mesh source
                        if d in ["system"]:
                            dirs.remove(d)

                root_path = Path(root)
                for file in files:
                    if Path(file).suffix in extensions:
                        file_path = root_path / file
                        path_str = str(file_path)

                        if path_str in seen_paths:
                            continue

                        seen_paths.add(path_str)
                        try:
                            rel_path = file_path.relative_to(tutorial_path)
                            mesh_files.append(
                                {
                                    "name": file_path.name,
                                    "path": path_str,
                                    "relative_path": str(rel_path),
                                    "size": file_path.stat().st_size,
                                }
                            )
                        except (ValueError, OSError):
                            continue

            return mesh_files

        except Exception as e:
            logger.error(f"Error getting available meshes: {e}")
            return []


# Global instance for use as a singleton
mesh_visualizer = MeshVisualizer()
