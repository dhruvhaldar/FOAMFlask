import logging
import pyvista as pv
from pathlib import Path
from typing import Optional, Union, Dict, Any
import multiprocessing
import tempfile
import os
import gzip
import shutil

logger = logging.getLogger("FOAMFlask")

ALLOWED_EXTENSIONS = {'.stl', '.obj', '.obj.gz', '.ply', '.vtp', '.vtu', '.g'}

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

        mesh = pv.read(read_path)
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

            # Create a temp file for the output
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                temp_output_path = tmp.name

            # Run generation in a separate process
            p = multiprocessing.Process(
                target=_generate_html_process,
                args=(str(path), temp_output_path, color, opacity)
            )
            p.start()
            p.join(timeout=30) # Wait up to 30 seconds

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

                mesh = pv.read(read_path)
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
