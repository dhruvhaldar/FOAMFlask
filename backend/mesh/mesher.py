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


    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'plotter') and self.plotter is not None:
            self.plotter.close()


# Global instances
mesh_visualizer = MeshVisualizer()
