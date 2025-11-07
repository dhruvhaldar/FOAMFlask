import logging
import os
import tempfile
import numpy as np
import pyvista as pv

# Configure logger
logger = logging.getLogger("FOAMFlask")

class IsosurfaceVisualizer:
    """
    Handles isosurface visualization from VTK mesh data using PyVista.
    
    This class provides functionality to:
    - Load VTK mesh files with scalar fields
    - Generate static isosurfaces at specified values
    - Create interactive HTML visualizations with isovalue sliders
    - Export visualization data and metadata
    
    Attributes:
        mesh (pyvista.DataSet): The loaded mesh with scalar data
        contours (pyvista.PolyData): Generated isosurface contours
        plotter (pyvista.Plotter): Active plotter instance (if any)
    """
    
    def __init__(self):
        """Initialize the isosurface visualizer."""
        self.mesh = None
        self.contours = None
        self.plotter = None
        logger.info("[FOAMFlask] [IsosurfaceVisualizer] Initialized")
    
    def load_mesh(self, file_path):
        """
        Load a mesh from a VTK file and compute derived scalar fields.
        
        Automatically computes velocity magnitude (U_Magnitude) if a velocity
        vector field (U) exists in the point data.
        
        Args:
            file_path (str): Path to the VTK/VTP/VTU file.
            
        Returns:
            dict: Mesh information including:
                - success (bool): Whether loading succeeded
                - n_points (int): Number of mesh points
                - n_cells (int): Number of mesh cells
                - bounds (tuple): Mesh spatial bounds (xmin, xmax, ymin, ymax, zmin, zmax)
                - point_arrays (list): Available point data arrays
                - cell_arrays (list): Available cell data arrays
                - u_magnitude (dict): Statistics for velocity magnitude (if U field exists)
                - error (str): Error message (if success is False)
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Mesh file not found: {file_path}")
            
            logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Loading mesh from: {file_path}")
            
            # Read the mesh with progress bar
            self.mesh = pv.read(file_path, progress_bar=True)
            logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Successfully loaded mesh: "
                       f"{self.mesh.n_points} points, {self.mesh.n_cells} cells")
            
            # Compute velocity magnitude if U vector field exists
            if 'U' in self.mesh.point_data:
                self.mesh.point_data["U_Magnitude"] = np.linalg.norm(
                    self.mesh.point_data["U"], axis=1
                )
                logger.info("[FOAMFlask] [IsosurfaceVisualizer] Computed U_Magnitude from U field")
            
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
            if 'U_Magnitude' in self.mesh.point_data:
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
                        "100": float(np.percentile(u_mag, 100))
                    }
                }
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] U_Magnitude range: "
                           f"[{mesh_info['u_magnitude']['min']:.3f}, "
                           f"{mesh_info['u_magnitude']['max']:.3f}]")
            
            return mesh_info
            
        except Exception as e:
            logger.error(f"[FOAMFlask] [IsosurfaceVisualizer] Error loading mesh: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_isosurfaces(self, scalar_field="U_Magnitude", num_isosurfaces=5, 
                            custom_range=None, isovalues=None):
        """
        Generate isosurfaces for the specified scalar field.
        
        Args:
            scalar_field (str): Name of the scalar field to create isosurfaces for.
            num_isosurfaces (int): Number of evenly-spaced isosurfaces to generate 
                                   (ignored if custom_range or isovalues is provided).
            custom_range (list): Custom [min, max] range for evenly-spaced isosurfaces.
            isovalues (list): Explicit list of isovalues to generate contours at.
            
        Returns:
            dict: Information about the generated isosurfaces including:
                - success (bool): Whether generation succeeded
                - scalar_field (str): Name of the scalar field used
                - num_isosurfaces (int): Number of isosurfaces generated
                - isovalues (list): The actual isovalue levels used
                - range (list): [min, max] range of the scalar field
                - n_points (int): Number of points in contour mesh
                - n_cells (int): Number of cells in contour mesh
                - bounds (tuple): Spatial bounds of the contours
                - error (str): Error message (if success is False)
        """
        try:
            if self.mesh is None:
                raise ValueError("No mesh loaded. Call load_mesh() first.")
            
            if scalar_field not in self.mesh.point_data:
                raise ValueError(
                    f"Scalar field '{scalar_field}' not found in point data. "
                    f"Available fields: {list(self.mesh.point_data.keys())}"
                )
            
            logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Generating isosurfaces "
                       f"for field: {scalar_field}")
            
            # Get the scalar data
            scalars = self.mesh.point_data[scalar_field]
            min_val, max_val = float(np.min(scalars)), float(np.max(scalars))
            
            # Determine isovalues to use
            if isovalues is not None:
                # Explicit isovalues provided
                values = np.array(isovalues)
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Using explicit isovalues: {values}")
            elif custom_range is not None:
                # Custom range for evenly-spaced values
                if len(custom_range) != 2:
                    raise ValueError("custom_range must be a list of [min, max] values.")
                values = np.linspace(custom_range[0], custom_range[1], num_isosurfaces)
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Using custom range: "
                           f"{custom_range} with {num_isosurfaces} isosurfaces")
            else:
                # Default: evenly-spaced values across full range (excluding extremes)
                values = np.linspace(min_val, max_val, num_isosurfaces + 2)[1:-1]
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Using {num_isosurfaces} "
                           f"evenly-spaced isosurfaces in range [{min_val:.3f}, {max_val:.3f}]")
            
            # Generate isosurfaces using contour filter
            self.contours = self.mesh.contour(
                isosurfaces=values.tolist(),
                scalars=scalar_field
            )
            
            result = {
                "success": True,
                "scalar_field": scalar_field,
                "num_isosurfaces": len(values),
                "isovalues": [float(v) for v in values],
                "range": [min_val, max_val],
                "n_points": int(self.contours.n_points),
                "n_cells": int(self.contours.n_cells),
                "bounds": tuple(float(b) for b in self.contours.bounds)
            }
            
            logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Generated {result['num_isosurfaces']} "
                       f"isosurfaces: {result['n_points']} points, {result['n_cells']} cells")
            
            return result
            
        except Exception as e:
            logger.error(f"[FOAMFlask] [IsosurfaceVisualizer] Error generating isosurfaces: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_scalar_field_info(self, scalar_field=None):
        """
        Get statistical information about scalar fields in the mesh.
        
        Args:
            scalar_field (str, optional): Specific field to get info for. 
                                         If None, returns info for all fields.
        
        Returns:
            dict: Dictionary with scalar field statistics.
        """
        try:
            if self.mesh is None:
                raise ValueError("No mesh loaded. Call load_mesh() first.")
            
            result = {}
            
            # Determine which fields to process
            if scalar_field:
                if scalar_field not in self.mesh.point_data:
                    raise ValueError(f"Scalar field '{scalar_field}' not found in point data.")
                fields = [scalar_field]
            else:
                fields = list(self.mesh.point_data.keys())
            
            # Compute statistics for each field
            for field in fields:
                data = self.mesh.point_data[field]
                
                # Handle vector fields vs scalar fields
                if len(data.shape) > 1:
                    # Vector field - compute magnitude
                    magnitude = np.linalg.norm(data, axis=1)
                    result[field] = {
                        "type": "vector",
                        "shape": data.shape,
                        "magnitude_stats": {
                            "min": float(np.min(magnitude)),
                            "max": float(np.max(magnitude)),
                            "mean": float(np.mean(magnitude)),
                            "std": float(np.std(magnitude))
                        }
                    }
                else:
                    # Scalar field
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
                            "100": float(np.percentile(data, 100))
                        }
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"[FOAMFlask] [IsosurfaceVisualizer] Error getting field info: {e}")
            return {"error": str(e)}
    
    def get_interactive_html(self, scalar_field="U_Magnitude", show_base_mesh=True, 
                            base_mesh_opacity=0.25, contour_opacity=0.8, 
                            contour_color='red', colormap='viridis', 
                            show_isovalue_slider=True, custom_range=None,
                            num_isosurfaces=5, isovalues=None,
                            window_size=(1200, 800)):
        """
        Generate a fully interactive HTML viewer for isosurfaces.
        
        Creates an HTML file with an interactive 3D visualization that can include:
        - The base mesh with scalar field coloring
        - Static isosurfaces at specified values
        - Interactive isovalue slider for dynamic exploration
        
        Args:
            scalar_field (str): Name of the scalar field to visualize (default: "U_Magnitude").
            show_base_mesh (bool): Whether to show the base mesh with transparency (default: True).
            base_mesh_opacity (float): Opacity of the base mesh (0.0 to 1.0, default: 0.25).
            contour_opacity (float): Opacity of the contour surfaces (0.0 to 1.0, default: 0.8).
            contour_color (str): Color for the contour surfaces (default: 'red').
            colormap (str): Colormap for the base mesh scalars (default: 'viridis').
            show_isovalue_slider (bool): Whether to add an interactive isovalue slider (default: True).
            custom_range (list): Custom [min, max] range for isosurfaces (optional).
            num_isosurfaces (int): Number of isosurfaces for static mode (default: 5).
            isovalues (list): Explicit list of isovalue levels for static mode (optional).
            window_size (tuple): Window size as (width, height) in pixels (default: (1200, 800)).
            
        Returns:
            str: HTML content for interactive viewer with controls.
        """
        try:
            # Validate that mesh is loaded
            if self.mesh is None:
                raise ValueError("No mesh loaded. Call load_mesh() first.")
            
            # Validate scalar field exists
            if scalar_field not in self.mesh.point_data:
                raise ValueError(
                    f"Scalar field '{scalar_field}' not found in point data. "
                    f"Available fields: {list(self.mesh.point_data.keys())}"
                )
            
            logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                       f"Creating interactive viewer for '{scalar_field}'")
            
            # Create plotter with specified window size
            plotter = pv.Plotter(notebook=False, window_size=list(window_size))
            
            # Add base mesh if requested
            if show_base_mesh:
                plotter.add_mesh(
                    self.mesh, 
                    opacity=base_mesh_opacity, 
                    scalars=scalar_field,
                    show_scalar_bar=True,
                    cmap=colormap,
                    label='Base Mesh',
                    scalar_bar_args={
                        'title': scalar_field,
                        'title_font_size': 20,
                        'label_font_size': 16,
                        'shadow': True,
                        'n_labels': 5,
                        'fmt': '%.2f',
                        'position_x': 0.85,
                        'position_y': 0.05
                    }
                )
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                           f"Added base mesh with opacity {base_mesh_opacity}")
            
            # Add isosurfaces with slider OR static contours
            if show_isovalue_slider:
                # Add interactive isovalue slider
                plotter.add_mesh_isovalue(
                    self.mesh, 
                    scalars=scalar_field,
                    compute_normals=True,
                    compute_gradients=False,
                    compute_scalars=True,
                    opacity=contour_opacity,
                    color=contour_color,
                    show_scalar_bar=False,
                    smooth_shading=True
                )
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                           f"Added interactive isovalue slider")
            else:
                # Generate static contours
                result = self.generate_isosurfaces(
                    scalar_field=scalar_field,
                    num_isosurfaces=num_isosurfaces,
                    custom_range=custom_range,
                    isovalues=isovalues
                )
                
                if not result.get("success"):
                    raise ValueError(f"Failed to generate isosurfaces: {result.get('error')}")
                
                if self.contours is not None and self.contours.n_points > 0:
                    plotter.add_mesh(
                        self.contours, 
                        opacity=contour_opacity,
                        show_scalar_bar=False,
                        color=contour_color,
                        label='Isosurfaces',
                        smooth_shading=True
                    )
                    logger.info(
                        f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                        f"Added {result['num_isosurfaces']} static isosurfaces "
                        f"({self.contours.n_points} points, {self.contours.n_cells} cells)"
                    )
                else:
                    logger.warning("[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                                 "No contour points generated")
            
            # Add axes with labels
            plotter.add_axes(
                xlabel='X',
                ylabel='Y',
                zlabel='Z',
                line_width=2,
                labels_off=False
            )
            
            # Set isometric camera position for better initial view
            plotter.camera_position = 'iso'
            plotter.reset_camera()
            
            # Export to HTML using temporary file
            temp_path = None
            try:
                # Create a temporary file for HTML export
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.html', 
                    delete=False, 
                    encoding='utf-8'
                ) as tmp_file:
                    temp_path = tmp_file.name
                
                logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                           f"Exporting to temporary file: {temp_path}")
                
                # Export to the temporary file
                plotter.export_html(temp_path)
                
                # Read the HTML content
                with open(temp_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                logger.info(
                    f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                    f"Generated HTML content: {len(html_content)} bytes"
                )
                
                return html_content
                
            except Exception as e:
                logger.error(f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                           f"Error during HTML export: {str(e)}")
                raise
                
            finally:
                # Clean up temporary file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                        logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                                   f"Cleaned up temporary file")
                    except Exception as cleanup_error:
                        logger.warning(
                            f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                            f"Failed to clean up temporary file: {cleanup_error}"
                        )
                
                # Always close the plotter
                plotter.close()
                
        except Exception as e:
            logger.error(f"[FOAMFlask] [IsosurfaceVisualizer] [get_interactive_html] "
                        f"Failed to generate HTML viewer: {e}")
            
            # Clean up plotter if it exists
            if 'plotter' in locals():
                plotter.close()
            
            # Return a user-friendly error message as HTML
            return self._generate_error_html(str(e), scalar_field)
    
    def _generate_error_html(self, error_message, scalar_field=""):
        """
        Generate a user-friendly HTML error page.
        
        Args:
            error_message (str): The error message to display.
            scalar_field (str): The scalar field that was being processed.
            
        Returns:
            str: HTML content with formatted error message.
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Visualization Error</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }}
                .error-icon {{
                    font-size: 32px;
                }}
                .error-message {{
                    color: #721c24;
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    padding: 20px;
                    border-radius: 6px;
                    margin: 20px 0;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    word-wrap: break-word;
                }}
                .help-text {{
                    color: #666;
                    font-size: 15px;
                    line-height: 1.6;
                    margin-top: 20px;
                }}
                .help-text ul {{
                    margin: 15px 0;
                    padding-left: 20px;
                }}
                .help-text li {{
                    margin: 10px 0;
                    padding: 8px;
                    background: #f8f9fa;
                    border-radius: 4px;
                }}
                .help-text code {{
                    background: #e9ecef;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }}
                .timestamp {{
                    color: #999;
                    font-size: 12px;
                    margin-top: 20px;
                    text-align: right;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h2>
                    <span class="error-icon">⚠️</span>
                    Error Generating 3D Visualization
                </h2>
                <div class="error-message">
                    <strong>Error:</strong><br>
                    {error_message}
                </div>
                <div class="help-text">
                    <p><strong>Troubleshooting steps:</strong></p>
                    <ul>
                        <li>Ensure the mesh file has been loaded correctly with <code>load_mesh()</code></li>
                        <li>Verify that the scalar field <code>'{scalar_field}'</code> exists in the mesh point data</li>
                        <li>Check that PyVista and trame are properly installed: <code>pip install pyvista[all] trame</code></li>
                        <li>Ensure the mesh contains valid point data (not just cell data)</li>
                        <li>Review the server logs for detailed error information and stack traces</li>
                        <li>Try loading the mesh manually to verify file integrity</li>
                    </ul>
                    <p><strong>Available debugging information:</strong></p>
                    <ul>
                        <li>Check <code>get_scalar_field_info()</code> to see available fields</li>
                        <li>Use <code>load_mesh()</code> to get mesh statistics</li>
                        <li>Verify the mesh has point data, not just cell data</li>
                    </ul>
                </div>
                <div class="timestamp">
                    Generated at {tempfile.gettempdir()}
                </div>
            </div>
        </body>
        </html>
        """
    
    def export_contours(self, output_path, file_format='vtk'):
        """
        Export generated contours to a file.
        
        Args:
            output_path (str): Path to save the contour mesh.
            file_format (str): Output format ('vtk', 'vtp', 'stl', 'ply').
            
        Returns:
            dict: Export status and information.
        """
        try:
            if self.contours is None:
                raise ValueError("No contours generated. Call generate_isosurfaces() first.")
            
            # Ensure output path has correct extension
            if not output_path.endswith(f'.{file_format}'):
                output_path = f"{output_path}.{file_format}"
            
            # Save the contours
            self.contours.save(output_path)
            
            logger.info(f"[FOAMFlask] [IsosurfaceVisualizer] Exported contours to: {output_path}")
            
            return {
                "success": True,
                "output_path": output_path,
                "file_size": os.path.getsize(output_path),
                "format": file_format
            }
            
        except Exception as e:
            logger.error(f"[FOAMFlask] [IsosurfaceVisualizer] Error exporting contours: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'plotter') and self.plotter is not None:
            try:
                self.plotter.close()
                logger.info("[FOAMFlask] [IsosurfaceVisualizer] Cleaned up plotter resources")
            except:
                pass


# Global instance
isosurface_visualizer = IsosurfaceVisualizer()
