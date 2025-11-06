"""
PyVista handler module for mesh visualization in FOAMFlask.
Provides functionality to load and visualize VTK/VTP mesh files using PyVista.
"""

import os
import logging
import base64
import tempfile
import numpy as np
from io import BytesIO
import pyvista as pv

logger = logging.getLogger("FOAMFlask.PyVista")


class MeshVisualizer:
    """
    Handles mesh visualization using PyVista.
    """
    
    def __init__(self):
        """Initialize the mesh visualizer."""
        self.mesh = None
        self.plotter = None
        
    def __del__(self):
        """Clean up resources."""
        if self.plotter is not None:
            self.plotter.close()

    def load_mesh(self, file_path):
        """
        Load a mesh from a VTK/VTP file.
        
        Args:
            file_path (str): Path to the VTK/VTP file.
            
        Returns:
            dict: Mesh information including bounds, number of points, cells, etc.
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Mesh file not found: {file_path}")
            
            # Read the mesh
            self.mesh = pv.read(file_path)
            logger.info(f"Loaded mesh from {file_path}")
            
            # Get mesh information
            mesh_info = {
                "n_points": self.mesh.n_points,
                "n_cells": self.mesh.n_cells,
                "bounds": self.mesh.bounds,
                "center": self.mesh.center,
                "length": self.mesh.length,
                "volume": self.mesh.volume if hasattr(self.mesh, 'volume') else None,
                "array_names": self.mesh.array_names,
                "success": True
            }
            
            return mesh_info
            
        except Exception as e:
            logger.error(f"Error loading mesh: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_mesh_screenshot(self, file_path, width=800, height=600, 
                           show_edges=True, color="lightblue", 
                           camera_position=None):
        """
        Generate a screenshot of the mesh.
        
        Args:
            file_path (str): Path to the VTK/VTP file.
            width (int): Screenshot width in pixels.
            height (int): Screenshot height in pixels.
            show_edges (bool): Whether to show mesh edges.
            color (str): Mesh color.
            camera_position (str): Camera position ('xy', 'xz', 'yz', 'iso', or None for auto).
            
        Returns:
            str: Base64-encoded PNG image.
        """
        try:
            # Load mesh if not already loaded
            if self.mesh is None or not os.path.exists(file_path):
                mesh_info = self.load_mesh(file_path)
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
                if camera_position == 'xy':
                    plotter.view_xy()
                elif camera_position == 'xz':
                    plotter.view_xz()
                elif camera_position == 'yz':
                    plotter.view_yz()
                elif camera_position == 'iso':
                    plotter.view_isometric()
            else:
                plotter.reset_camera()
            
            # Render to image
            img_bytes = plotter.screenshot(return_img=True, transparent_background=False)
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
    
    def get_mesh_html(self, file_path, show_edges=True, color="lightblue"):
        """
        Generate an interactive HTML viewer for the mesh using PyVista's HTML export.
        
        Args:
            file_path (str): Path to the VTK/VTP file.
            show_edges (bool): Whether to show mesh edges.
            color (str): Mesh color.
            
        Returns:
            str: HTML content for interactive viewer.
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
            html_content = plotter.export_html(None, backend='pythreejs')
            plotter.close()
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating HTML viewer: {e}")
            return None
    
    def get_interactive_viewer_html(self, file_path, show_edges=True, color="lightblue"):
        """
        Generate a fully interactive HTML viewer with better controls.
        Uses PyVista's export_html with enhanced settings.
        
        Args:
            file_path (str): Path to the VTK/VTP file.
            show_edges (bool): Whether to show mesh edges.
            color (str): Mesh color.
            
        Returns:
            str: HTML content for interactive viewer with controls.
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
                smooth_shading=True
            )
            
            # Add axes with labels
            plotter.add_axes(
                xlabel='X',
                ylabel='Y',
                zlabel='Z',
                line_width=2,
                labels_off=False
            )
            
            # Set better camera position
            plotter.camera_position = 'iso'
            
            # Export to HTML using temporary file
            try:
                # Create a temporary file for HTML export
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                    tmp_path = tmp_file.name
                
                # Export to the temporary file
                plotter.export_html(tmp_path)
                plotter.close()
                
                # Read the HTML content
                with open(tmp_path, 'r', encoding='utf-8') as f:
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
    
    def get_available_meshes(self, case_dir, tutorial):
        """
        Get list of available mesh files in the case directory.
        
        Args:
            case_dir (str): Base case directory.
            tutorial (str): Tutorial name.
            
        Returns:
            list: List of available mesh files with their paths.
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
                        if file.endswith(('.vtk', '.vtp', '.vtu')):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, tutorial_path)
                            mesh_files.append({
                                "name": file,
                                "path": full_path,
                                "relative_path": rel_path,
                                "size": os.path.getsize(full_path)
                            })
            
            return mesh_files
            
        except Exception as e:
            logger.error(f"Failed to export HTML: {e}")
            if 'plotter' in locals():
                plotter.close()
            raise
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'plotter') and self.plotter is not None:
            self.plotter.close()




class IsosurfaceVisualizer:
    """
    Handles isosurface visualization from VTK mesh data using PyVista.
    """
    
    def __init__(self):
        """Initialize the isosurface visualizer."""
        self.mesh = None
        self.contours = None
        self.plotter = None
    
    def load_mesh(self, file_path):
        """
        Load a mesh from a VTK file and compute velocity magnitude.
        
        Args:
            file_path (str): Path to the VTK file.
            
        Returns:
            dict: Mesh information including bounds, number of points, arrays, etc.
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Mesh file not found: {file_path}")
            
            # Read the mesh
            self.mesh = pv.read(file_path, progress_bar=True)
            logger.info(f"Loaded mesh from {file_path}")
            
            # Compute velocity magnitude if U vector field exists
            if 'U' in self.mesh.point_data:
                self.mesh.point_data["U_Magnitude"] = np.linalg.norm(
                    self.mesh.point_data["U"], axis=1
                )
            
            # Get mesh information
            mesh_info = {
                "n_points": self.mesh.n_points,
                "n_cells": self.mesh.n_cells,
                "bounds": self.mesh.bounds,
                "point_arrays": list(self.mesh.point_data.keys()),
                "cell_arrays": list(self.mesh.cell_data.keys()),
                "success": True
            }
            
            if 'U_Magnitude' in self.mesh.point_data:
                u_mag = self.mesh.point_data["U_Magnitude"]
                mesh_info["u_magnitude"] = {
                    "min": float(np.min(u_mag)),
                    "max": float(np.max(u_mag)),
                    "mean": float(np.mean(u_mag)),
                    "percentiles": [float(x) for x in np.percentile(u_mag, [0, 25, 50, 75, 100])]
                }
            
            return mesh_info
            
        except Exception as e:
            logger.error(f"Error loading mesh: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_isosurfaces(self, scalar_field="U_Magnitude", num_isosurfaces=5, custom_range=None):
        """
        Generate isosurfaces for the specified scalar field.
        
        Args:
            scalar_field (str): Name of the scalar field to create isosurfaces for.
            num_isosurfaces (int): Number of isosurfaces to generate (ignored if custom_range is provided).
            custom_range (list): Custom [min, max] range for isosurfaces.
            
        Returns:
            dict: Information about the generated isosurfaces.
        """
        try:
            if self.mesh is None:
                raise ValueError("No mesh loaded. Call load_mesh() first.")
            
            if scalar_field not in self.mesh.point_data:
                raise ValueError(f"Scalar field '{scalar_field}' not found in point data.")
            
            # Get the scalar data
            scalars = self.mesh.point_data[scalar_field]
            
            # Determine range for isosurfaces
            if custom_range is not None:
                if len(custom_range) != 2:
                    raise ValueError("custom_range must be a list of [min, max] values.")
                min_val, max_val = custom_range
                values = custom_range
            else:
                min_val, max_val = np.min(scalars), np.max(scalars)
                # Generate evenly spaced values between min and max
                values = np.linspace(min_val, max_val, num_isosurfaces + 2)[1:-1]
            
            # Generate isosurfaces
            self.contours = self.mesh.contour(
                values,
                scalars=scalar_field
            )
            
            return {
                "success": True,
                "scalar_field": scalar_field,
                "num_isosurfaces": len(values),
                "range": [float(min_val), float(max_val)],
                "n_points": self.contours.n_points,
                "n_cells": self.contours.n_cells,
                "bounds": self.contours.bounds
            }
            
        except Exception as e:
            logger.error(f"Error generating isosurfaces: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_plotter(self, show_mesh=True, show_contours=True, mesh_opacity=0.25, 
                   contour_opacity=0.8, cmap='viridis', window_size=(1200, 800)):
        """
        Get a PyVista plotter with the mesh and isosurfaces.
        
        Args:
            show_mesh (bool): Whether to show the original mesh.
            show_contours (bool): Whether to show the isosurfaces.
            mesh_opacity (float): Opacity of the original mesh (0-1).
            contour_opacity (float): Opacity of the isosurfaces (0-1).
            cmap (str): Colormap to use for the mesh.
            window_size (tuple): Window size as (width, height).
            
        Returns:
            pv.Plotter: Configured PyVista plotter.
        """
        if self.plotter is not None:
            self.plotter.close()
            
        self.plotter = pv.Plotter(window_size=window_size)
        
        if show_mesh and self.mesh is not None:
            self.plotter.add_mesh(
                self.mesh, 
                opacity=mesh_opacity, 
                scalars="U_Magnitude" if "U_Magnitude" in self.mesh.point_data else None,
                show_scalar_bar=True,
                cmap=cmap
            )
        
        if show_contours and self.contours is not None:
            self.plotter.add_mesh(
                self.contours,
                opacity=contour_opacity,
                show_scalar_bar=False,
                color='red'
            )
        
        # Add interactive isosurface widget if mesh and scalar field are available
        if self.mesh is not None and "U_Magnitude" in self.mesh.point_data:
            self.plotter.add_mesh_isovalue(
                self.mesh,
                scalars="U_Magnitude",
                color='blue',
                line_width=3
            )
        
        # Add axes and other decorations
        self.plotter.add_axes()
        self.plotter.add_bounding_box()
        
        return self.plotter
    
    def show_plot(self, **kwargs):
        """
        Show the interactive plot.
        
        Args:
            **kwargs: Additional arguments to pass to get_plotter().
        """
        plotter = self.get_plotter(**kwargs)
        plotter.show()
    
    def get_screenshot(self, output_path=None, **kwargs):
        """
        Get a screenshot of the current plot.
        
        Args:
            output_path (str, optional): Path to save the screenshot. If None, returns the image as bytes.
            **kwargs: Additional arguments to pass to get_plotter().
            
        Returns:
            bytes or None: Image data if output_path is None, otherwise None.
        """
        plotter = self.get_plotter(off_screen=True, **kwargs)
        if output_path:
            plotter.screenshot(output_path)
            return None
        else:
            return plotter.screenshot(return_img=True)
    
    def get_interactive_html(self, **kwargs):
        """
        Generate an interactive HTML viewer with the mesh and isosurfaces.
        
        Args:
            **kwargs: Additional arguments to pass to get_plotter().
                - notebook (bool): Whether to use notebook mode (ignored, kept for compatibility).
                - Other arguments are passed to get_plotter().
            
        Returns:
            str: HTML content for the interactive viewer.
        """
        # Remove notebook parameter if it exists to avoid passing it to get_plotter
        kwargs.pop('notebook', None)
        plotter = self.get_plotter(**kwargs)
        
        # Export to HTML using temporary file
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                tmp_path = tmp_file.name
            
            # Export to the temporary file
            plotter.export_html(tmp_path)
            plotter.close()
            
            # Read the HTML content
            with open(tmp_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to export HTML: {e}")
            if 'plotter' in locals():
                plotter.close()
            raise
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'plotter') and self.plotter is not None:
            self.plotter.close()


# Global instances
mesh_visualizer = MeshVisualizer()
isosurface_visualizer = IsosurfaceVisualizer()
