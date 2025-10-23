import os
import posixpath
import platform
import pathlib
import json
import docker
import logging
import threading
import time

from flask import Flask, request, jsonify, render_template_string, Response
from realtime_plots import OpenFOAMFieldParser, get_available_fields

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

# --- Docker client ---
docker_client = docker.from_env()

# --- Load HTML template ---
TEMPLATE_FILE = os.path.join("static", "foamflask_frontend.html")
with open(TEMPLATE_FILE, "r") as f:
    TEMPLATE = f.read()

# --- Helpers ---
def get_tutorials():
    """
    Return a list of available OpenFOAM tutorial cases (category/case).
    
    Returns:
        list: List of available OpenFOAM tutorial cases.
    """
    try:
        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
        docker_cmd = f"bash -c 'source {bashrc} && echo $FOAM_TUTORIALS'"

        container = docker_client.containers.run(
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
        container = docker_client.containers.run(
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
        container = docker_client.containers.run(
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

        container = docker_client.containers.run(
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
