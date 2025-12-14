import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union
from werkzeug.utils import secure_filename
from backend.security import validate_path

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
            # Validate case_path (ensure it's safe - caller should have done it, but double check doesn't hurt if we knew base)
            # Since managers might be used independently, we assume case_path is valid/authorized path passed by caller.
            # But we must ensure we don't write outside it.

            path = Path(case_path).resolve()

            # Ensure path exists (it should)
            if not path.exists():
                 return {"success": False, "message": "Case directory does not exist."}

            tri_surface_dir = path / "constant" / "triSurface"
            tri_surface_dir.mkdir(parents=True, exist_ok=True)

            safe_filename = secure_filename(filename)
            if not safe_filename.lower().endswith(".stl"):
                 return {"success": False, "message": "Only .stl files are allowed."}

            filepath = tri_surface_dir / safe_filename

            # Additional check: ensure filepath is within tri_surface_dir
            try:
                filepath.resolve().relative_to(tri_surface_dir.resolve())
            except ValueError:
                 return {"success": False, "message": "Invalid file path."}

            file.save(str(filepath))

            logger.info(f"Uploaded STL to {filepath}")
            return {"success": True, "message": "File uploaded successfully.", "filename": safe_filename}

        except Exception as e:
            logger.error(f"Error uploading STL: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def list_stls(case_path: Union[str, Path]) -> Dict[str, Union[bool, List[str], str]]:
        """
        List all STL files in the constant/triSurface directory.

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

            files = [f.name for f in tri_surface_dir.iterdir() if f.is_file() and f.suffix.lower() == ".stl"]
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

            safe_filename = secure_filename(filename)
            filepath = path / "constant" / "triSurface" / safe_filename

            # Ensure we are deleting inside the directory
            try:
                filepath.resolve().relative_to(path)
            except ValueError:
                return {"success": False, "message": "Invalid file path."}

            if not filepath.exists():
                return {"success": False, "message": "File not found."}

            os.remove(filepath)
            logger.info(f"Deleted STL {filepath}")
            return {"success": True, "message": "File deleted successfully."}

        except Exception as e:
            logger.error(f"Error deleting STL: {e}")
            return {"success": False, "message": str(e)}
