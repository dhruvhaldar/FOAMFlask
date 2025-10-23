# app — API documentation (converted from docs/app.html)

This file is a GitHub-flavored Markdown conversion of the generated HTML documentation for the `app` module (original HTML: https://github.com/dhruvhaldar/FOAMFlask/blob/8c5a668f6566d675101e94412f7f17a1e47b5b2e/docs/app.html). It summarizes available endpoints, functions, arguments, return types, and includes source snippets where appropriate.

## Table of contents

- [Functions](#functions)
  - [api_available_fields](#api_available_fields)
  - [api_latest_data](#api_latest_data)
  - [api_plot_data](#api_plot_data)
  - [api_residuals](#api_residuals)
  - [get_case_root](#get_case_root)
  - [get_docker_config](#get_docker_config)
  - [get_tutorials](#get_tutorials)
  - [index](#index)
  - [load_config](#load_config)
  - [load_tutorial](#load_tutorial)
  - [monitor_foamrun_log](#monitor_foamrun_log)
  - [run_case](#run_case)
  - [save_config](#save_config)
  - [set_case](#set_case)
  - [set_docker_config](#set_docker_config)

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
- Description: Watch for `log.FoamRun` in the case directory, capture it to an in-memory dictionary (`foamrun_logs`) and write to `foamrun_logs.txt`.
- Args:
  - `tutorial` (str)
  - `case_dir` (str)

Source:
```python
def monitor_foamrun_log(tutorial, case_dir):
    """
    Watch for log.FoamRun, capture it in foamrun_logs and write it to a file.
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