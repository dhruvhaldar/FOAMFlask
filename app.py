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
import pathlib
import platform
import posixpath
import threading
import time
from typing import Dict, List, Optional, Tuple, Union

# Third-party imports
import docker
from docker import DockerClient
from docker.errors import DockerException
from flask import Flask, Response, jsonify, render_template_string, request
from werkzeug.utils import secure_filename

# Local application imports
from backend.mesh.mesher import mesh_visualizer
from backend.plots.realtime_plots import OpenFOAMFieldParser, get_available_fields
from backend.post.isosurface import IsosurfaceVisualizer, isosurface_visualizer

# Initialize Flask application
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("FOAMFlask")

# Global configuration
CONFIG_FILE = "case_config.json"
CONFIG: Optional[Dict] = None
CASE_ROOT: Optional[str] = None
DOCKER_IMAGE: Optional[str] = None
OPENFOAM_VERSION: Optional[str] = None
docker_client: Optional[DockerClient] = None
foamrun_logs: Dict[str, str] = {}  # Maps tutorial names to their log content


def load_config() -> Dict[str, str]:
    """Load configuration from case_config.json with sensible defaults.

    Returns:
        Dictionary containing configuration with keys:
            - CASE_ROOT: Root directory for OpenFOAM cases
            - DOCKER_IMAGE: Docker image to use
            - OPENFOAM_VERSION: OpenFOAM version
    """
    defaults = {
        "CASE_ROOT": os.path.abspath("tutorial_cases"),
        "DOCKER_IMAGE": "haldardhruv/ubuntu_noble_openfoam:v12",
        "OPENFOAM_VERSION": "12",
    }

    if not os.path.exists(CONFIG_FILE):
        return defaults

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
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
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
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


# Load HTML template
TEMPLATE_FILE = os.path.join("static", "html", "foamflask_frontend.html")
try:
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        TEMPLATE = f.read()
except (OSError, UnicodeDecodeError) as e:
    logger.error(
        "[FOAMFlask] Failed to load template file %s: %s", TEMPLATE_FILE, str(e)
    )
    TEMPLATE = "<html><body>Error loading template</body></html>"


def get_tutorials() -> List[str]:
    """Get a list of available OpenFOAM tutorial cases.

    Returns:
        Sorted list of available OpenFOAM tutorial paths (category/case).
    """
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
            tutorials = [os.path.relpath(c, tutorial_root) for c in cases]

        return sorted(tutorials)

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
    host_log_path = pathlib.Path(case_dir) / tutorial / "log.FoamRun"
    output_file = pathlib.Path(case_dir) / tutorial / "foamrun_logs.txt"

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


@app.route("/get_case_root", methods=["GET"])
def get_case_root() -> Response:
    """Get the case root directory.

    Returns:
        JSON response containing the case root directory.
    """
    return jsonify({"caseDir": CASE_ROOT})


@app.route("/set_case", methods=["POST"])
def set_case() -> Response:
    """Set the case root directory.

    Returns:
        JSON response with status and case directory information.
    """
    global CASE_ROOT

    data = request.get_json()
    if not data or "caseDir" not in data or not data["caseDir"]:
        return jsonify({"output": "[FOAMFlask] [Error] No caseDir provided"})

    try:
        case_dir = os.path.abspath(data["caseDir"])
        os.makedirs(case_dir, exist_ok=True)
        CASE_ROOT = case_dir
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
def set_docker_config() -> Response:
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
def load_tutorial():
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
    container_run_path = f"/home/foam/OpenFOAM/{OPENFOAM_VERSION}/run"
    container_case_path = posixpath.join(container_run_path, tutorial)

    # Convert Windows paths to POSIX style for Docker
    host_path = pathlib.Path(CASE_ROOT).resolve()
    is_windows = platform.system() == "Windows"
    if is_windows:
        host_path = host_path.as_posix()  # Docker expects POSIX paths on Windows

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
        container = client.containers.run(
            DOCKER_IMAGE,
            docker_cmd,
            detach=True,
            tty=True,
            stdout=True,
            stderr=True,
            volumes={CASE_ROOT: {"bind": container_run_path, "mode": "rw"}},
            working_dir=container_run_path,
            remove=True,
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
def run_case():
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

    def stream_container_logs():
        client = get_docker_client()
        if client is None:
            # Return a short HTML stream explaining the issue
            yield (
                "[FOAMFlask] [Error] Docker daemon not available. "
                "Please start Docker Desktop and re-run the case.<br>"
            )
            return

        container_case_path = posixpath.join(
            f"/home/foam/OpenFOAM/{OPENFOAM_VERSION}/run", tutorial
        )
        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"

        # Convert Windows path to POSIX for Docker volumes
        host_path = pathlib.Path(case_dir).resolve().as_posix()
        volumes = {
            host_path: {
                "bind": f"/home/foam/OpenFOAM/{OPENFOAM_VERSION}/run",
                "mode": "rw",
            }
        }

        # Start the watcher thread before running container
        watcher_thread = threading.Thread(
            target=monitor_foamrun_log, args=(tutorial, case_dir), daemon=True
        )
        watcher_thread.start()

        # Determine if command is an OpenFOAM command or a script file
        openfoam_commands = ["blockMesh", "simpleFoam", "pimpleFoam", "decomposePar", "reconstructPar", "foamToVTK", "paraFoam"]
        
        if command.startswith("./") or command in openfoam_commands:
            if command.startswith("./"):
                # Script file - make executable and run
                docker_cmd = f"bash -c 'source {bashrc} && cd {container_case_path} && chmod +x {command} && {command}'"
            else:
                # OpenFOAM command - run directly after sourcing bashrc
                docker_cmd = f"bash -c 'source {bashrc} && cd {container_case_path} && {command}'"
        else:
            # Fallback to original behavior
            docker_cmd = f"bash -c 'source {bashrc} && cd {container_case_path} && chmod +x {command} && ./{command}'"

        container = client.containers.run(
            DOCKER_IMAGE,
            docker_cmd,
            detach=True,
            tty=False,
            volumes=volumes,
            working_dir=container_case_path,
        )

        try:
            # Stream logs line by line
            for line in container.logs(stream=True):
                decoded = line.decode(errors="ignore")
                for subline in decoded.splitlines():
                    yield subline + "<br>"

        finally:
            try:
                container.kill()
            except:
                pass
            try:
                container.remove()
            except:
                logger.error("[FOAMPilot] Could not remove container")

    return Response(stream_container_logs(), mimetype="text/html")


# --- Realtime Plotting Endpoints ---
@app.route("/api/available_fields", methods=["GET"])
def api_available_fields():
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

    case_dir = os.path.join(CASE_ROOT, tutorial)
    if not os.path.exists(case_dir):
        return jsonify({"error": "Case directory not found"}), 404

    try:
        fields = get_available_fields(case_dir)
        return jsonify({"fields": fields})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plot_data", methods=["GET"])
def api_plot_data():
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

    case_dir = os.path.join(CASE_ROOT, tutorial)
    if not os.path.exists(case_dir):
        return jsonify({"error": "Case directory not found"}), 404

    try:
        parser = OpenFOAMFieldParser(case_dir)
        data = parser.get_all_time_series_data(max_points=100)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting plot data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest_data", methods=["GET"])
def api_latest_data():
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

    case_dir = os.path.join(CASE_ROOT, tutorial)
    if not os.path.exists(case_dir):
        return jsonify({"error": "Case directory not found"}), 404

    try:
        parser = OpenFOAMFieldParser(case_dir)
        data = parser.get_latest_time_data()
        return jsonify(data if data else {})
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/residuals", methods=["GET"])
def api_residuals():
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

    case_dir = os.path.join(CASE_ROOT, tutorial)
    if not os.path.exists(case_dir):
        return jsonify({"error": "Case directory not found"}), 404

    try:
        parser = OpenFOAMFieldParser(case_dir)
        residuals = parser.get_residuals_from_log()
        return jsonify(residuals)
    except Exception as e:
        logger.error(f"Error getting residuals: {e}")
        return jsonify({"error": str(e)}), 500


# --- PyVista Mesh Visualization Endpoints ---
@app.route("/api/available_meshes", methods=["GET"])
def api_available_meshes():
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
        mesh_files = mesh_visualizer.get_available_meshes(CASE_ROOT, tutorial)
        return jsonify({"meshes": mesh_files})
    except Exception as e:
        logger.error(f"Error getting available meshes: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/load_mesh", methods=["POST"])
def api_load_mesh():
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
                logger.error(f"Error loading mesh for contour: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify(mesh_info)
    except Exception as e:
        logger.error(f"Error loading mesh: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/mesh_screenshot", methods=["POST"])
def api_mesh_screenshot():
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
        logger.error(f"Error generating mesh screenshot: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/mesh_interactive", methods=["POST"])
def api_mesh_interactive():
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
        logger.error(f"Error generating interactive viewer: {e}")


@app.route("/run_foamtovtk", methods=["POST"])
def run_foamtovtk():
    """
    Run foamToVTK command in the Docker container.
    """
    data = request.json
    tutorial = data.get("tutorial")
    case_dir = data.get("caseDir")

    if not tutorial or not case_dir:
        return {"error": "Missing tutorial or caseDir"}, 400

    def stream_foamtovtk_logs():
        client = get_docker_client()
        if client is None:
            yield "[FOAMFlask] [Error] Docker daemon not available. Please start Docker Desktop and try again.<br>"
            return

        container_case_path = posixpath.join(
            f"/home/foam/OpenFOAM/{OPENFOAM_VERSION}/run", tutorial
        )
        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"

        # Convert Windows path to POSIX for Docker volumes
        host_path = pathlib.Path(case_dir).resolve().as_posix()
        volumes = {
            host_path: {
                "bind": f"/home/foam/OpenFOAM/{OPENFOAM_VERSION}/run",
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

        container = client.containers.run(
            DOCKER_IMAGE,
            docker_cmd,
            detach=True,
            tty=False,
            volumes=volumes,
            working_dir=container_case_path,
        )

        try:
            # Stream logs line by line
            for line in container.logs(stream=True):
                decoded = line.decode(errors="ignore")
                for subline in decoded.splitlines():
                    yield subline + "<br>"

        finally:
            try:
                container.kill()
            except:
                pass
            try:
                container.remove()
            except:
                logger.error("[FOAMFlask] Could not remove container")

    return Response(stream_foamtovtk_logs(), mimetype="text/html")


# --- PyVista Post Processing Visualization Endpoints ---
@app.route("/api/post_process", methods=["POST"])
def post_process():
    try:
        # Add your post-processing logic here
        return jsonify({"status": "success", "message": "Post processing endpoint"})
    except Exception as e:
        logger.error(f"Error during post-processing: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/contours/create", methods=["POST", "OPTIONS"])
def create_contour():
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
        case_dir = request_data.get("caseDir")
        scalar_field = request_data.get("scalar_field", "U_Magnitude")
        num_isosurfaces = int(request_data.get("num_isosurfaces", 5))

        logger.info(
            f"[FOAMFlask] [create_contour] Parsed parameters: "
            f"tutorial={tutorial}, caseDir={case_dir}, "
            f"scalarField={scalar_field}, numIsosurfaces={num_isosurfaces}"
        )

        if not tutorial:
            error_msg = "Tutorial not specified"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        if not case_dir:
            error_msg = "Case directory not specified"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        # Normalize path
        if not os.path.isabs(case_dir):
            case_dir = os.path.join(CASE_ROOT, case_dir)

        logger.info(
            f"[FOAMFlask] [create_contour] Normalized case directory: {case_dir}"
        )

        if not os.path.exists(case_dir):
            error_msg = f"Case directory not found: {case_dir}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 404

        logger.info(f"[FOAMFlask] [create_contour] Case directory exists")

        # Find VTK files
        logger.info(
            f"[FOAMFlask] [create_contour] Searching for VTK files in {case_dir}"
        )
        vtk_files = []
        for root, _, files in os.walk(case_dir):
            for file in files:
                if file.endswith((".vtk", ".vtp", ".vtu")):
                    vtk_files.append(os.path.join(root, file))

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
def upload_vtk():
    logger.info("[FOAMFlask] [upload_vtk] Received file upload request")
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    temp_dir = os.path.join("temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    filepath = os.path.join(temp_dir, secure_filename(file.filename))

    try:
        # Save the file temporarily
        file.save(filepath)

        # Use IsosurfaceVisualizer to handle the mesh loading
        visualizer = IsosurfaceVisualizer()
        result = visualizer.load_mesh(filepath)

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
            if "filepath" in locals() and os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.error(f"Error cleaning up file {filepath}: {e}")


if __name__ == "__main__":
    # Initialize configuration
    CONFIG = load_config()
    CASE_ROOT = CONFIG["CASE_ROOT"]
    DOCKER_IMAGE = CONFIG["DOCKER_IMAGE"]
    OPENFOAM_VERSION = CONFIG["OPENFOAM_VERSION"]

    # Ensure case directory exists
    os.makedirs(CASE_ROOT, exist_ok=True)

    # Start the Flask application
    app.run(host="0.0.0.0", port=5000, debug=True)
