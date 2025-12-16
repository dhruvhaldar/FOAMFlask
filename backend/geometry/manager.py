import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union
from werkzeug.utils import secure_filename
from backend.security import validate_path, safe_join

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
            # case_path is assumed validated by caller, but we use safe_join to be sure about subpaths
            path = Path(case_path).resolve()

            if not path.exists():
                 return {"success": False, "message": "Case directory does not exist."}

            # Use safe_join to construct triSurface path
            tri_surface_dir = safe_join(path, "constant", "triSurface")

            # Ensure triSurface dir exists (validate_path/safe_join might return it even if not exists if allow_new=True,
            # but here we want to create it if missing)
            if not tri_surface_dir.exists():
                tri_surface_dir.mkdir(parents=True, exist_ok=True)

            safe_filename = secure_filename(filename)
            allowed_extensions = (".stl", ".obj", ".gz")
            if not any(safe_filename.lower().endswith(ext) for ext in allowed_extensions):
                 return {"success": False, "message": "Only .stl, .obj, and .gz files are allowed."}

            # Use safe_join for the file path
            filepath = safe_join(tri_surface_dir, safe_filename)

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
            tri_surface_dir = safe_join(path, "constant", "triSurface")

            if not tri_surface_dir.exists():
                return {"success": True, "files": []}

            # List .stl, .obj, and .gz files
            files = [
                f.name for f in tri_surface_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in [".stl", ".obj", ".gz"]
            ]
            return {"success": True, "files": sorted(files)}

        except Exception as e:
            logger.error(f"Error listing STLs: {e}")
            return {"success": False, "message": "An internal error occurred."}

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

            safe_filename = secure_filename(filename)
            filepath = safe_join(path, "constant", "triSurface", safe_filename)

            if not filepath.exists():
                return {"success": False, "message": "File not found."}

            os.remove(filepath)
            logger.info(f"Deleted STL {filepath}")
            return {"success": True, "message": "File deleted successfully."}

        except Exception as e:
            logger.error(f"Error deleting STL: {e}")
            return {"success": False, "message": "An internal error occurred."}
