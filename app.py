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
from backend.startup import run_initial_setup_checks

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


# Security validation functions
def is_safe_command(command: str) -> bool:
    """
    Validate command input to prevent shell injection.
    
    Args:
        command: User-provided command string
        
    Returns:
        True if command is safe, False otherwise
    """
    if not command or not isinstance(command, str):
        return False
    
    # Check for dangerous shell metacharacters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'"]
    if any(char in command for char in dangerous_chars):
        return False
    
    # Check for path traversal attempts
    if '..' in command:
        return False
    
    # Check for command substitution
    if '$(' in command or '`' in command:
        return False
    
    # Check for file descriptor redirection
    if re.search(r'[0-9]+[<>]', command):
        return False
    
    # Check for background/foreground operators
    if '&' in command or '%' in command:
        return False
    
    # Length check to prevent extremely long commands
    if len(command) > 100:
        return False
    
    return True


def is_safe_script_name(script_name: str) -> bool:
    """
    Validate script name to prevent path traversal and injection.
    
    Args:
        script_name: Script file name (without path)
        
    Returns:
        True if script name is safe, False otherwise
    """
    if not script_name or not isinstance(script_name, str):
        return False
    
    # Only allow alphanumeric characters, underscores, hyphens, and dots
    if not re.match(r'^[a-zA-Z0-9_.-]+$', script_name):
        return False
    
    # Prevent path traversal
    if '..' in script_name or '/' in script_name or '\\' in script_name:
        return False
    
    # Prevent hidden files starting with dot
    if script_name.startswith('.'):
        return False
    
    # Length check
    if len(script_name) > 50:
        return False
    
    return True


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
        STARTUP_STATUS["message"] = f"Startup check failed: {str(e)}"


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
    host_log_path = Path(case_dir) / tutorial / "log.FoamRun"
    output_file = Path(case_dir) / tutorial / "foamrun_logs.txt"

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

    data = request.get_json()
    if not data or "caseDir" not in data or not data["caseDir"]:
        return jsonify({"output": "[FOAMFlask] [Error] No caseDir provided"}), 400

    try:
        case_dir_path = Path(data["caseDir"]).resolve()
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
        logger.error("Error setting case directory: %s", str(e))
        return jsonify({"output": f"[FOAMFlask] [Error] {str(e)}"}), 400


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
    data = request.get_json()
    tutorial = data.get("tutorial")

    if not tutorial:
        return jsonify({"output": "[FOAMFlask] [Error] No tutorial selected"})

    client = get_docker_client()
    if client is None:
        return docker_unavailable_response()

    bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
    container_run_path = "/tmp/FOAM_Run"
    container_case_path = posixpath.join(container_run_path, tutorial)

    # Convert Windows paths to POSIX style for Docker
    host_path = Path(CASE_ROOT).resolve()
    is_windows = platform.system() == "Windows"
    # Docker expects POSIX paths for bind mounts on Windows (e.g. /c/Users/...)
    # We use as_posix() to ensure forward slashes.
    host_path_str = host_path.as_posix() if is_windows else str(host_path)

    # Base docker command: create directory and copy tutorial
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
    try:
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
        return jsonify({"output": f"[FOAMFlask] [Error] {str(e)}"}), 500

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
    data = request.json
    tutorial = data.get("tutorial")
    command = data.get("command")
    case_dir = data.get("caseDir")

    if not command:
        return {"error": "No command provided"}, 400
    if not tutorial or not case_dir:
        return {"error": "Missing tutorial or caseDir"}, 400

    def stream_container_logs() -> Generator[str, None, None]:
        """Stream container logs for OpenFOAM command execution.
        
        Yields:
            Log lines as HTML-formatted strings.
        """
        client = get_docker_client()
        if client is None:
            # Return a short HTML stream explaining the issue
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
        host_path = Path(case_dir).resolve()
        host_path_str = host_path.as_posix() if platform.system() == "Windows" else str(host_path)

        volumes = {
            host_path_str: {
                "bind": "/tmp/FOAM_Run",
                "mode": "rw",
            }
        }

        # Start the watcher thread before running container
        watcher_thread = threading.Thread(
            target=monitor_foamrun_log, args=(tutorial, case_dir), daemon=True
        )
        watcher_thread.start()

        # Validate and sanitize command input to prevent injection
        if not is_safe_command(command):
            yield f"[FOAMFlask] [Error] Unsafe command detected: {command}<br>"
            yield "[FOAMFlask] [Error] Commands containing shell metacharacters are not allowed.<br>"
            return

        # Determine if command is an OpenFOAM command or a script file
        openfoam_commands = ["blockMesh", "simpleFoam", "pimpleFoam", "decomposePar", "reconstructPar", "foamToVTK", "paraFoam"]
        
        if command.startswith("./") or command in openfoam_commands:
            if command.startswith("./"):
                # Script file - validate path and execute safely
                script_name = command[2:]  # Remove "./" prefix
                if not is_safe_script_name(script_name):
                    yield f"[FOAMFlask] [Error] Unsafe script name: {script_name}<br>"
                    yield "[FOAMFlask] [Error] Script names must be alphanumeric with underscores/hyphens only.<br>"
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
                yield f"[FOAMFlask] [Error] Unsafe command name: {command}<br>"
                yield "[FOAMFlask] [Error] Command names must be alphanumeric with underscores/hyphens only.<br>"
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


# --- Realtime Plotting Endpoints ---
@app.route("/api/available_fields", methods=["GET"])
def api_available_fields() -> Union[Response, Tuple[Response, int]]:
    """
    Get list of available fields in the current case.

    Args:
        tutorial (str): The name of the tutorial.
        caseDir (str): The path to the case directory.

    Returns:
        list: List of available fields.
    """
    tutorial = request.args.get("tutorial")
    if not tutorial:
        return jsonify({"error": "No tutorial specified"}), 400

    case_dir = Path(CASE_ROOT) / tutorial
    if not case_dir.exists():
        return jsonify({"error": "Case directory not found"}), 404

    try:
        fields = get_available_fields(str(case_dir))
        return jsonify({"fields": fields})
    except Exception as e:
        logger.error(f"Error in available_fields: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/plot_data", methods=["GET"])
def api_plot_data() -> Union[Response, Tuple[Response, int]]:
    """
    Get realtime plot data for the current case.

    Args:
        tutorial (str): The name of the tutorial.
        caseDir (str): The path to the case directory.

    Returns:
        dict: Realtime plot data.
    """
    tutorial = request.args.get("tutorial")
    if not tutorial:
        return jsonify({"error": "No tutorial specified"}), 400

    case_dir = Path(CASE_ROOT) / tutorial
    if not case_dir.exists():
        return jsonify({"error": "Case directory not found"}), 404

    try:
        parser = OpenFOAMFieldParser(str(case_dir))
        data = parser.get_all_time_series_data(max_points=100)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting plot data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest_data", methods=["GET"])
def api_latest_data() -> Union[Response, Tuple[Response, int]]:
    """
    Get the latest time step data.

    Args:
        tutorial (str): The name of the tutorial.
        caseDir (str): The path to the case directory.

    Returns:
        dict: Latest time step data.
    """
    tutorial = request.args.get("tutorial")
    if not tutorial:
        return jsonify({"error": "No tutorial specified"}), 400

    case_dir = Path(CASE_ROOT) / tutorial
    if not case_dir.exists():
        return jsonify({"error": "Case directory not found"}), 404

    try:
        parser = OpenFOAMFieldParser(str(case_dir))
        data = parser.get_latest_time_data()
        return jsonify(data if data else {})
    except Exception as e:
        logger.error(f"Error getting latest data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/residuals", methods=["GET"])
def api_residuals() -> Union[Response, Tuple[Response, int]]:
    """
    Get residuals from log file.

    Args:
        tutorial (str): The name of the tutorial.
        caseDir (str): The path to the case directory.

    Returns:
        dict: Residuals from log file.
    """
    tutorial = request.args.get("tutorial")
    if not tutorial:
        return jsonify({"error": "No tutorial specified"}), 400

    case_dir = Path(CASE_ROOT) / tutorial
    if not case_dir.exists():
        return jsonify({"error": "Case directory not found"}), 404

    try:
        parser = OpenFOAMFieldParser(str(case_dir))
        residuals = parser.get_residuals_from_log()
        return jsonify(residuals)
    except Exception as e:
        logger.error(f"Error getting residuals: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# --- PyVista Mesh Visualization Endpoints ---
@app.route("/api/available_meshes", methods=["GET"])
def api_available_meshes() -> Union[Response, Tuple[Response, int]]:
    """
    Get list of available mesh files in the case directory.

    Args:
        tutorial (str): The name of the tutorial.

    Returns:
        list: List of available mesh files.
    """
    tutorial = request.args.get("tutorial")
    if not tutorial:
        return jsonify({"error": "No tutorial specified"}), 400

    try:
        # mesh_visualizer expects strings for paths currently
        mesh_files = mesh_visualizer.get_available_meshes(CASE_ROOT, tutorial)
        return jsonify({"meshes": mesh_files})
    except Exception as e:
        logger.error(f"Error getting available meshes: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/load_mesh", methods=["POST"])
def api_load_mesh() -> Union[Response, Tuple[Response, int]]:
    """
    Load a mesh file and return mesh information.

    Args:
        file_path (str): Path to the mesh file.

    Returns:
        dict: Mesh information.
    """
    data = request.get_json()
    file_path = data.get("file_path")
    for_contour = data.get(
        "for_contour", False
    )  # Get the for_contour flag, default to False

    if not file_path:
        return jsonify({"error": "No file path provided"}), 400

    try:
        logger.info("[FOAMFlask] [api_load_mesh] Mesh loading called")
        mesh_info = mesh_visualizer.load_mesh(file_path)

        if for_contour:
            logger.info(
                "[FOAMFlask] [api_load_mesh] [for_contour] Mesh loading for contour called"
            )

            try:
                # Ensure we have the required fields for contour generation
                mesh_info.setdefault("point_arrays", mesh_info.get("array_names", []))
                # Add any contour-specific processing here if needed
            except Exception as e:
                logger.error(f"Error loading mesh for contour: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

        return jsonify(mesh_info)
    except Exception as e:
        logger.error(f"Error loading mesh: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/mesh_screenshot", methods=["POST"])
def api_mesh_screenshot() -> Union[Response, Tuple[Response, int]]:
    """
    Generate a screenshot of the mesh.

    Args:
        file_path (str): Path to the mesh file.
        width (int): Screenshot width.
        height (int): Screenshot height.
        show_edges (bool): Whether to show edges.
        color (str): Mesh color.
        camera_position (str): Camera position.

    Returns:
        dict: Base64-encoded image.
    """
    data = request.get_json()
    file_path = data.get("file_path")
    width = data.get("width", 800)
    height = data.get("height", 600)
    show_edges = data.get("show_edges", True)
    color = data.get("color", "lightblue")
    camera_position = data.get("camera_position", None)

    if not file_path:
        return jsonify({"error": "No file path provided"}), 400

    try:
        # Add delay for first call
        if not hasattr(api_mesh_screenshot, "_has_been_called"):
            time.sleep(4)  # 4 second delay for first call
            api_mesh_screenshot._has_been_called = True

        img_str = mesh_visualizer.get_mesh_screenshot(
            file_path, width, height, show_edges, color, camera_position
        )

        if img_str:
            return jsonify({"success": True, "image": img_str})
        else:
            return (
                jsonify({"success": False, "error": "Failed to generate screenshot"}),
                500,
            )
    except Exception as e:
        logger.error(f"Error generating mesh screenshot: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/mesh_interactive", methods=["POST"])
def api_mesh_interactive() -> Union[Response, Tuple[Response, int]]:
    """
    Generate an interactive HTML viewer for the mesh.

    Args:
        file_path (str): Path to the mesh file.
        show_edges (bool): Whether to show edges.
        color (str): Mesh color.

    Returns:
        HTML: Interactive mesh viewer page.
    """
    data = request.get_json()
    file_path = data.get("file_path")
    show_edges = data.get("show_edges", True)
    color = data.get("color", "lightblue")

    if not file_path:
        return jsonify({"error": "No file path provided"}), 400

    try:
        # Add a small delay to prevent race conditions
        time.sleep(2)  # 2 second delay

        html_content = mesh_visualizer.get_interactive_viewer_html(
            file_path, show_edges, color
        )

        if html_content:
            return Response(html_content, mimetype="text/html")
        else:
            return (
                jsonify(
                    {"success": False, "error": "Failed to generate interactive viewer"}
                ),
                500,
            )
    except Exception as e:
        logger.error(f"Error generating interactive viewer: {e}", exc_info=True)


@app.route("/run_foamtovtk", methods=["POST"])
def run_foamtovtk() -> Union[Response, Tuple[Dict, int]]:
    """
    Run foamToVTK command in the Docker container.
    """
    data = request.json
    tutorial = data.get("tutorial")
    case_dir = data.get("caseDir")

    if not tutorial or not case_dir:
        return {"error": "Missing tutorial or caseDir"}, 400

    def stream_foamtovtk_logs() -> Generator[str, None, None]:
        """Stream logs for foamToVTK conversion process.
        
        Yields:
            Log lines as HTML-formatted strings.
        """
        client = get_docker_client()
        if client is None:
            yield "[FOAMFlask] [Error] Docker daemon not available. Please start Docker Desktop and try again.<br>"
            return

        container_case_path = posixpath.join(
            "/tmp/FOAM_Run", tutorial
        )
        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"

        # Convert Windows path to POSIX for Docker volumes
        host_path = Path(case_dir).resolve()
        host_path_str = host_path.as_posix() if platform.system() == "Windows" else str(host_path)

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


# --- PyVista Post Processing Visualization Endpoints ---
@app.route("/api/post_process", methods=["POST"])
def post_process() -> Union[Response, Tuple[Response, int]]:
    """Handle post-processing requests for OpenFOAM results.
    
    Returns:
        JSON response with post-processing status or error.
    """
    try:
        # Add your post-processing logic here
        return jsonify({"status": "success", "message": "Post processing endpoint"})
    except Exception as e:
        logger.error(f"Error during post-processing: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/contours/create", methods=["POST", "OPTIONS"])
def create_contour() -> Union[Response, Tuple[Response, int]]:
    """
    Create isosurfaces for the current mesh.

    Returns:
        HTML: Interactive visualization HTML.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return "", 204

    try:
        logger.info("[FOAMFlask] [create_contour] Route handler called")

        # Get JSON data from request
        if not request.is_json:
            logger.error("[FOAMFlask] [create_contour] Request is not JSON")
            logger.error(
                f"[FOAMFlask] [create_contour] Content-Type: {request.content_type}"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Expected JSON, got {request.content_type}",
                    }
                ),
                400,
            )

        request_data = request.get_json()
        logger.info(f"[FOAMFlask] [create_contour] Request data: {request_data}")

        tutorial = request_data.get("tutorial")
        case_dir_str = request_data.get("caseDir")
        scalar_field = request_data.get("scalar_field", "U_Magnitude")
        num_isosurfaces = int(request_data.get("num_isosurfaces", 5))

        logger.info(
            f"[FOAMFlask] [create_contour] Parsed parameters: "
            f"tutorial={tutorial}, caseDir={case_dir_str}, "
            f"scalarField={scalar_field}, numIsosurfaces={num_isosurfaces}"
        )

        if not tutorial:
            error_msg = "Tutorial not specified"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        if not case_dir_str:
            error_msg = "Case directory not specified"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        # Normalize path
        case_dir = Path(case_dir_str)
        if not case_dir.is_absolute():
            case_dir = Path(CASE_ROOT) / case_dir

        logger.info(
            f"[FOAMFlask] [create_contour] Normalized case directory: {case_dir}"
        )

        if not case_dir.exists():
            error_msg = f"Case directory not found: {case_dir}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 404

        logger.info(f"[FOAMFlask] [create_contour] Case directory exists")

        # Find VTK files
        logger.info(
            f"[FOAMFlask] [create_contour] Searching for VTK files in {case_dir}"
        )
        vtk_files = []
        for file in case_dir.rglob("*"):
             if file.suffix in [".vtk", ".vtp", ".vtu"]:
                 vtk_files.append(str(file))

        logger.info(f"[FOAMFlask] [create_contour] Found {len(vtk_files)} VTK files")

        if not vtk_files:
            error_msg = f"No VTK files found in {case_dir}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 404

        # Get latest VTK file
        latest_vtk = max(vtk_files, key=os.path.getmtime)
        logger.info(f"[FOAMFlask] [create_contour] Using VTK file: {latest_vtk}")

        # Load mesh
        logger.info(f"[FOAMFlask] [create_contour] Loading mesh...")
        mesh_info = isosurface_visualizer.load_mesh(latest_vtk)

        if not mesh_info.get("success"):
            error_msg = f"Failed to load mesh: {mesh_info.get('error')}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 500

        logger.info(
            f"[FOAMFlask] [create_contour] Mesh loaded: {mesh_info['n_points']} points"
        )

        # Check scalar field
        available_fields = mesh_info.get("point_arrays", [])
        logger.info(
            f"[FOAMFlask] [create_contour] Available fields: {available_fields}"
        )

        if scalar_field not in available_fields:
            error_msg = f"Scalar field '{scalar_field}' not found. Available: {available_fields}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        logger.info(f"[FOAMFlask] [create_contour] Scalar field '{scalar_field}' found")

        # Get range from request if provided
        custom_range = None
        if (
            "range" in request_data
            and isinstance(request_data["range"], list)
            and len(request_data["range"]) == 2
        ):
            custom_range = request_data["range"]
            logger.info(
                f"[FOAMFlask] [create_contour] Using custom range: {custom_range}"
            )

        # Generate isosurfaces
        logger.info(
            f"[FOAMFlask] [create_contour] Generating {num_isosurfaces} isosurfaces..."
        )
        isosurface_info = isosurface_visualizer.generate_isosurfaces(
            scalar_field=scalar_field,
            num_isosurfaces=num_isosurfaces,
            custom_range=custom_range,
        )

        if not isosurface_info.get("success"):
            error_msg = (
                f"Failed to generate isosurfaces: {isosurface_info.get('error')}"
            )
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 500

        logger.info(
            f"[FOAMFlask] [create_contour] Isosurfaces generated: {isosurface_info['n_points']} points"
        )

        # Generate HTML
        logger.info(f"[FOAMFlask] [create_contour] Generating interactive HTML...")
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
            error_msg = "Empty HTML content generated"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 500

        logger.info(
            f"[FOAMFlask] [create_contour] HTML generated: {len(html_content)} bytes"
        )

        # Return HTML
        logger.info(f"[FOAMFlask] [create_contour] Returning HTML response")
        return Response(html_content, mimetype="text/html")

    except Exception as e:
        logger.error(f"[FOAMFlask] [create_contour] Exception: {str(e)}")
        logger.error(f"[FOAMFlask] [create_contour] Exception type: {type(e).__name__}")
        import traceback

        logger.error(
            f"[FOAMFlask] [create_contour] Traceback:\n{traceback.format_exc()}"
        )

        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


@app.route("/api/upload_vtk", methods=["POST"])
def upload_vtk() -> Union[Response, Tuple[Response, int]]:
    """Upload VTK files for visualization.
    
    Returns:
        JSON response with upload status or error.
    """
    logger.info("[FOAMFlask] [upload_vtk] Received file upload request")
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)

    if not file.filename:
        return jsonify({"success": False, "error": "Invalid filename"}), 400

    filepath = temp_dir / secure_filename(file.filename)

    try:
        # Save the file temporarily
        file.save(str(filepath))

        # Use IsosurfaceVisualizer to handle the mesh loading
        visualizer = IsosurfaceVisualizer()
        result = visualizer.load_mesh(str(filepath))

        if not result.get("success", False):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Failed to load mesh"),
                    }
                ),
                400,
            )

        return jsonify(
            {
                "success": True,
                "filename": file.filename,
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
        return (
            jsonify({"success": False, "error": f"Error processing file: {str(e)}"}),
            500,
        )
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
    # We use a thread to not block the server startup
    # We check if we are in the reloader or not to avoid running twice if possible
    # but re-running is safe.
    threading.Thread(target=run_startup_check, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
