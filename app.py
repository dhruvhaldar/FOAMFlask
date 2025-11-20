# Standard library imports
import json
import logging
import os
import pathlib
import platform
import posixpath
import threading
import time

# Third-party imports
import docker
from flask import Flask, Response, jsonify, render_template_string, request

# Local application imports
from backend.mesh.mesher import mesh_visualizer
from backend.plots.realtime_plots import OpenFOAMFieldParser, get_available_fields

# Backend API handlers
from backend.post.isosurface import isosurface_visualizer

app = Flask(__name__)

# --- Logging ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("FOAMFlask")

# --- Config file ---
CONFIG_FILE = "case_config.json"

def load_config():
    """
    Load configuration from case_config.json with sensible defaults.
    
    Returns:
        dict: Configuration dictionary.
    """
    defaults = {
        "CASE_ROOT": os.path.abspath("tutorial_cases"),
        "DOCKER_IMAGE": "haldardhruv/ubuntu_noble_openfoam:v12",
        "OPENFOAM_VERSION": "12"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return {**defaults, **data}
        except Exception as e:
            logger.warning(f"[WARN] Could not load config file: {e}")
    return defaults

def save_config(updates: dict):
    """
    Save configuration back to case_config.json.
    
    Args:
        updates (dict): Dictionary of updates to the configuration.
    """
    config = load_config()
    config.update(updates)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"[ERROR] Could not save config: {e}")

# --- Load config ---
CONFIG = load_config()
CASE_ROOT = CONFIG["CASE_ROOT"]
DOCKER_IMAGE = CONFIG["DOCKER_IMAGE"]
OPENFOAM_VERSION = CONFIG["OPENFOAM_VERSION"]

from docker.errors import DockerException  # add with other imports

# --- Docker client ---
docker_client = None

def get_docker_client():
    """
    Lazily create a Docker client and handle the case
    where Docker Desktop / daemon is not running.
    """
    global docker_client
    if docker_client is not None:
        return docker_client

    try:
        client = docker.from_env()
        # Cheap liveness check: will fail fast if daemon is down
        client.ping()
        logger.info("[FOAMFlask] Connected to Docker daemon")
        docker_client = client
        return docker_client
    except DockerException as e:
        logger.error(
            "[FOAMFlask] Docker daemon not available. "
            "Make sure Docker Desktop is running. "
            f"Details: {e}"
        )
        return None

def docker_unavailable_response():
    return jsonify({
        "output": (
            "[FOAMFlask] [Error] Docker daemon not available. "
            "Please start Docker Desktop and reload the page."
        )
    }), 503

# --- Load HTML template ---
TEMPLATE_FILE = os.path.join("static", "html", "foamflask_frontend.html")
with open(TEMPLATE_FILE, "r", encoding='utf-8') as f:
    TEMPLATE = f.read()

# --- Helpers ---
def get_tutorials():
    """
    Return a list of available OpenFOAM tutorial cases (category/case).
    
    Returns:
        list: List of available OpenFOAM tutorial cases.
    """
    try:
        client = get_docker_client()
        if client is None:
            logger.warning("[FOAMFlask] get_tutorials called but Docker Desktop is not running")
            return []

        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
        docker_cmd = f"bash -c 'source {bashrc} && echo $FOAM_TUTORIALS'"

        container = client.containers.run(
            DOCKER_IMAGE, docker_cmd, remove=True,
            stdout=True, stderr=True, tty=True
        )
        tutorial_root = container.decode().strip()
        if not tutorial_root:
            return []

        # Find actual tutorial cases
        docker_cmd = (
            "bash -c 'find " + tutorial_root +
            " -mindepth 2 -maxdepth 2 -type d "
            "-exec test -d {}/system -a -d {}/constant \\; -print'"
        )
        container = client.containers.run(
            DOCKER_IMAGE, docker_cmd, remove=True,
            stdout=True, stderr=True, tty=True
        )
        cases = container.decode().splitlines()

        # Normalize only if running on Windows
        if platform.system() == "Windows":
            tutorials = [posixpath.relpath(c, tutorial_root) for c in cases]
        else:
            tutorials = [os.path.relpath(c, tutorial_root) for c in cases]

        tutorials.sort()
        return tutorials

    except Exception as e:
        logger.error(f"[FOAMFlask] Could not fetch tutorials: {e}")
        return []

# --- Global storage for FoamRun logs ---
foamrun_logs = {}  # { "<tutorial_name>": "<log content>" }

def monitor_foamrun_log(tutorial, case_dir):
    """
    Watch for log.FoamRun, capture it in foamrun_logs and write it to a file.
    
    Args:
        tutorial (str): The name of the tutorial.
        caseDir (str): The path to the case directory.
    """
    import pathlib
    import time

    host_log_path = pathlib.Path(case_dir) / tutorial / "log.FoamRun"
    output_file = pathlib.Path(case_dir) / tutorial / "foamrun_logs.txt"

    timeout = 300  # seconds max wait
    interval = 1   # check every 1 second
    elapsed = 0

    while elapsed < timeout:
        if host_log_path.exists():
            log_content = host_log_path.read_text()
            foamrun_logs[tutorial] = log_content

            # Write to file
            try:
                output_file.write_text(log_content)
                logger.info(f"[FOAMFlask] Captured log.FoamRun for tutorial '{tutorial}' and wrote to {output_file}")
            except Exception as e:
                logger.error(f"[FOAMFlask] Could not write foamrun_logs to file: {e}")

            return

        time.sleep(interval)
        elapsed += interval

    logger.warning(f"[FOAMFlask] Timeout: log.FoamRun not found for '{tutorial}'")

# --- Routes ---
@app.route("/")
def index():
    """
    Get the index page.
    
    Returns:
        str: The index page.
    """
    tutorials = get_tutorials()
    options_html = "\n".join([f"<option value='{t}'>{t}</option>" for t in tutorials])
    return render_template_string(TEMPLATE, options=options_html, CASE_ROOT=CASE_ROOT)

@app.route("/get_case_root", methods=["GET"])
def get_case_root():
    """
    Get the case root directory.
    
    Returns:
        dict: The case root directory.
    """
    return jsonify({"caseDir": CASE_ROOT})

@app.route("/set_case", methods=["POST"])
def set_case():
    """
    Set the case root directory.
    
    Args:
        caseDir (str): The case root directory.
    
    Returns:
        dict: The output of the command.
    """
    global CASE_ROOT
    data = request.get_json()
    case_dir = data.get("caseDir")
    if not case_dir:
        return jsonify({"output": "[FOAMFlask] [Error] No caseDir provided"})
    case_dir = os.path.abspath(case_dir)
    os.makedirs(case_dir, exist_ok=True)
    CASE_ROOT = case_dir
    save_config({"CASE_ROOT": CASE_ROOT})
    return jsonify({
        "output": f"INFO::[FOAMFlask] Case root set to: {CASE_ROOT}",
        "caseDir": CASE_ROOT
    })

@app.route("/get_docker_config", methods=["GET"])
def get_docker_config():
    """
    Get the Docker configuration.
    
    Returns:
        dict: The Docker configuration.
    """
    return jsonify({
        "dockerImage": DOCKER_IMAGE,
        "openfoamVersion": OPENFOAM_VERSION
    })

@app.route("/set_docker_config", methods=["POST"])
def set_docker_config():
    """
    Set the Docker configuration.
    
    Args:
        dockerImage (str): The Docker image to use.
        openfoamVersion (str): The OpenFOAM version to use.
    
    Returns:
        dict: The output of the command.
    """
    global DOCKER_IMAGE, OPENFOAM_VERSION
    data = request.get_json()
    if "dockerImage" in data:
        DOCKER_IMAGE = data["dockerImage"]
    if "openfoamVersion" in data:
        OPENFOAM_VERSION = str(data["openfoamVersion"])
    save_config({
        "DOCKER_IMAGE": DOCKER_IMAGE,
        "OPENFOAM_VERSION": OPENFOAM_VERSION
    })
    return jsonify({
        "output": f"INFO::[FOAMFlask] Docker config updated",
        "dockerImage": DOCKER_IMAGE,
        "openfoamVersion": OPENFOAM_VERSION
    })

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
            remove=True
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
            host_path: {"bind": f"/home/foam/OpenFOAM/{OPENFOAM_VERSION}/run", "mode": "rw"}
        }

        # Start the watcher thread before running container
        watcher_thread = threading.Thread(
            target=monitor_foamrun_log,
            args=(tutorial, case_dir),
            daemon=True
        )
        watcher_thread.start()

        docker_cmd = f"bash -c 'source {bashrc} && cd {container_case_path} && chmod +x {command} && ./{command}'"

        container = client.containers.run(
            DOCKER_IMAGE,
            docker_cmd,
            detach=True,
            tty=False,
            volumes=volumes,
            working_dir=container_case_path
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
    
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    try:
        mesh_info = mesh_visualizer.load_mesh(file_path)
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
        if not hasattr(api_mesh_screenshot, '_has_been_called'):
            time.sleep(4)  # 4 second delay for first call
            api_mesh_screenshot._has_been_called = True

        img_str = mesh_visualizer.get_mesh_screenshot(
            file_path, width, height, show_edges, color, camera_position
        )
        
        if img_str:
            return jsonify({"success": True, "image": img_str})
        else:
            return jsonify({"success": False, "error": "Failed to generate screenshot"}), 500
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
            return Response(html_content, mimetype='text/html')
        else:
            return jsonify({"success": False, "error": "Failed to generate interactive viewer"}), 500
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
            host_path: {"bind": f"/home/foam/OpenFOAM/{OPENFOAM_VERSION}/run", "mode": "rw"}
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
            working_dir=container_case_path
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
@app.route('/api/post_process', methods=['POST'])
def post_process():
    try:
        # Add your post-processing logic here
        return jsonify({"status": "success", "message": "Post processing endpoint"})
    except Exception as e:
        logger.error(f"Error during post-processing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/contours/create', methods=['POST', 'OPTIONS'])
def create_contour():
    """
    Create isosurfaces for the current mesh.
    
    Returns:
        HTML: Interactive visualization HTML.
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        logger.info("[FOAMFlask] [create_contour] Route handler called")
        
        # Get JSON data from request
        if not request.is_json:
            logger.error("[FOAMFlask] [create_contour] Request is not JSON")
            logger.error(f"[FOAMFlask] [create_contour] Content-Type: {request.content_type}")
            return jsonify({
                "success": False,
                "error": f"Expected JSON, got {request.content_type}"
            }), 400
        
        request_data = request.get_json()
        logger.info(f"[FOAMFlask] [create_contour] Request data: {request_data}")
        
        tutorial = request_data.get('tutorial')
        case_dir = request_data.get('caseDir')
        scalar_field = request_data.get('scalar_field', 'U_Magnitude')
        num_isosurfaces = int(request_data.get('num_isosurfaces', 5))
        
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
        
        logger.info(f"[FOAMFlask] [create_contour] Normalized case directory: {case_dir}")
        
        if not os.path.exists(case_dir):
            error_msg = f"Case directory not found: {case_dir}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 404
        
        logger.info(f"[FOAMFlask] [create_contour] Case directory exists")
        
        # Find VTK files
        logger.info(f"[FOAMFlask] [create_contour] Searching for VTK files in {case_dir}")
        vtk_files = []
        for root, _, files in os.walk(case_dir):
            for file in files:
                if file.endswith(('.vtk', '.vtp', '.vtu')):
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
        
        if not mesh_info.get('success'):
            error_msg = f"Failed to load mesh: {mesh_info.get('error')}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 500
        
        logger.info(f"[FOAMFlask] [create_contour] Mesh loaded: {mesh_info['n_points']} points")
        
        # Check scalar field
        available_fields = mesh_info.get('point_arrays', [])
        logger.info(f"[FOAMFlask] [create_contour] Available fields: {available_fields}")
        
        if scalar_field not in available_fields:
            error_msg = f"Scalar field '{scalar_field}' not found. Available: {available_fields}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400
        
        logger.info(f"[FOAMFlask] [create_contour] Scalar field '{scalar_field}' found")
        
        # Get range from request if provided
        custom_range = None
        if 'range' in request_data and isinstance(request_data['range'], list) and len(request_data['range']) == 2:
            custom_range = request_data['range']
            logger.info(f"[FOAMFlask] [create_contour] Using custom range: {custom_range}")
        
        # Generate isosurfaces
        logger.info(f"[FOAMFlask] [create_contour] Generating {num_isosurfaces} isosurfaces...")
        isosurface_info = isosurface_visualizer.generate_isosurfaces(
            scalar_field=scalar_field,
            num_isosurfaces=num_isosurfaces,
            custom_range=custom_range
        )
        
        if not isosurface_info.get('success'):
            error_msg = f"Failed to generate isosurfaces: {isosurface_info.get('error')}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 500
        
        logger.info(f"[FOAMFlask] [create_contour] Isosurfaces generated: {isosurface_info['n_points']} points")
        
        # Generate HTML
        logger.info(f"[FOAMFlask] [create_contour] Generating interactive HTML...")
        html_content = isosurface_visualizer.get_interactive_html(
            scalar_field=scalar_field,
            show_base_mesh=True,
            base_mesh_opacity=0.25,
            contour_opacity=0.8,
            contour_color='red',
            colormap='viridis',
            show_isovalue_slider=True
        )
        
        if not html_content:
            error_msg = "Empty HTML content generated"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 500
        
        logger.info(f"[FOAMFlask] [create_contour] HTML generated: {len(html_content)} bytes")
        
        # Return HTML
        logger.info(f"[FOAMFlask] [create_contour] Returning HTML response")
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        logger.error(f"[FOAMFlask] [create_contour] Exception: {str(e)}")
        logger.error(f"[FOAMFlask] [create_contour] Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"[FOAMFlask] [create_contour] Traceback:\n{traceback.format_exc()}")
        
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
