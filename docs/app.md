# FOAMPilot API Documentation

This document provides comprehensive documentation for the FOAMPilot API, which serves as the backend for OpenFOAM case management and visualization.

## Overview

The FOAMPilot API is a Flask-based web service that provides endpoints for:
- Managing OpenFOAM tutorial cases
- Running OpenFOAM simulations in Docker containers
- Retrieving simulation data and results
- Real-time monitoring of simulation progress
- Configuration management

## Table of Contents

- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Case Management](#case-management)
  - [Simulation Control](#simulation-control)
  - [Data Retrieval](#data-retrieval)
  - [Mesh Visualization](#mesh-visualization)
  - [Post-Processing](#post-processing)
  - [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Development](#development)

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

## Endpoints

### Case Management

#### `GET /`
**Description**: Render the index page with a list of available OpenFOAM tutorials.

**Response**:
- `200 OK`: Returns HTML page with tutorial selection interface

**Example**:
```bash
curl http://localhost:5000/
```

#### `GET /get_tutorials`
**Description**: List all available OpenFOAM tutorial cases.

**Response**:
- `200 OK`: Returns JSON array of tutorial paths (e.g., `["incompressible/simpleFoam/airFoil2D"]`)

**Example**:
```bash
curl http://localhost:5000/get_tutorials
```

### Simulation Control

#### `POST /run`
**Description**: Execute an OpenFOAM case in a Docker container.

**Request Body**:
```json
{
  "tutorial": "incompressible/simpleFoam/airFoil2D",
  "command": "blockMesh",
  "caseDir": "/path/to/case"
}
```

**Parameters**:
- `tutorial` (required): Name of the tutorial to run
- `command` (required): OpenFOAM command to execute (e.g., "blockMesh", "simpleFoam")
- `caseDir` (required): Path to the case directory

**Response**:
- `200 OK`: Returns simulation output as streamed text/event-stream
- `400 Bad Request`: If required parameters are missing
- `404 Not Found`: If case directory doesn't exist

**Example**:
```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{"tutorial": "fluid/aerofoilNACA0012Steady", "command": "blockMesh", "caseDir": "/path/to/case"}'
```

### Data Retrieval

#### `GET /api/available_fields`
**Description**: List all available fields in the current case.

**Query Parameters**:
- `tutorial` (required): Name of the tutorial
- `caseDir`: Path to case directory (optional)

**Response**:
- `200 OK`: JSON object with array of field names
- `400 Bad Request`: If tutorial parameter is missing
- `404 Not Found`: If case directory doesn't exist
- `500 Internal Server Error`: For other errors

**Example**:
```bash
curl "http://localhost:5000/api/available_fields?tutorial=incompressible/simpleFoam/airFoil2D"
```

#### `GET /api/latest_data`
**Description**: Get the latest time step data.

**Query Parameters**:
- `tutorial` (required): Name of the tutorial
- `caseDir`: Path to case directory (optional)

**Response**:
- `200 OK`: JSON object with latest time step data
- `400 Bad Request`: If tutorial parameter is missing
- `404 Not Found`: If case directory doesn't exist
- `500 Internal Server Error`: For other errors

#### `GET /api/plot_data`
**Description**: Get real-time plot data for the current case.

**Query Parameters**:
- `tutorial` (required): Name of the tutorial
- `caseDir`: Path to case directory (optional)
- `max_points`: Maximum number of data points to return (default: 100)

**Response**:
- `200 OK`: JSON object with time series data
- `400 Bad Request`: If tutorial parameter is missing
- `404 Not Found`: If case directory doesn't exist
- `500 Internal Server Error`: For other errors

#### `GET /api/residuals`
**Description**: Get residuals data from OpenFOAM log file.

**Query Parameters**:
- `tutorial` (required): Name of the tutorial

**Response**:
- `200 OK`: JSON object with residuals data (time, Ux, Uy, Uz, p, k, epsilon, omega)
- `400 Bad Request`: If tutorial parameter is missing
- `404 Not Found`: If case directory doesn't exist
- `500 Internal Server Error`: For other errors

**Example**:
```bash
curl "http://localhost:5000/api/residuals?tutorial=incompressible/simpleFoam/airFoil2D"
```

### Mesh Visualization

#### `GET /api/available_meshes`
**Description**: Get list of available mesh files in the case directory.

**Query Parameters**:
- `tutorial` (required): Name of the tutorial

**Response**:
- `200 OK`: JSON object with array of mesh file information
- `400 Bad Request`: If tutorial parameter is missing
- `500 Internal Server Error`: For other errors

**Example**:
```bash
curl "http://localhost:5000/api/available_meshes?tutorial=incompressible/simpleFoam/airFoil2D"
```

#### `POST /api/load_mesh`
**Description**: Load a mesh file for visualization.

**Request Body**:
```json
{
  "tutorial": "incompressible/simpleFoam/airFoil2D",
  "meshFile": "constant/polyMesh"
}
```

**Response**:
- `200 OK`: JSON object with mesh data and visualization information
- `400 Bad Request`: If required parameters are missing
- `404 Not Found`: If mesh file doesn't exist
- `500 Internal Server Error`: For other errors

#### `POST /api/mesh_screenshot`
**Description**: Generate a screenshot of the mesh visualization.

**Request Body**:
```json
{
  "tutorial": "incompressible/simpleFoam/airFoil2D",
  "meshFile": "constant/polyMesh",
  "camera": "front",
  "width": 800,
  "height": 600
}
```

**Response**:
- `200 OK`: JSON object with base64-encoded screenshot image
- `400 Bad Request`: If required parameters are missing
- `500 Internal Server Error`: For other errors

#### `POST /api/mesh_interactive`
**Description**: Generate interactive HTML mesh visualization.

**Request Body**:
```json
{
  "tutorial": "incompressible/simpleFoam/airFoil2D",
  "meshFile": "constant/polyMesh"
}
```

**Response**:
- `200 OK`: HTML content for interactive mesh viewer
- `400 Bad Request`: If required parameters are missing
- `500 Internal Server Error`: For other errors

### Post-Processing

#### `POST /api/contours/create`
**Description**: Generate 3D contour visualization for a scalar field.

**Request Body**:
```json
{
  "tutorial": "incompressible/simpleFoam/airFoil2D",
  "scalarField": "p",
  "numIsosurfaces": 10,
  "range": [0, 100]
}
```

**Parameters**:
- `tutorial` (required): Name of the tutorial
- `scalarField` (required): Field name to visualize (e.g., "p", "U", "k")
- `numIsosurfaces` (optional): Number of isosurfaces (default: 10)
- `range` (optional): Min/max values for contour range

**Response**:
- `200 OK`: HTML content for interactive contour visualization
- `400 Bad Request`: If required parameters are missing
- `500 Internal Server Error`: For other errors

#### `POST /api/upload_vtk`
**Description**: Upload a VTK file for visualization.

**Request Body**: `multipart/form-data`
- `file`: VTK file to upload
- `tutorial`: Tutorial name (optional)

**Response**:
- `200 OK`: JSON object with uploaded file information
- `400 Bad Request`: If no file is uploaded
- `500 Internal Server Error`: For other errors

### Configuration

#### `GET /get_case_root`
**Description**: Get the root directory for case storage.

**Response**:
- `200 OK`: JSON object with `caseDir` path

**Example**:
```bash
curl http://localhost:5000/get_case_root
```

#### `POST /set_case`
**Description**: Set the root directory for case storage.

**Request Body**:
```json
{
  "caseDir": "/path/to/case/directory"
}
```

**Response**:
- `200 OK`: JSON object with status and new case directory
- `400 Bad Request`: If case directory is not provided

**Example**:
```bash
curl -X POST http://localhost:5000/set_case \
  -H "Content-Type: application/json" \
  -d '{"caseDir": "/path/to/case/directory"}'
```

#### `GET /get_docker_config`
**Description**: Get current Docker configuration.

**Response**:
```json
{
  "dockerImage": "haldardhruv/ubuntu_noble_openfoam:v12",
  "openfoamVersion": "12"
}
```

#### `POST /set_docker_config`
**Description**: Set Docker configuration.

**Request Body**:
```json
{
  "dockerImage": "haldardhruv/ubuntu_noble_openfoam:v12",
  "openfoamVersion": "12"
}
```

**Response**:
- `200 OK`: JSON object with status and new configuration
- `400 Bad Request`: If required parameters are missing

**Example**:
```bash
curl -X POST http://localhost:5000/set_docker_config \
  -H "Content-Type: application/json" \
  -d '{"dockerImage": "haldardhruv/ubuntu_noble_openfoam:v12", "openfoamVersion": "12"}'
```

## Error Handling

All error responses follow the same format:
```json
{
  "error": "Error message describing the issue"
}
```

Common HTTP status codes:
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Requested resource not found
- `500 Internal Server Error`: Server-side error occurred

## Examples

### Running a Simulation

1. List available tutorials:
   ```bash
   curl http://localhost:5000/get_tutorials
   ```

2. Run a specific tutorial, e.g., `incompressible/simpleFoam/airFoil2D`, with the `blockMesh` command and specify the case directory `/path/to/case`:
   ```bash
   curl -X POST http://localhost:5000/run \
     -H "Content-Type: application/json" \
     -d '{"tutorial": "incompressible/simpleFoam/airFoil2D", "command": "blockMesh", "caseDir": "/path/to/case"}'
   ```

3. Monitor simulation progress for the `incompressible/simpleFoam/airFoil2D` tutorial:
   ```bash
   # In a separate terminal
   curl "http://localhost:5000/api/residuals?tutorial=incompressible/simpleFoam/airFoil2D"
   ```

## Development

### Prerequisites
- Python 3.8+
- Docker
- OpenFOAM (optional, for local development)

### Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the development server:
   ```bash
   python app.py
   ```

### Configuration

Create a `case_config.json` file in the project root with the following structure:
```json
{
  "CASE_ROOT": "/path/to/cases",
  "DOCKER_IMAGE": "haldardhruv/ubuntu_noble_openfoam:v12",
  "OPENFOAM_VERSION": "12"
}
```

---

## Functions

### api_available_fields
- Route: `GET /api/available_fields`
- Description: Get list of available fields in the current case.
- Args:
  - `tutorial` (str) — The name of the tutorial.
  - `caseDir` (str) — The path to the case directory.
- Returns: `list` — List of available fields.

Source (excerpt):
```python
@app.route("/api/available_fields", methods=["GET"])
def api_available_fields():
    """
    Get list of available fields in the current case.
    ...
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
```

---

### api_latest_data
- Route: `GET /api/latest_data`
- Description: Get the latest time step data.
- Args:
  - `tutorial` (str)
  - `caseDir` (str)
- Returns: `dict` — Latest time step data.

Source (excerpt):
```python
@app.route("/api/latest_data", methods=["GET"])
def api_latest_data():
    """
    Get the latest time step data.
    ...
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
```

---

### api_plot_data
- Route: `GET /api/plot_data`
- Description: Get realtime plot data for the current case.
- Args:
  - `tutorial` (str)
  - `caseDir` (str)
- Returns: `dict` — Realtime plot data.

Source (excerpt):
```python
@app.route("/api/plot_data", methods=["GET"])
def api_plot_data():
    """
    Get realtime plot data for the current case.
    ...
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
```

---

### api_residuals
- Route: `GET /api/residuals`
- Description: Get residuals from log file.
- Args:
  - `tutorial` (str)
  - `caseDir` (str)
- Returns: `dict` — Residuals from log file.

Source (excerpt):
```python
@app.route("/api/residuals", methods=["GET"])
def api_residuals():
    """
    Get residuals from log file.
    ...
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
```

---

### get_case_root
- Route: `GET /get_case_root`
- Description: Get the case root directory.
- Returns: `dict` — The case root directory.

Source:
```python
@app.route("/get_case_root", methods=["GET"])
def get_case_root():
    """
    Get the case root directory.
    Returns:
        dict: The case root directory.
    """
    return jsonify({"caseDir": CASE_ROOT})
```

---

### get_docker_config
- Route: `GET /get_docker_config`
- Description: Get the Docker configuration.
- Returns: `dict` — Docker image and OpenFOAM version.

Source:
```python
@app.route("/get_docker_config", methods=["GET"])
def get_docker_config():
    """
    Get the Docker configuration.
    """
    return jsonify({
        "dockerImage": DOCKER_IMAGE,
        "openfoamVersion": OPENFOAM_VERSION
    })
```

---

### get_tutorials
- Description: Return a list of available OpenFOAM tutorial cases (category/case).
- Returns: `list` — List of available OpenFOAM tutorial cases.

Notes:
- This uses Docker to query the container's FOAM_TUTORIALS location and finds cases that have `system` and `constant` directories.
- Normalizes paths for Windows by using POSIX relpaths where necessary.

Source (excerpt):
```python
def get_tutorials():
    """
    Return a list of available OpenFOAM tutorial cases (category/case).
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
```

---

### index
- Route: `GET /`
- Description: Render the index page with a list of tutorials.
- Returns: `str` — The rendered HTML page.

Source (excerpt):
```python
@app.route("/")
def index():
    """
    Get the index page.
    """
    tutorials = get_tutorials()
    options_html = "\n".join([f"<option value='{t}'>{t}</option>" for t in tutorials])
    return render_template_string(TEMPLATE, options=options_html, CASE_ROOT=CASE_ROOT)
```

---

### load_config
- Description: Load configuration from `case_config.json` with sensible defaults.
- Returns: `dict` — Configuration dictionary.

Defaults:
- `CASE_ROOT`: `tutorial_cases` (absolute path)
- `DOCKER_IMAGE`: `haldardhruv/ubuntu_noble_openfoam:v12`
- `OPENFOAM_VERSION`: `12`

Source:
```python
def load_config():
    """
    Load configuration from case_config.json with sensible defaults.
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
```

---

### load_tutorial
- Route: `POST /load_tutorial`
- Description: Load a tutorial into the Docker container (copies from FOAM_TUTORIALS into the configured CASE_ROOT).
- Args:
  - `tutorial` (str)
- Returns: `dict` — Output information and `caseDir`.

Important notes:
- Uses Docker to copy the tutorial into the container run directory, then maps that to host `CASE_ROOT`.
- Handles POSIX path normalization on Windows.

Source (excerpt):
```python
@app.route("/load_tutorial", methods=["POST"])
def load_tutorial():
    """
    Load a tutorial in the Docker container.
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
```

---

### monitor_foamrun_log
- Description: Watch for `log.foamRun` in the case directory, capture it to an in-memory dictionary (`foamrun_logs`) and write to `foamrun_logs.txt`.
- Args:
  - `tutorial` (str)
  - `case_dir` (str)

Source:
```python
def monitor_foamrun_log(tutorial, case_dir):
    """
    Watch for log.foamRun, capture it in foamrun_logs and write it to a file.
    """
    import pathlib
    import time

    host_log_path = pathlib.Path(case_dir) / tutorial / "log.foamRun"
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
                logger.info(f"[FOAMFlask] Captured log.foamRun for tutorial '{tutorial}' and wrote to {output_file}")
            except Exception as e:
                logger.error(f"[FOAMFlask] Could not write foamrun_logs to file: {e}")

            return

        time.sleep(interval)
        elapsed += interval

    logger.warning(f"[FOAMFlask] Timeout: log.foamRun not found for '{tutorial}'")
```

---

### run_case
- Route: `POST /run`
- Description: Run a case in Docker and stream container logs to the HTTP response.
- Args:
  - `tutorial` (str)
  - `command` (str)
  - `caseDir` (str)
- Returns: HTTP streaming `text/html` response where each log line is yielded as HTML with `<br>`.

Important details:
- Starts a background watcher thread calling `monitor_foamrun_log`.
- Runs the container and yields logs line-by-line.
- Ensures container is killed/removed in finalization.

Source (excerpt):
```python
@app.route("/run", methods=["POST"])
def run_case():
    """
    Run a case in the Docker container.
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
```

---

### save_config
- Description: Save configuration back to `case_config.json`.
- Args:
  - `updates` (dict)

Source:
```python
def save_config(updates: dict):
    """
    Save configuration back to case_config.json.
    """
    config = load_config()
    config.update(updates)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"[ERROR] Could not save config: {e}")
```

---

### set_case
- Route: `POST /set_case`
- Description: Set the case root directory and persist it to config.
- Args:
  - `caseDir` (str)
- Returns: `dict` — Output and `caseDir`.

Source:
```python
@app.route("/set_case", methods=["POST"])
def set_case():
    """
    Set the case root directory.
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
```

---

### set_docker_config
- Route: `POST /set_docker_config`
- Description: Update Docker image and OpenFOAM version and persist to config.
- Args:
  - `dockerImage` (str)
  - `openfoamVersion` (str)
- Returns: `dict` — Output and current Docker config.

Source:
```python
@app.route("/set_docker_config", methods=["POST"])
def set_docker_config():
    """
    Set the Docker configuration.
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
```

---

### api_available_meshes
- Route: `GET /api/available_meshes`
- Description: Get list of available mesh files in the case directory.
- Args:
  - `tutorial` (str) — The name of the tutorial.
- Returns: `list` — List of available mesh files.

Source (excerpt):
```python
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
```

---

### api_load_mesh
- Route: `POST /api/load_mesh`
- Description: Load a mesh file and return mesh information.
- Args:
  - `file_path` (str) — Path to the mesh file.
  - `for_contour` (bool, optional) — Whether to load for contour visualization.
- Returns: `dict` — Mesh information.

Source (excerpt):
```python
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
    for_contour = data.get("for_contour", False)
```

---

### api_mesh_screenshot
- Route: `POST /api/mesh_screenshot`
- Description: Generate a screenshot of the mesh.
- Args:
  - `file_path` (str) — Path to the mesh file.
  - `width` (int) — Screenshot width.
  - `height` (int) — Screenshot height.
  - `show_edges` (bool) — Whether to show edges.
  - `color` (str) — Mesh color.
  - `camera_position` (str) — Camera position.
- Returns: `dict` — Base64-encoded image.

Source (excerpt):
```python
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
```

---

### api_mesh_interactive
- Route: `POST /api/mesh_interactive`
- Description: Generate an interactive HTML viewer for the mesh.
- Args:
  - `file_path` (str) — Path to the mesh file.
  - `show_edges` (bool) — Whether to show edges.
  - `color` (str) — Mesh color.
- Returns: `HTML` — Interactive mesh viewer page.

Source (excerpt):
```python
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
```

---

### create_contour
- Route: `POST /api/contours/create`
- Description: Create isosurfaces for the current mesh.
- Args:
  - Various parameters for contour generation (from request JSON)
- Returns: `HTML` — Interactive visualization HTML.

Source (excerpt):
```python
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
```

---

### upload_vtk
- Route: `POST /api/upload_vtk`
- Description: Upload VTK files for visualization.
- Args:
  - `file` (file) — VTK file to upload (from request.files).
- Returns: `dict` — JSON response with upload status or error.

Source (excerpt):
```python
@app.route("/api/upload_vtk", methods=["POST"])
def upload_vtk():
    """Upload VTK files for visualization.
    
    Returns:
        JSON response with upload status or error.
    """
    logger.info("[FOAMFlask] [upload_vtk] Received file upload request")
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
```

---

## Notes / Observations

- Many endpoints expect a `tutorial` parameter and rely on a configured `CASE_ROOT`.
- Several operations are performed by running Docker containers and mapping host CASE_ROOT into the container runtime path.
- `run_case` streams logs as HTML lines; the client should be prepared to handle a streaming response.
- `monitor_foamrun_log` writes log content to `foamrun_logs.txt` and an in-memory `foamrun_logs` mapping (not shown here; assumed part of the module's globals).
- Config is persisted to `case_config.json` via `load_config` / `save_config`.

If you want, I can:
- Turn this into a README.md in the repo and open a PR (or prepare the file content for you to commit).
- Extract a smaller cheat-sheet for the API (only routes + required params).
- Generate OpenAPI/Swagger spec from these endpoints.

Which would you like next?
