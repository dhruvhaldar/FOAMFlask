"""
FOAMFlask - A web interface for OpenFOAM simulations.

This module provides a Flask-based web interface for interacting with
OpenFOAM simulations, including running cases, visualizing results,
and managing Docker containers.
"""

# Standard library imports
import json
import logging
import os
import threading
import time
import platform
import posixpath
import re
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Generator

# Third-party imports
import docker
from docker import DockerClient
from docker.errors import DockerException
from flask import Flask, Response, jsonify, render_template_string, request, send_from_directory
from werkzeug.utils import secure_filename

# Local application imports
from backend.mesh.mesher import mesh_visualizer
from backend.plots.realtime_plots import OpenFOAMFieldParser, get_available_fields
from backend.post.isosurface import IsosurfaceVisualizer, isosurface_visualizer
from backend.startup import run_initial_setup_checks, check_docker_permissions
from backend.case.manager import CaseManager
from backend.geometry.manager import GeometryManager
from backend.geometry.visualizer import GeometryVisualizer
from backend.meshing.runner import MeshingRunner
from backend.security import validate_path, is_safe_command, is_safe_script_name

# Initialize Flask application
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("FOAMFlask")

# Global configuration
CONFIG_FILE = Path("case_config.json")
CONFIG: Optional[Dict] = None
CASE_ROOT: Optional[str] = None
DOCKER_IMAGE: Optional[str] = None
OPENFOAM_VERSION: Optional[str] = None
docker_client: Optional[DockerClient] = None
foamrun_logs: Dict[str, str] = {}  # Maps tutorial names to their log content
STARTUP_STATUS = {"status": "starting", "message": "Initializing..."}


def load_config() -> Dict[str, str]:
    """Load configuration from case_config.json with sensible defaults.

    Returns:
        Dictionary containing configuration with keys:
            - CASE_ROOT: Root directory for OpenFOAM cases
            - DOCKER_IMAGE: Docker image to use
            - OPENFOAM_VERSION: OpenFOAM version
    """
    defaults = {
        "CASE_ROOT": str(Path("tutorial_cases").resolve()),
        "DOCKER_IMAGE": "haldardhruv/ubuntu_noble_openfoam:v12",
        "OPENFOAM_VERSION": "12",
    }

    if not CONFIG_FILE.exists():
        return defaults

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return {**defaults, **data}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "[FOAMFlask] Could not load config file: %s. Using defaults.", str(e)
        )
        return defaults


def save_config(updates: Dict[str, str]) -> bool:
    """Save configuration back to case_config.json.

    Args:
        updates: Dictionary of configuration updates to save.

    Returns:
        True if save was successful, False otherwise.
    """
    config = load_config()
    config.update(updates)

    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except (OSError, TypeError) as e:
        logger.error("[FOAMFlask] Could not save config to %s: %s", CONFIG_FILE, str(e))
        return False


# Initialize configuration
CONFIG = load_config()
CASE_ROOT = CONFIG["CASE_ROOT"]
DOCKER_IMAGE = CONFIG["DOCKER_IMAGE"]
OPENFOAM_VERSION = CONFIG["OPENFOAM_VERSION"]


def get_docker_client() -> Optional[DockerClient]:
    """Get or create a Docker client instance.

    Returns:
        Docker client instance if available, None otherwise.
    """
    global docker_client

    if docker_client is not None:
        return docker_client

    try:
        client = docker.from_env()
        client.ping()  # Verify Docker daemon is running
        logger.info("[FOAMFlask] Connected to Docker daemon")
        docker_client = client
        return client
    except DockerException as e:
        logger.error(
            "[FOAMFlask] Docker daemon not available. "
            "Make sure Docker Desktop is running. Details: %s",
            str(e),
        )
        return None


def docker_unavailable_response() -> Tuple[Response, int]:
    """Return a standardized error response when Docker is not available.

    Returns:
        Tuple containing JSON response with error message and 503 status code.
    """
    error_msg = (
        "[FOAMFlask] [Error] Docker daemon not available. "
        "Please start Docker Desktop and reload the page."
    )
    return jsonify({"output": error_msg}), 503


def get_docker_user_config() -> Dict[str, str]:
    """
    Get Docker user configuration for running containers.

    Returns:
        Dictionary with 'user' key if configured, else empty.
    """
    if CONFIG and CONFIG.get("docker_run_as_user"):
        uid = CONFIG.get("docker_uid")
        gid = CONFIG.get("docker_gid")
        if uid is not None and gid is not None:
            return {"user": f"{uid}:{gid}"}
    return {}


def run_startup_check() -> None:
    """
    Run the startup check in a background thread.
    """
    global STARTUP_STATUS, CONFIG, CASE_ROOT, DOCKER_IMAGE, OPENFOAM_VERSION

    STARTUP_STATUS["status"] = "running"
    STARTUP_STATUS["message"] = "Performing initial system checks..."

    def update_status_message(msg: str) -> None:
        """Callback to update global startup status message."""
        STARTUP_STATUS["message"] = msg

    try:
        # Re-load config to ensure we have latest
        current_config = load_config()

        # Use a temporary client for the check
        check_client_func = get_docker_client

        result = run_initial_setup_checks(
            check_client_func,
            current_config["CASE_ROOT"], # Use config directly as global CASE_ROOT might be stale
            current_config["DOCKER_IMAGE"],
            save_config,
            current_config,
            status_callback=update_status_message
        )

        STARTUP_STATUS.update(result)

        # Reload global config after check (which might have updated it)
        CONFIG = load_config()
        CASE_ROOT = CONFIG["CASE_ROOT"]
        DOCKER_IMAGE = CONFIG["DOCKER_IMAGE"]
        OPENFOAM_VERSION = CONFIG["OPENFOAM_VERSION"]

    except Exception as e:
        logger.error(f"Startup check failed: {e}", exc_info=True)
        STARTUP_STATUS["status"] = "failed"
        STARTUP_STATUS["message"] = "Startup check failed. See logs for details."


# Load HTML template
TEMPLATE_FILE = Path("static/html/foamflask_frontend.html")
try:
    with TEMPLATE_FILE.open("r", encoding="utf-8") as f:
        TEMPLATE = f.read()
except (OSError, UnicodeDecodeError) as e:
    logger.error(
        "[FOAMFlask] Failed to load template file %s: %s", TEMPLATE_FILE, str(e)
    )
    TEMPLATE = "<html><body>Error loading template</body></html>"


# --- Caching for Tutorials ---
# Structure: { "key": (docker_image, openfoam_version), "data": [tutorials] }
_TUTORIALS_CACHE: Dict[str, Union[Tuple[Optional[str], Optional[str]], List[str]]] = {}


def get_tutorials() -> List[str]:
    """Get a list of available OpenFOAM tutorial cases.

    Returns:
        Sorted list of available OpenFOAM tutorial paths (category/case).
    """
    global _TUTORIALS_CACHE

    # Check cache
    cache_key = (DOCKER_IMAGE, OPENFOAM_VERSION)
    if _TUTORIALS_CACHE.get("key") == cache_key:
        logger.debug("[FOAMFlask] Returning cached tutorials list")
        # Type check to satisfy mypy, though we know it's a list if key matches
        data = _TUTORIALS_CACHE.get("data", [])
        if isinstance(data, list):
            return data

    try:
        client = get_docker_client()
        if client is None:
            logger.warning("[FOAMFlask] Docker not available, cannot fetch tutorials")
            return []

        # Get the tutorials directory from OpenFOAM
        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
        result = client.containers.run(
            DOCKER_IMAGE,
            f"bash -c 'source {bashrc} && echo $FOAM_TUTORIALS'",
            remove=True,
            stdout=True,
            stderr=True,
            tty=True,
        )

        tutorial_root = result.decode().strip()
        if not tutorial_root:
            logger.warning("[FOAMFlask] No tutorial root found in OpenFOAM")
            return []

        # Find directories containing system/ and constant/ subdirectories
        find_cmd = (
            f"find {tutorial_root} -mindepth 2 -maxdepth 2 -type d "
            "-exec test -d {}/system -a -d {}/constant \\; -print"
        )

        result = client.containers.run(
            DOCKER_IMAGE,
            f"bash -c '{find_cmd}'",
            remove=True,
            stdout=True,
            stderr=True,
            tty=True,
        )

        cases = result.decode().splitlines()

        # Normalize paths based on OS
        if platform.system() == "Windows":
            tutorials = [posixpath.relpath(c, tutorial_root) for c in cases]
        else:
            # Using posixpath.relpath because Docker paths are POSIX
            tutorials = [posixpath.relpath(c, tutorial_root) for c in cases]

        sorted_tutorials = sorted(tutorials)

        # Update cache
        _TUTORIALS_CACHE = {
            "key": cache_key,
            "data": sorted_tutorials
        }

        return sorted_tutorials

    except docker.errors.APIError as e:
        logger.error(
            "[FOAMFlask] Docker API error while fetching tutorials: %s", str(e)
        )
    except Exception as e:
        logger.error(
            "[FOAMFlask] Unexpected error while fetching tutorials: %s",
            str(e),
            exc_info=True,
        )

    return []


# --- Global storage for FoamRun logs ---
foamrun_logs = {}  # { "<tutorial_name>": "<log content>" }


def monitor_foamrun_log(tutorial: str, case_dir: str) -> None:
    """Watch for log.FoamRun, capture it in foamrun_logs and write to a file.

    Args:
        tutorial: The name of the tutorial.
        case_dir: The path to the case directory.
    """
    try:
        validated_case_dir = validate_path(case_dir, CASE_ROOT)
        host_log_path = validate_path(validated_case_dir / tutorial / "log.FoamRun", CASE_ROOT)
        output_file = validate_path(validated_case_dir / tutorial / "foamrun_logs.txt", CASE_ROOT, allow_new=True)
    except Exception as e:
        logger.error(f"[FOAMFlask] Invalid path in monitor_foamrun_log: {e}")
        return

    # Configuration
    timeout = 300  # seconds max wait
    interval = 1  # check every 1 second
    elapsed = 0

    while elapsed < timeout:
        if host_log_path.exists():
            try:
                log_content = host_log_path.read_text(encoding="utf-8")
                foamrun_logs[tutorial] = log_content
                output_file.write_text(log_content, encoding="utf-8")
                logger.info(
                    "[FOAMFlask] Captured log.FoamRun for tutorial '%s' "
                    "and wrote to %s",
                    tutorial,
                    output_file,
                )
                return
            except (OSError, UnicodeDecodeError) as e:
                logger.error("[FOAMFlask] Could not process foamrun_logs: %s", str(e))
                return

        time.sleep(interval)
        elapsed += interval

    logger.warning("[FOAMFlask] Timeout: log.FoamRun not found for '%s'", tutorial)


# --- Routes ---
@app.route("/")
def index() -> str:
    """Render the index page with available tutorials.

    Returns:
        Rendered HTML template with tutorials and case root.
    """
    tutorials = get_tutorials()
    options_html = "\n".join(f'<option value="{t}">{t}</option>' for t in tutorials)
    return render_template_string(TEMPLATE, options=options_html, CASE_ROOT=CASE_ROOT)


@app.route("/api/startup_status", methods=["GET"])
def get_startup_status() -> Response:
    """
    Get the status of the startup checks.

    Returns:
        JSON response with status and message.
    """
    return jsonify(STARTUP_STATUS)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/get_case_root", methods=["GET"])
def get_case_root() -> Response:
    """Get the case root directory.

    Returns:
        JSON response containing the case root directory.
    """
    return jsonify({"caseDir": CASE_ROOT})


@app.route("/set_case", methods=["POST"])
def set_case() -> Union[Response, Tuple[Response, int]]:
    """Set the case root directory.

    Returns:
        JSON response with status and case directory information.
    """
    global CASE_ROOT

    try:
        data = request.get_json()
        if not data or "caseDir" not in data or not data["caseDir"]:
            return jsonify({"output": "[FOAMFlask] [Error] No caseDir provided"}), 400

        # We allow setting absolute paths for CASE_ROOT, as this is the configuration step.
        # However, we should ensure it is a directory.
        case_dir_path = Path(data["caseDir"]).resolve()

        # Security check: Limit to a specific parent directory if needed?
        # For this application, the user sets the root workspace.
        # We assume the user has access to the file system.
        # But to be safe, we can check if it exists or create it.

        case_dir_path.mkdir(parents=True, exist_ok=True)
        CASE_ROOT = str(case_dir_path)
        save_config({"CASE_ROOT": CASE_ROOT})

        return jsonify(
            {
                "output": f"INFO::[FOAMFlask] Case root set to: {CASE_ROOT}",
                "caseDir": CASE_ROOT,
            }
        )
    except Exception as e:
        logger.error("Error setting case directory: %s", str(e), exc_info=True)
        return jsonify({"output": "[FOAMFlask] [Error] An internal error occurred."}), 500


@app.route("/api/cases/list", methods=["GET"])
def api_list_cases() -> Response:
    """List available cases in the CASE_ROOT."""
    if not CASE_ROOT:
         return jsonify({"cases": []})

    try:
        root = Path(CASE_ROOT)
        if not root.exists():
             return jsonify({"cases": []})

        # List subdirectories that look like cases (or just all dirs)
        cases = [d.name for d in root.iterdir() if d.is_dir()]
        return jsonify({"cases": sorted(cases)})
    except Exception as e:
        logger.error(f"Error listing cases: {e}", exc_info=True)
        return jsonify({"cases": []}), 500

@app.route("/api/case/create", methods=["POST"])
def api_create_case() -> Union[Response, Tuple[Response, int]]:
    """
    Create a new OpenFOAM case with minimal structure.

    Returns:
        JSON response with status and path.
    """
    try:
        data = request.get_json()
        case_name = data.get("caseName")

        if not case_name:
            return jsonify({"success": False, "message": "No case name provided"}), 400

        if not is_safe_script_name(case_name):
             return jsonify({"success": False, "message": "Invalid case name"}), 400

        # Use globally set CASE_ROOT
        if not CASE_ROOT:
             return jsonify({"success": False, "message": "Case root not set"}), 500

        # Validate path
        full_path = validate_path(case_name, CASE_ROOT, allow_new=True)

        result = CaseManager.create_case_structure(full_path)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"Error in api_create_case: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500


# --- Geometry Routes ---

@app.route("/api/geometry/upload", methods=["POST"])
def api_upload_geometry() -> Union[Response, Tuple[Response, int]]:
    """Upload an STL file to the current case."""
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file part"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No selected file"}), 400

        # Get the current case path from request
        case_name = request.form.get("caseName")
        if not case_name:
             return jsonify({"success": False, "message": "No case name specified"}), 400

        # Validate case directory
        case_dir = validate_path(case_name, CASE_ROOT)

        result = GeometryManager.upload_stl(case_dir, file, file.filename)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error in api_upload_geometry: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route("/api/geometry/list", methods=["GET"])
def api_list_geometry() -> Union[Response, Tuple[Response, int]]:
    """List STL files in the current case."""
    try:
        case_name = request.args.get("caseName")
        if not case_name:
             return jsonify({"success": False, "message": "No case name specified"}), 400

        case_dir = validate_path(case_name, CASE_ROOT)
        result = GeometryManager.list_stls(case_dir)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error in api_list_geometry: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route("/api/geometry/delete", methods=["POST"])
def api_delete_geometry() -> Union[Response, Tuple[Response, int]]:
    """Delete an STL file."""
    try:
        data = request.get_json()
        case_name = data.get("caseName")
        filename = data.get("filename")

        if not case_name or not filename:
            return jsonify({"success": False, "message": "Missing parameters"}), 400

        case_dir = validate_path(case_name, CASE_ROOT)
        result = GeometryManager.delete_stl(case_dir, filename)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error in api_delete_geometry: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route("/api/geometry/view", methods=["POST"])
def api_view_geometry() -> Union[Response, Tuple[Response, int]]:
    """Get interactive HTML viewer for an STL."""
    try:
        data = request.get_json()
        case_name = data.get("caseName")
        filename = data.get("filename")
        color = data.get("color", "lightblue")
        opacity = data.get("opacity", 1.0)

        if not case_name or not filename:
            return jsonify({"success": False, "message": "Missing parameters"}), 400

        # Validate case dir and filename inside it
        case_dir = validate_path(case_name, CASE_ROOT)
        # Assuming files are in constant/triSurface as managed by GeometryManager
        file_path = validate_path(case_dir / "constant" / "triSurface" / filename, CASE_ROOT)

        html_content = GeometryVisualizer.get_interactive_html(file_path, color, opacity)

        if html_content:
            return Response(html_content, mimetype="text/html")
        else:
            return jsonify({"success": False, "message": "Failed to generate view"}), 500
    except Exception as e:
        logger.error(f"Error in api_view_geometry: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route("/api/geometry/info", methods=["POST"])
def api_info_geometry() -> Union[Response, Tuple[Response, int]]:
    """Get info (bounds, etc) for an STL."""
    try:
        data = request.get_json()
        case_name = data.get("caseName")
        filename = data.get("filename")

        if not case_name or not filename:
            return jsonify({"success": False, "message": "Missing parameters"}), 400

        case_dir = validate_path(case_name, CASE_ROOT)
        file_path = validate_path(case_dir / "constant" / "triSurface" / filename, CASE_ROOT)

        info = GeometryVisualizer.get_mesh_info(file_path)
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error in api_info_geometry: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500


# --- Meshing Routes ---

@app.route("/api/meshing/blockMesh/config", methods=["POST"])
def api_meshing_blockmesh_config() -> Union[Response, Tuple[Response, int]]:
    """Generate blockMeshDict."""
    try:
        data = request.get_json()
        case_name = data.get("caseName")
        config = data.get("config", {})

        if not case_name:
             return jsonify({"success": False, "message": "No case name specified"}), 400

        case_path = validate_path(case_name, CASE_ROOT)
        result = MeshingRunner.configure_blockmesh(case_path, config)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error in api_meshing_blockmesh_config: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route("/api/meshing/snappyHexMesh/config", methods=["POST"])
def api_meshing_snappyhexmesh_config() -> Union[Response, Tuple[Response, int]]:
    """Generate snappyHexMeshDict."""
    try:
        data = request.get_json()
        case_name = data.get("caseName")
        config = data.get("config", {})

        if not case_name:
             return jsonify({"success": False, "message": "No case name specified"}), 400

        case_path = validate_path(case_name, CASE_ROOT)
        result = MeshingRunner.configure_snappyhexmesh(case_path, config)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error in api_meshing_snappyhexmesh_config: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route("/api/meshing/run", methods=["POST"])
def api_meshing_run() -> Union[Response, Tuple[Response, int]]:
    """Run a meshing command."""
    try:
        data = request.get_json()
        case_name = data.get("caseName")
        command = data.get("command") # "blockMesh" or "snappyHexMesh"

        if not case_name or not command:
             return jsonify({"success": False, "message": "Missing parameters"}), 400

        if command not in ["blockMesh", "snappyHexMesh"]:
            return jsonify({"success": False, "message": "Invalid command"}), 400

        case_path = validate_path(case_name, CASE_ROOT)
        client = get_docker_client()
        user_config = get_docker_user_config()

        result = MeshingRunner.run_meshing_command(
            case_path,
            command,
            client,
            DOCKER_IMAGE,
            OPENFOAM_VERSION,
            user_config
        )

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error in api_meshing_run: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An internal error occurred."}), 500


@app.route("/get_docker_config", methods=["GET"])
def get_docker_config() -> Response:
    """Get the Docker configuration.

    Returns:
        JSON response containing Docker image and OpenFOAM version.
    """
    return jsonify({"dockerImage": DOCKER_IMAGE, "openfoamVersion": OPENFOAM_VERSION})


@app.route("/set_docker_config", methods=["POST"])
def set_docker_config() -> Union[Response, Tuple[Response, int]]:
    """Update Docker configuration.

    Returns:
        JSON response with updated Docker configuration.
    """
    global DOCKER_IMAGE, OPENFOAM_VERSION

    try:
        data = request.get_json()
        if not data:
            return (
                jsonify({"output": "[FOAMFlask] [Error] No configuration data provided"}),
                400,
            )

        updates = {}
        if "dockerImage" in data and data["dockerImage"]:
            DOCKER_IMAGE = data["dockerImage"]
            updates["DOCKER_IMAGE"] = DOCKER_IMAGE

        if "openfoamVersion" in data and data["openfoamVersion"]:
            OPENFOAM_VERSION = str(data["openfoamVersion"])
            updates["OPENFOAM_VERSION"] = OPENFOAM_VERSION

        if updates:
            save_config(updates)

        return jsonify(
            {
                "output": "INFO::[FOAMFlask] Docker config updated",
                "dockerImage": DOCKER_IMAGE,
                "openfoamVersion": OPENFOAM_VERSION,
            }
        )
    except Exception as e:
        logger.error(f"Error in set_docker_config: {e}", exc_info=True)
        return jsonify({"output": "[FOAMFlask] [Error] An internal error occurred."}), 500


@app.route("/load_tutorial", methods=["POST"])
def load_tutorial() -> Union[Response, Tuple[Response, int]]:
    """
    Load a tutorial in the Docker container.

    Args:
        tutorial (str): The name of the tutorial.

    Returns:
        dict: The output of the command.
    """
    global CASE_ROOT, DOCKER_IMAGE, OPENFOAM_VERSION

    try:
        data = request.get_json()
        tutorial = data.get("tutorial")

        if not tutorial:
            return jsonify({"output": "[FOAMFlask] [Error] No tutorial selected"})

        # Validate that tutorial name/path is safe (no ..)
        if ".." in tutorial:
             return jsonify({"output": "[FOAMFlask] [Error] Invalid tutorial path"}), 400

        client = get_docker_client()
        if client is None:
            return docker_unavailable_response()

        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
        container_run_path = "/tmp/FOAM_Run"
        container_case_path = posixpath.join(container_run_path, tutorial)

        # Convert Windows paths to POSIX style for Docker
        # We assume CASE_ROOT is valid here as it is global
        host_path = Path(CASE_ROOT).resolve()
        is_windows = platform.system() == "Windows"
        # Docker expects POSIX paths for bind mounts on Windows (e.g. /c/Users/...)
        host_path_str = host_path.as_posix() if is_windows else str(host_path)

        # Base docker command: create directory and copy tutorial
        # Note: tutorial variable is injected into command. We should ensure it's safe.
        # But here it's passed as arg to bash.
        # Using simple string substitution is risky if tutorial contains shell metachars.
        if not is_safe_script_name(os.path.basename(tutorial)):
             return jsonify({"output": "[FOAMFlask] [Error] Invalid tutorial name"}), 400

        # Also need to handle nested tutorials "basic/pitzDaily"
        # We can split by / and check each part
        for part in tutorial.split('/'):
             if not is_safe_script_name(part):
                 return jsonify({"output": "[FOAMFlask] [Error] Invalid tutorial path component"}), 400

        docker_cmd = (
            f"bash -c 'source {bashrc} && "
            f"mkdir -p {container_case_path} && "
            f"cp -r $FOAM_TUTORIALS/{tutorial}/* {container_case_path}"
        )

        # On Linux/macOS, add chmod; on Windows skip it
        if not is_windows:
            docker_cmd += f" && chmod +x {container_case_path}/Allrun"

        docker_cmd += "'"

        container = None

        run_kwargs = {
            "detach": True,
            "tty": True,
            "stdout": True,
            "stderr": True,
            "volumes": {host_path_str: {"bind": container_run_path, "mode": "rw"}},
            "working_dir": container_run_path,
            "remove": True,
        }
        # Update with user config if present
        run_kwargs.update(get_docker_user_config())

        container = client.containers.run(
            DOCKER_IMAGE,
            docker_cmd,
            **run_kwargs
        )

        result = container.wait()
        logs = container.logs().decode()

        if result["StatusCode"] == 0:
            output = (
                f"INFO::[FOAMFlask] Tutorial loaded::{tutorial}\n"
                f"Source: $FOAM_TUTORIALS/{tutorial}\n"
                f"Copied to: {CASE_ROOT}/{tutorial}\n"
            )
        else:
            output = f"[FOAMFlask] [Error] Failed to load tutorial {tutorial}\n{logs}"

        return jsonify({"output": output, "caseDir": CASE_ROOT})

    except Exception as e:
        logger.error(f"Error loading tutorial: {e}", exc_info=True)
        return jsonify({"output": "[FOAMFlask] [Error] An internal error occurred."}), 500

    finally:
        if container:
            try:
                container.reload()
                if container.status == "running":
                    container.kill()
            except Exception:
                pass
            try:
                container.remove()
            except Exception:
                pass


@app.route("/run", methods=["POST"])
def run_case() -> Union[Response, Tuple[Dict, int]]:
    """
    Run a case in the Docker container.

    Args:
        tutorial (str): The name of the tutorial.
        command (str): The command to run.
        caseDir (str): The path to the case directory.

    Returns:
        dict: The output of the command.
    """
    try:
        data = request.json
        tutorial = data.get("tutorial")
        command = data.get("command")
        case_dir_str = data.get("caseDir")

        if not command:
            return {"error": "No command provided"}, 400
        if not tutorial or not case_dir_str:
            return {"error": "Missing tutorial or caseDir"}, 400

        # Validate case_dir
        # We must ensure caseDir matches CASE_ROOT or is inside it?
        # Usually it IS CASE_ROOT.
        # But we accept it from client.
        
        # Security: Validate paths
        try:
             validated_case_dir = validate_path(case_dir_str, CASE_ROOT)
             # Also ensure tutorial is valid subpath
             validate_path(validated_case_dir / tutorial, CASE_ROOT)
        except Exception as e:
             return {"error": f"Invalid path: {e}"}, 400

        # Use valid path string for streaming generator
        valid_case_dir = str(validated_case_dir)

        def stream_container_logs() -> Generator[str, None, None]:
            """Stream container logs for OpenFOAM command execution.

            Yields:
                Log lines as HTML-formatted strings.
            """
            client = get_docker_client()
            if client is None:
                yield (
                    "[FOAMFlask] [Error] Docker daemon not available. "
                    "Please start Docker Desktop and re-run the case.<br>"
                )
                return

            container_case_path = posixpath.join(
                "/tmp/FOAM_Run", tutorial
            )
            bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"

            # Convert Windows path to POSIX for Docker volumes
            host_path = Path(valid_case_dir).resolve()
            host_path_str = host_path.as_posix() if platform.system() == "Windows" else str(host_path)

            volumes = {
                host_path_str: {
                    "bind": "/tmp/FOAM_Run",
                    "mode": "rw",
                }
            }

            # Start the watcher thread before running container
            watcher_thread = threading.Thread(
                target=monitor_foamrun_log, args=(tutorial, valid_case_dir), daemon=True
            )
            watcher_thread.start()

            # Validate and sanitize command input to prevent injection
            if not is_safe_command(command):
                yield f"[FOAMFlask] [Error] Unsafe command detected.<br>"
                yield "[FOAMFlask] [Error] Commands containing shell metacharacters or dangerous patterns are not allowed.<br>"
                return

            # Determine if command is an OpenFOAM command or a script file
            openfoam_commands = ["blockMesh", "simpleFoam", "pimpleFoam", "decomposePar", "reconstructPar", "foamToVTK", "paraFoam"]

            if command.startswith("./") or command in openfoam_commands:
                if command.startswith("./"):
                    # Script file - validate path and execute safely
                    script_name = command[2:]  # Remove "./" prefix
                    if not is_safe_script_name(script_name):
                        yield f"[FOAMFlask] [Error] Unsafe script name.<br>"
                        return

                    # Create a secure wrapper script using string concatenation
                    wrapper_script = "#!/bin/bash\n"
                    wrapper_script += "source " + bashrc + "\n"
                    wrapper_script += "cd " + container_case_path + "\n"
                    wrapper_script += "chmod +x " + script_name + "\n"
                    wrapper_script += "./" + script_name + "\n"
                    docker_cmd = ["bash", "-c", wrapper_script]
                else:
                    # OpenFOAM command - create secure wrapper script
                    wrapper_script = "#!/bin/bash\n"
                    wrapper_script += "source " + bashrc + "\n"
                    wrapper_script += "cd " + container_case_path + "\n"
                    wrapper_script += command + "\n"
                    docker_cmd = ["bash", "-c", wrapper_script]
            else:
                # Fallback - treat as script with validation
                if not is_safe_script_name(command):
                    yield f"[FOAMFlask] [Error] Unsafe command name.<br>"
                    return
                
                wrapper_script = "#!/bin/bash\n"
                wrapper_script += "source " + bashrc + "\n"
                wrapper_script += "cd " + container_case_path + "\n"
                wrapper_script += "chmod +x " + command + "\n"
                wrapper_script += "./" + command + "\n"
                docker_cmd = ["bash", "-c", wrapper_script]

            try:
                run_kwargs = {
                    "detach": True,
                    "tty": False,
                    "volumes": volumes,
                    "working_dir": container_case_path,
                }
                run_kwargs.update(get_docker_user_config())

                container = client.containers.run(
                    DOCKER_IMAGE,
                    docker_cmd,
                    **run_kwargs
                )

                try:
                    for line in container.logs(stream=True):
                        decoded = line.decode(errors="ignore")
                        for subline in decoded.splitlines():
                            yield subline + "<br>"
                except Exception as e:
                    yield f"[FOAMFlask] [Error] Failed to stream container logs: {e}<br>"

            except Exception as e:
                logger.error(f"Error running container: {e}", exc_info=True)
                yield f"[FOAMFlask] [Error] Failed to start container: {e}<br>"
                return

            finally:
                if 'container' in locals():
                    try:
                        container.kill()
                    except Exception as kill_err:
                        logger.debug(f"[FOAMPilot] Could not kill container (might have stopped): {kill_err}")
                    try:
                        container.remove()
                    except Exception as remove_err:
                        logger.error(f"[FOAMPilot] Could not remove container: {remove_err}")

        return Response(stream_container_logs(), mimetype="text/html")

    except Exception as e:
        logger.error(f"Error in run_case: {e}", exc_info=True)
        return {"error": "An internal error occurred."}, 500


# --- Realtime Plotting Endpoints ---
@app.route("/api/available_fields", methods=["GET"])
def api_available_fields() -> Union[Response, Tuple[Response, int]]:
    """
    Get list of available fields in the current case.
    """
    try:
        tutorial = request.args.get("tutorial")
        if not tutorial:
            return jsonify({"error": "No tutorial specified"}), 400

        case_dir = validate_path(tutorial, CASE_ROOT)
        if not case_dir.exists():
            return jsonify({"error": "Case directory not found"}), 404

        fields = get_available_fields(str(case_dir))
        return jsonify({"fields": fields})
    except Exception as e:
        logger.error(f"Error in available_fields: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/api/plot_data", methods=["GET"])
def api_plot_data() -> Union[Response, Tuple[Response, int]]:
    """
    Get realtime plot data for the current case.
    """
    try:
        tutorial = request.args.get("tutorial")
        if not tutorial:
            return jsonify({"error": "No tutorial specified"}), 400

        case_dir = validate_path(tutorial, CASE_ROOT)
        if not case_dir.exists():
            return jsonify({"error": "Case directory not found"}), 404

        parser = OpenFOAMFieldParser(str(case_dir))
        data = parser.get_all_time_series_data(max_points=100)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting plot data: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/api/latest_data", methods=["GET"])
def api_latest_data() -> Union[Response, Tuple[Response, int]]:
    """
    Get the latest time step data.
    """
    try:
        tutorial = request.args.get("tutorial")
        if not tutorial:
            return jsonify({"error": "No tutorial specified"}), 400

        case_dir = validate_path(tutorial, CASE_ROOT)
        if not case_dir.exists():
            return jsonify({"error": "Case directory not found"}), 404

        parser = OpenFOAMFieldParser(str(case_dir))
        data = parser.get_latest_time_data()
        return jsonify(data if data else {})
    except Exception as e:
        logger.error(f"Error getting latest data: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/api/residuals", methods=["GET"])
def api_residuals() -> Union[Response, Tuple[Response, int]]:
    """
    Get residuals from log file.
    """
    try:
        tutorial = request.args.get("tutorial")
        if not tutorial:
            return jsonify({"error": "No tutorial specified"}), 400

        case_dir = validate_path(tutorial, CASE_ROOT)
        if not case_dir.exists():
            return jsonify({"error": "Case directory not found"}), 404

        parser = OpenFOAMFieldParser(str(case_dir))
        residuals = parser.get_residuals_from_log()
        return jsonify(residuals)
    except Exception as e:
        logger.error(f"Error getting residuals: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


# --- PyVista Mesh Visualization Endpoints ---
@app.route("/api/available_meshes", methods=["GET"])
def api_available_meshes() -> Union[Response, Tuple[Response, int]]:
    """
    Get list of available mesh files in the case directory.
    """
    try:
        tutorial = request.args.get("tutorial")
        if not tutorial:
            return jsonify({"error": "No tutorial specified"}), 400

        # Validate tutorial path to ensure it is within CASE_ROOT
        # mesh_visualizer.get_available_meshes takes strings, so we validate first
        validate_path(tutorial, CASE_ROOT)

        mesh_files = mesh_visualizer.get_available_meshes(CASE_ROOT, tutorial)
        return jsonify({"meshes": mesh_files})
    except Exception as e:
        logger.error(f"Error getting available meshes: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/api/load_mesh", methods=["POST"])
def api_load_mesh() -> Union[Response, Tuple[Response, int]]:
    """
    Load a mesh file and return mesh information.
    """
    try:
        data = request.get_json()
        file_path = data.get("file_path")
        for_contour = data.get("for_contour", False)

        if not file_path:
            return jsonify({"error": "No file path provided"}), 400

        # Validate file path
        # file_path provided might be absolute or relative to CASE_ROOT?
        # Typically frontend sends path from available_meshes which uses full path.
        # We need to ensure it is within CASE_ROOT.

        # If absolute path, validate_path with CASE_ROOT checks it's inside.
        validated_path = validate_path(file_path, CASE_ROOT)

        logger.info("[FOAMFlask] [api_load_mesh] Mesh loading called")
        mesh_info = mesh_visualizer.load_mesh(validated_path)

        if for_contour:
            logger.info("[FOAMFlask] [api_load_mesh] [for_contour] Mesh loading for contour called")
            try:
                mesh_info.setdefault("point_arrays", mesh_info.get("array_names", []))
            except Exception as e:
                logger.error(f"Error loading mesh for contour: {e}", exc_info=True)
                return jsonify({"error": "An internal error occurred."}), 500

        return jsonify(mesh_info)
    except Exception as e:
        logger.error(f"Error loading mesh: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/api/mesh_screenshot", methods=["POST"])
def api_mesh_screenshot() -> Union[Response, Tuple[Response, int]]:
    """
    Generate a screenshot of the mesh.
    """
    try:
        data = request.get_json()
        file_path = data.get("file_path")
        width = data.get("width", 800)
        height = data.get("height", 600)
        show_edges = data.get("show_edges", True)
        color = data.get("color", "lightblue")
        camera_position = data.get("camera_position", None)

        if not file_path:
            return jsonify({"error": "No file path provided"}), 400

        validated_path = validate_path(file_path, CASE_ROOT)

        # Add delay for first call
        if not hasattr(api_mesh_screenshot, "_has_been_called"):
            time.sleep(4)  # 4 second delay for first call
            api_mesh_screenshot._has_been_called = True

        img_str = mesh_visualizer.get_mesh_screenshot(
            validated_path, width, height, show_edges, color, camera_position
        )

        if img_str:
            return jsonify({"success": True, "image": img_str})
        else:
            return jsonify({"success": False, "error": "Failed to generate screenshot"}), 500
    except Exception as e:
        logger.error(f"Error generating mesh screenshot: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/api/mesh_interactive", methods=["POST"])
def api_mesh_interactive() -> Union[Response, Tuple[Response, int]]:
    """
    Generate an interactive HTML viewer for the mesh.
    """
    try:
        data = request.get_json()
        file_path = data.get("file_path")
        show_edges = data.get("show_edges", True)
        color = data.get("color", "lightblue")

        if not file_path:
            return jsonify({"error": "No file path provided"}), 400

        validated_path = validate_path(file_path, CASE_ROOT)

        # Add a small delay to prevent race conditions
        time.sleep(2)  # 2 second delay

        html_content = mesh_visualizer.get_interactive_viewer_html(
            validated_path, show_edges, color
        )

        if html_content:
            return Response(html_content, mimetype="text/html")
        else:
            return jsonify({"success": False, "error": "Failed to generate interactive viewer"}), 500
    except Exception as e:
        logger.error(f"Error generating interactive viewer: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/run_foamtovtk", methods=["POST"])
def run_foamtovtk() -> Union[Response, Tuple[Dict, int]]:
    """
    Run foamToVTK command in the Docker container.
    """
    try:
        data = request.json
        tutorial = data.get("tutorial")
        case_dir_str = data.get("caseDir")

        if not tutorial or not case_dir_str:
            return {"error": "Missing tutorial or caseDir"}, 400

        # Validate path
        validated_case_dir = validate_path(case_dir_str, CASE_ROOT)
        
        # Validate tutorial as subpath
        validate_path(validated_case_dir / tutorial, CASE_ROOT)

        def stream_foamtovtk_logs() -> Generator[str, None, None]:
            """Stream logs for foamToVTK conversion process.
            """
            client = get_docker_client()
            if client is None:
                yield "[FOAMFlask] [Error] Docker daemon not available. Please start Docker Desktop and try again.<br>"
                return

            container_case_path = posixpath.join(
                "/tmp/FOAM_Run", tutorial
            )
            bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"

            host_path_str = validated_case_dir.as_posix() if platform.system() == "Windows" else str(validated_case_dir)

            volumes = {
                host_path_str: {
                    "bind": "/tmp/FOAM_Run",
                    "mode": "rw",
                }
            }

            docker_cmd = (
                f"bash -c '"
                f"source {bashrc} && "
                f"cd {container_case_path} && "
                f"source {bashrc} && "  # Source bashrc again in case we need it
                f"foamToVTK -case {container_case_path}"
                f"'"
            )

            try:
                run_kwargs = {
                    "detach": True,
                    "tty": False,
                    "volumes": volumes,
                    "working_dir": container_case_path,
                }
                run_kwargs.update(get_docker_user_config())

                container = client.containers.run(
                    DOCKER_IMAGE,
                    docker_cmd,
                    **run_kwargs
                )

                # Stream logs line by line
                for line in container.logs(stream=True):
                    decoded = line.decode(errors="ignore")
                    for subline in decoded.splitlines():
                        yield subline + "<br>"

            except Exception as e:
                logger.error(f"Error running foamToVTK: {e}", exc_info=True)
                yield f"[FOAMFlask] [Error] {e}<br>"

            finally:
                if 'container' in locals():
                    try:
                        container.kill()
                    except Exception:
                        pass
                    try:
                        container.remove()
                    except Exception:
                        logger.error("[FOAMFlask] Could not remove container")

        return Response(stream_foamtovtk_logs(), mimetype="text/html")

    except Exception as e:
        logger.error(f"Error in run_foamtovtk: {e}", exc_info=True)
        return {"error": "An internal error occurred."}, 500


# --- PyVista Post Processing Visualization Endpoints ---
@app.route("/api/post_process", methods=["POST"])
def post_process() -> Union[Response, Tuple[Response, int]]:
    """Handle post-processing requests for OpenFOAM results.
    """
    try:
        # Add your post-processing logic here
        return jsonify({"status": "success", "message": "Post processing endpoint"})
    except Exception as e:
        logger.error(f"Error during post-processing: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/api/contours/create", methods=["POST", "OPTIONS"])
def create_contour() -> Union[Response, Tuple[Response, int]]:
    """
    Create isosurfaces for the current mesh.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return "", 204

    try:
        logger.info("[FOAMFlask] [create_contour] Route handler called")

        if not request.is_json:
            return jsonify({"success": False, "error": f"Expected JSON, got {request.content_type}"}), 400

        request_data = request.get_json()
        tutorial = request_data.get("tutorial")
        case_dir_str = request_data.get("caseDir")
        scalar_field = request_data.get("scalar_field", "U_Magnitude")
        num_isosurfaces = int(request_data.get("num_isosurfaces", 5))

        if not tutorial:
            return jsonify({"success": False, "error": "Tutorial not specified"}), 400

        if not case_dir_str:
            return jsonify({"success": False, "error": "Case directory not specified"}), 400

        # Validate paths
        case_dir = validate_path(case_dir_str, CASE_ROOT)

        # Also check tutorial? Usually case_dir *is* the tutorial dir for this call or parent?
        # The logic below iterates `case_dir.rglob("*")`. If case_dir is CASE_ROOT, that's heavy.
        # But if `case_dir_str` was set to `CASE_ROOT/tutorial`, then it's fine.
        # Let's assume input is correct but validated.

        logger.info(f"[FOAMFlask] [create_contour] Searching for VTK files in {case_dir}")
        vtk_files = []
        for file in case_dir.rglob("*"):
             if file.suffix in [".vtk", ".vtp", ".vtu"]:
                 vtk_files.append(str(file))

        if not vtk_files:
            return jsonify({"success": False, "error": f"No VTK files found in {case_dir}"}), 404

        # Get latest VTK file
        latest_vtk = max(vtk_files, key=os.path.getmtime)
        logger.info(f"[FOAMFlask] [create_contour] Using VTK file: {latest_vtk}")

        # Load mesh
        mesh_info = isosurface_visualizer.load_mesh(latest_vtk)

        if not mesh_info.get("success"):
            return jsonify({"success": False, "error": f"Failed to load mesh"}), 500

        # Check scalar field
        available_fields = mesh_info.get("point_arrays", [])
        if scalar_field not in available_fields:
            return jsonify({"success": False, "error": f"Scalar field '{scalar_field}' not found."}), 400

        # Get range from request if provided
        custom_range = None
        if (
            "range" in request_data
            and isinstance(request_data["range"], list)
            and len(request_data["range"]) == 2
        ):
            custom_range = request_data["range"]

        # Generate isosurfaces
        isosurface_info = isosurface_visualizer.generate_isosurfaces(
            scalar_field=scalar_field,
            num_isosurfaces=num_isosurfaces,
            custom_range=custom_range,
        )

        if not isosurface_info.get("success"):
            return jsonify({"success": False, "error": "Failed to generate isosurfaces"}), 500

        # Generate HTML
        html_content = isosurface_visualizer.get_interactive_html(
            scalar_field=scalar_field,
            show_base_mesh=True,
            base_mesh_opacity=0.25,
            contour_opacity=0.8,
            contour_color="red",
            colormap="viridis",
            show_isovalue_slider=True,
        )

        if not html_content:
            return jsonify({"success": False, "error": "Empty HTML content generated"}), 500

        return Response(html_content, mimetype="text/html")

    except Exception as e:
        logger.error(f"[FOAMFlask] [create_contour] Exception: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "An internal error occurred."}), 500


@app.route("/api/upload_vtk", methods=["POST"])
def upload_vtk() -> Union[Response, Tuple[Response, int]]:
    """Upload VTK files for visualization.
    """
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file part"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No selected file"}), 400

        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)

        if not file.filename:
            return jsonify({"success": False, "error": "Invalid filename"}), 400

        filename = secure_filename(file.filename)
        filepath = temp_dir / filename

        # Validate that temp_dir is safe. It is relative to CWD.
        # But we should ensure filepath is strictly inside temp_dir
        try:
             filepath.resolve().relative_to(temp_dir.resolve())
        except ValueError:
             return jsonify({"success": False, "error": "Invalid filename"}), 400

        # Save the file temporarily
        file.save(str(filepath))

        # Use IsosurfaceVisualizer to handle the mesh loading
        visualizer = IsosurfaceVisualizer()
        result = visualizer.load_mesh(str(filepath))

        if not result.get("success", False):
            return jsonify({"success": False, "error": "Failed to load mesh"}), 400

        return jsonify(
            {
                "success": True,
                "filename": filename,
                "mesh_info": {
                    "n_points": result.get("n_points"),
                    "n_cells": result.get("n_cells"),
                    "bounds": result.get("bounds"),
                    "point_arrays": result.get("point_arrays", []),
                    "cell_arrays": result.get("cell_arrays", []),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in upload_vtk: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "An internal error occurred."}), 500
    finally:
        # Clean up the temporary file
        try:
            if 'filepath' in locals() and filepath.exists():
                filepath.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up file {filepath}: {e}")


def main() -> None:
    global CONFIG, CASE_ROOT, DOCKER_IMAGE, OPENFOAM_VERSION
    CONFIG = load_config()
    CASE_ROOT = CONFIG["CASE_ROOT"]
    DOCKER_IMAGE = CONFIG["DOCKER_IMAGE"]
    OPENFOAM_VERSION = CONFIG["OPENFOAM_VERSION"]

    Path(CASE_ROOT).mkdir(parents=True, exist_ok=True)

    # Start startup check in background
    threading.Thread(target=run_startup_check, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
