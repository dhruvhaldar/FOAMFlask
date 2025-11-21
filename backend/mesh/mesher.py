"""PyVista handler module for mesh visualization in FOAMFlask.

This module provides functionality to load and visualize VTK/VTP mesh files using PyVista.
It includes features for generating screenshots, interactive HTML viewers, and managing
mesh data for visualization purposes.
"""

# Standard library imports
import base64
import logging
import os
import tempfile
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Union, Any, BinaryIO

# Third-party imports
import numpy as np
import pyvista as pv
from pyvista import DataSet, Plotter

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
        self, file_path: str, for_contour: bool = False, **kwargs: Any
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

        Raises:
            FileNotFoundError: If the specified file does not exist.
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Mesh file not found: {file_path}")

            # Read the mesh
            logger.info("[FOAMFlask] [backend] [mesh] [mesher.py] [load_mesh]")
            self.mesh = pv.read(file_path, progress_bar=True)
            logger.info(
                f"[FOAMFlask] [backend] [mesh] [mesher.py] [load_mesh] Loaded mesh from {file_path}"
            )

            # Get mesh information
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
        file_path: str,
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

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the camera position is invalid.
        """
        try:
            # Load mesh if not already loaded
            if self.mesh is None or not os.path.exists(file_path):
                mesh_info = self.load_mesh(file_path, for_contour=for_contour)
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
            import PIL.Image

            PIL.Image.fromarray(img_bytes).save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return img_str

        except Exception as e:
            logger.error(f"Error generating screenshot: {e}")
            return None

    def get_mesh_html(
        self, file_path: str, show_edges: bool = True, color: str = "lightblue"
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

        Raises:
            FileNotFoundError: If the specified file does not exist.
        """
        try:
            # Load mesh if not already loaded
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
        self, file_path: str, show_edges: bool = True, color: str = "lightblue"
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

        Raises:
            FileNotFoundError: If the specified file does not exist.
            RuntimeError: If there's an error generating the HTML content.
        """
        try:
            # Load mesh if not already loaded
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
                    tmp_path = tmp_file.name

                # Export to the temporary file
                plotter.export_html(tmp_path)
                plotter.close()

                # Read the HTML content
                with open(tmp_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except:
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
        self, case_dir: str, tutorial: str
    ) -> List[Dict[str, Union[str, int]]]:
        """Get list of available mesh files in the case directory.

        This method searches for VTK/VTP files in common OpenFOAM case
        directories and returns information about each found mesh file.

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
            tutorial_path = os.path.join(case_dir, tutorial)
            if not os.path.exists(tutorial_path):
                return []

            mesh_files = []

            # Common locations for mesh files in OpenFOAM cases
            search_dirs = [
                tutorial_path,
                os.path.join(tutorial_path, "VTK"),
                os.path.join(tutorial_path, "postProcessing"),
            ]

            # Search for VTK/VTP files
            for search_dir in search_dirs:
                if not os.path.exists(search_dir):
                    continue

                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        if file.endswith((".vtk", ".vtp", ".vtu")):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, tutorial_path)
                            mesh_files.append(
                                {
                                    "name": file,
                                    "path": full_path,
                                    "relative_path": rel_path,
                                    "size": os.path.getsize(full_path),
                                }
                            )

            return mesh_files

        except Exception as e:
            logger.error(f"Failed to export HTML: {e}")
            if "plotter" in locals():
                plotter.close()
            raise

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, "plotter") and self.plotter is not None:
            self.plotter.close()

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, "plotter") and self.plotter is not None:
            self.plotter.close()


# Global instance for use as a singleton
mesh_visualizer = MeshVisualizer()
