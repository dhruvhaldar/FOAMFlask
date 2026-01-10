import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union
from werkzeug.utils import secure_filename

logger = logging.getLogger("FOAMFlask")

class GeometryManager:
    """Manages geometry files (STL) in the OpenFOAM case."""

    @staticmethod
    def upload_stl(case_path: Union[str, Path], file, filename: str) -> Dict[str, Union[bool, str]]:
        """
        Save an uploaded STL file to the constant/triSurface directory.

        Args:
            case_path: Path to the case directory.
            file: File object from the request.
            filename: Name of the file.

        Returns:
            Dictionary with success status and message.
        """
        try:
            path = Path(case_path).resolve()
            tri_surface_dir = path / "constant" / "triSurface"
            tri_surface_dir.mkdir(parents=True, exist_ok=True)

            safe_filename = secure_filename(filename)
            allowed_extensions = (".stl", ".obj", ".gz")
            if not any(safe_filename.lower().endswith(ext) for ext in allowed_extensions):
                 return {"success": False, "message": "Only .stl, .obj, and .gz files are allowed."}

            filepath = tri_surface_dir / safe_filename
            file.save(str(filepath))

            logger.info(f"Uploaded Geometry to {filepath}")
            return {"success": True, "message": "File uploaded successfully.", "filename": safe_filename}

        except Exception as e:
            logger.error(f"Error uploading Geometry: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def list_stls(case_path: Union[str, Path]) -> Dict[str, Union[bool, List[str], str]]:
        """
        List all geometry files in the constant/triSurface directory.

        Args:
            case_path: Path to the case directory.

        Returns:
            Dictionary with success status and list of filenames.
        """
        try:
            path = Path(case_path).resolve()
            tri_surface_dir = path / "constant" / "triSurface"

            if not tri_surface_dir.exists():
                return {"success": True, "files": []}

            # List .stl, .obj, and .gz files
            # ⚡ Bolt Optimization: Use os.scandir instead of Path.iterdir()
            # Significantly faster for directories with many files
            files = []
            allowed_extensions = {".stl", ".obj", ".gz"}

            try:
                with os.scandir(str(tri_surface_dir)) as entries:
                    for entry in entries:
                        if entry.is_file():
                            # Check extension efficiently
                            name = entry.name
                            ext = os.path.splitext(name)[1].lower()
                            if ext in allowed_extensions:
                                files.append(name)
            except OSError:
                pass # Directory might have been deleted concurrently

            return {"success": True, "files": sorted(files)}

        except Exception as e:
            logger.error(f"Error listing STLs: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def delete_stl(case_path: Union[str, Path], filename: str) -> Dict[str, Union[bool, str]]:
        """
        Delete an STL file from the constant/triSurface directory.

        Args:
            case_path: Path to the case directory.
            filename: Name of the file to delete.

        Returns:
            Dictionary with success status and message.
        """
        try:
            path = Path(case_path).resolve()
            filepath = path / "constant" / "triSurface" / secure_filename(filename)

            if not filepath.exists():
                return {"success": False, "message": "File not found."}

            os.remove(filepath)
            logger.info(f"Deleted STL {filepath}")
            return {"success": True, "message": "File deleted successfully."}

        except Exception as e:
            logger.error(f"Error deleting STL: {e}")
            return {"success": False, "message": str(e)}
