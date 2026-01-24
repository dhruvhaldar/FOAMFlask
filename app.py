# Standard library imports
import json
import logging
import os
import shutil
import threading
import time
import platform
import posixpath
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Generator, Any
from functools import wraps, lru_cache
import email.utils
import secrets

# Third-party imports
import docker
import orjson
from docker import DockerClient
from docker.errors import DockerException
from flask import Flask, Response, render_template_string, request, send_from_directory
from markupsafe import escape
from werkzeug.utils import secure_filename
from flask_compress import Compress

# Local application imports
from backend.mesh.mesher import mesh_visualizer
from backend.plots.realtime_plots import OpenFOAMFieldParser, get_available_fields
from backend.post.isosurface import IsosurfaceVisualizer, isosurface_visualizer
from backend.post.slice import SliceVisualizer
from backend.post.streamline import StreamlineVisualizer
from backend.post.surface_projection import SurfaceProjectionVisualizer
from backend.startup import run_initial_setup_checks, check_docker_permissions
from backend.case.manager import CaseManager
from backend.geometry.manager import GeometryManager
from backend.geometry.visualizer import GeometryVisualizer
from backend.meshing.runner import MeshingRunner
from backend.utils import sanitize_error, is_safe_command

# Initialize Flask application
app = Flask(__name__)

# Configure Compression
app.config["COMPRESS_MIMETYPES"] = [
    "text/html",
    "text/css",
    "text/xml",
    "application/json",
    "application/javascript",
]
app.config["COMPRESS_LEVEL"] = 6
app.config["COMPRESS_MIN_SIZE"] = 500
compress = Compress(app)

# Security: Set maximum upload size to 500MB to prevent DoS
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("FOAMFlask")



def fast_jsonify(data: Any, status: int = 200) -> Response:
    """
    Drop-in replacement for flask.jsonify using orjson for high performance.

    Args:
        data: Data to serialize (dict, list, etc.)
        status: HTTP status code

    Returns:
        Flask Response object with application/json mimetype
    """
    # orjson.dumps returns bytes
    # OPT_SERIALIZE_NUMPY: Handles numpy arrays automatically
    # OPT_NAIVE_UTC: Assumes naive datetime is UTC
    json_bytes = orjson.dumps(
        data,
        option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NAIVE_UTC
    )
    return Response(json_bytes, status=status, mimetype='application/json')




def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.

    Args:
        relative_path: Relative path to the resource (e.g. "static/html/template.html")

    Returns:
        Resolved absolute Path object
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS) # type: ignore
    except AttributeError:
        base_path = Path(app.root_path)

    return (base_path / relative_path).resolve()

# Global configuration
CONFIG_FILE = Path("case_config.json")
CONFIG: Optional[Dict] = None
CASE_ROOT: Optional[str] = None
DOCKER_IMAGE: Optional[str] = None
OPENFOAM_VERSION: Optional[str] = None
docker_client: Optional[DockerClient] = None
# foamrun_logs global removed to prevent memory leaks
STARTUP_STATUS = {"status": "starting", "message": "Initializing..."}

# --- Rate Limiting Logic ---
# IP -> list of timestamps
_request_history: Dict[str, List[float]] = {}
_last_cleanup_time = 0.0

def _cleanup_rate_limit_history(window: int = 60):
    """
    Clean up old entries from the rate limit history to prevent memory leaks.
    """
    global _last_cleanup_time
    now = time.time()

    # Only cleanup every 'window' seconds
    if now - _last_cleanup_time < window:
        return

    _last_cleanup_time = now
    ips_to_remove = []

    for ip, history in _request_history.items():
        # Keep only timestamps within the window
        valid_timestamps = [t for t in history if now - t < window]
        if not valid_timestamps:
            ips_to_remove.append(ip)
        else:
            _request_history[ip] = valid_timestamps

    for ip in ips_to_remove:
        del _request_history[ip]

def rate_limit(limit: int = 5, window: int = 60):
    """
    Decorator to rate limit endpoints.

    Args:
        limit: Max requests allowed in the window.
        window: Time window in seconds.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Allow rate limiting to be disabled for testing if needed
            if app.config.get("TESTING") and not app.config.get("ENABLE_RATE_LIMIT", True):
                return f(*args, **kwargs)

            # Get IP address (simple remote_addr, trusted in this context)
            ip = request.remote_addr or "unknown"

            # Allow internal testing calls if needed, or handle unknown IPs
            if ip == "unknown":
                pass

            now = time.time()

            # Opportunistic cleanup
            _cleanup_rate_limit_history(window)

            # Clean up old history for this IP
            history = _request_history.get(ip, [])
            # Filter out timestamps older than the window
            history = [t for t in history if now - t < window]

            if len(history) >= limit:
                logger.warning(f"Security: Rate limit exceeded for {ip} on {request.endpoint}")
                return fast_jsonify({
                    "error": "Too many requests. Please try again later.",
                    "retry_after": int(window - (now - history[0])) if history else window
                }), 429

            history.append(now)
            _request_history[ip] = history

            return f(*args, **kwargs)
        return wrapped
    return decorator


# Security validation functions
def is_safe_tutorial_path(path: str) -> bool:
    """
    Validate tutorial path to prevent command injection.

    Args:
        path: Tutorial path string

    Returns:
        True if path is safe, False otherwise
    """
    if not path or not isinstance(path, str):
        return False
    # Only allow alphanumeric, underscore, hyphen, dot, and slash
    if not re.match(r'^[a-zA-Z0-9_./-]+$', path):
        return False
    if '..' in path:
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


@lru_cache(maxsize=32)
def _resolve_path_cached(path_str: str) -> Path:
    """
    Cache the resolution of base directories to reduce syscalls.
    Only used for the base directory which changes infrequently.
    """
    return Path(path_str).resolve()


def is_safe_case_root(path_str: str) -> bool:
    """
    Check if the path is safe to use as a case root.
    Blocks system directories on Linux and Windows.

    Args:
        path_str: The resolved absolute path string.

    Returns:
        True if safe, False if system directory.
    """
    # Normalize path separators
    normalized = os.path.normpath(path_str)

    system = platform.system()

    if system == "Windows":
        # Windows system directories
        # Normalize to lower case for case-insensitive comparison
        norm_lower = normalized.lower()

        # Check for drive root (e.g. C:\)
        # Regex: ^[a-z]:\\?$ or ^[a-z]:$
        if re.match(r'^[a-z]:\\?$', norm_lower):
            return False

        forbidden_prefixes = [
            "c:\\windows",
            "c:\\program files",
            "c:\\program files (x86)",
            "c:\\users\\public",
            "c:\\inetpub",
        ]

        # Check specific prefixes
        for p in forbidden_prefixes:
            if norm_lower == p or norm_lower.startswith(p + "\\"):
                return False

    else:
        # Linux/Unix system directories
        forbidden_prefixes = [
            "/bin", "/boot", "/dev", "/etc", "/lib", "/lib64",
            "/proc", "/root", "/run", "/sbin", "/sys", "/usr", "/var"
        ]

        if normalized == "/":
            return False

        for p in forbidden_prefixes:
            if normalized == p or normalized.startswith(p + os.sep):
                return False

    return True


def validate_safe_path(base_dir: str, relative_path: str) -> Path:
    """
    Validate and resolve a path to ensure it remains within the base directory.

    Args:
        base_dir: The authorized base directory (e.g. CASE_ROOT)
        relative_path: The user-provided path component

    Returns:
        The resolved Path object

    Raises:
        ValueError: If path traversal is detected or path is invalid
    """
    if not relative_path:
        raise ValueError("No path specified")

    # ⚡ Bolt Optimization: Use cached resolution for base_dir
    # resolving the base path every time adds significant overhead (syscalls)
    base = _resolve_path_cached(base_dir)

    # ⚡ Bolt Optimization: Use os.path.join + realpath instead of Path / operator + resolve()
    # This avoids intermediate Path creation and is ~2.3x faster (2.18s vs 5.15s for 100k iters).
    # We still need to return a Path object, but we construct it once at the end.
    try:
        # Note: os.path.realpath resolves symlinks, similar to Path.resolve()
        # We convert base to string once (it's a Path from cache)
        target_str = os.path.realpath(os.path.join(str(base), relative_path))
        target = Path(target_str)
    except OSError:
        # Fallback for rare OS errors
        target = (base / relative_path).resolve()

    # Check if the resolved target starts with the resolved base path
    if not target.is_relative_to(base):
        logger.warning(f"Security: Path traversal attempt blocked. Path: {target}, Base: {base}")
        raise ValueError("Access denied: Invalid path")

    return target


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
    return fast_jsonify({"output": error_msg}), 503


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
TEMPLATE_FILE = get_resource_path("static/html/foamflask_frontend.html")
try:
    with TEMPLATE_FILE.open("r", encoding="utf-8") as f:
        TEMPLATE = f.read()
except (OSError, UnicodeDecodeError) as e:
    logger.error(
        "[FOAMFlask] Failed to load template file %s: %s", TEMPLATE_FILE, str(e)
    )
    TEMPLATE = "<html><body>Error loading template</body></html>"

# ⚡ Bolt Optimization: Pre-compile template to avoid recompiling on every request.
# This reduces rendering time from ~134ms to ~0.9ms for the 98KB template.
COMPILED_TEMPLATE = None


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

        # ⚡ Bolt Optimization: Combine fetching FOAM_TUTORIALS and running find into a single container execution.
        # This saves ~500ms-1s of overhead by avoiding a second container startup/shutdown cycle.
        # We output the root path first, then the list of cases.
        cmd = (
            f"source {bashrc} && "
            "echo $FOAM_TUTORIALS && "
            "find $FOAM_TUTORIALS -mindepth 2 -maxdepth 2 -type d "
            "-exec test -d {}/system -a -d {}/constant \\; -print"
        )

        result = client.containers.run(
            DOCKER_IMAGE,
            f"bash -c '{cmd}'",
            remove=True,
            stdout=True,
            stderr=True,
            tty=True,
        )

        output = result.decode().strip()
        if not output:
            logger.warning("[FOAMFlask] No tutorial root found in OpenFOAM")
            return []

        lines = output.splitlines()
        tutorial_root = lines[0].strip()
        cases = lines[1:]

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


def monitor_foamrun_log(tutorial: str, case_dir: str) -> None:
    """Watch for log.foamRun and write to a file safely.

    SECURITY FIX: This function previously read the entire file into memory and
    stored it in a global dictionary, causing a memory leak and potential DoS
    on large files. It has been refactored to copy the file efficiently
    without memory unbounded growth.

    Args:
        tutorial: The name of the tutorial.
        case_dir: The path to the case directory.
    """
    host_log_path = Path(case_dir) / tutorial / "log.foamRun"
    output_file = Path(case_dir) / tutorial / "foamrun_logs.txt"

    # Configuration
    timeout = 300  # seconds max wait
    interval = 1  # check every 1 second
    elapsed = 0

    while elapsed < timeout:
        # Security: Atomic check-and-open to prevent TOCTOU symlink attacks
        try:
            # O_NOFOLLOW ensures that if the last component is a symlink, open fails with ELOOP.
            # This is safer than checking is_symlink() then opening.
            import errno
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            
            fd = os.open(str(host_log_path), flags)

            with os.fdopen(fd, "rb") as fsrc:
                with open(output_file, "wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst)

            logger.info(
                "[FOAMFlask] Captured log.foamRun for tutorial '%s' "
                "and wrote to %s",
                tutorial,
                output_file,
            )
            return

        except OSError as e:
            # Check specifically for symlink error (ELOOP)
            if e.errno == errno.ELOOP:
                logger.warning(
                    "[FOAMFlask] Security: log.foamRun is a symlink. Ignoring to prevent file read vulnerability."
                )
                return
            elif e.errno == errno.ENOENT:
                # File not found yet, wait and retry
                pass
            else:
                logger.error("[FOAMFlask] Could not process foamrun_logs: %s", str(e))
                return

        time.sleep(interval)
        elapsed += interval

    logger.warning("[FOAMFlask] Timeout: log.foamRun not found for '%s'", tutorial)


# --- Routes ---
@app.before_request
def csrf_protect():
    """Check CSRF token on state-changing requests."""
    if request.method not in ["GET", "HEAD", "OPTIONS", "TRACE"]:
        if app.config.get("TESTING") and not app.config.get("ENABLE_CSRF", True):
            return
        token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRFToken")
        if not token or not header_token or not secrets.compare_digest(token, header_token):
            return fast_jsonify({"error": "CSRF token missing or invalid"}), 403

@app.after_request
def set_security_headers(response: Response) -> Response:
    """
    Set security headers and CSRF cookie for all responses.
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy
    # Disable sensitive features not used by the app
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=(), usb=()"

    # Content Security Policy (CSP)
    # Allows external CDNs used by the frontend (Tailwind, Plotly, Google Fonts)
    # 'unsafe-inline' and 'unsafe-eval' are required for Plotly and inline scripts/styles
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.tailwindcss.com https://cdn.plot.ly https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: http://127.0.0.1:*; "
        "frame-src 'self' http://127.0.0.1:* ws://127.0.0.1:*;"
    )
    response.headers["Content-Security-Policy"] = csp_policy

    # Set CSRF cookie if not present
    if not request.cookies.get("csrf_token"):
        # Lax allows top-level navigation, Strict is better but might break if linked from elsewhere
        # Since this is a local app, Lax is fine.
        response.set_cookie("csrf_token", secrets.token_hex(32), samesite="Lax", secure=False)

    return response


@app.route("/")
@app.route("/setup")
@app.route("/geometry")
@app.route("/meshing")
@app.route("/visualizer")
@app.route("/run")
@app.route("/plots")
@app.route("/post")
def index() -> str:
    """Render the index page with available tutorials.

    Returns:
        Rendered HTML template with tutorials and case root.
    """
    global COMPILED_TEMPLATE

    # Lazy initialization of compiled template
    if COMPILED_TEMPLATE is None:
        COMPILED_TEMPLATE = app.jinja_env.from_string(TEMPLATE)

    tutorials = get_tutorials()
    # Use escape to prevent XSS in option values
    options_html = "\n".join(f'<option value="{escape(t)}">{escape(t)}</option>' for t in tutorials)

    # ⚡ Bolt Optimization: Use pre-compiled template rendering
    # We must manually update the context with Flask globals (url_for, request, etc.)
    context = {"options": options_html, "CASE_ROOT": CASE_ROOT}
    app.update_template_context(context)
    return COMPILED_TEMPLATE.render(context)


@app.route("/api/startup_status", methods=["GET"])
def get_startup_status() -> Response:
    """
    Get the status of the startup checks.

    Returns:
        JSON response with status and message.
    """
    return fast_jsonify(STARTUP_STATUS)


@app.route('/favicon.ico')
def favicon():
    static_dir = get_resource_path("static")
    return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/get_case_root", methods=["GET"])
def get_case_root() -> Response:
    """Get the case root directory.

    Returns:
        JSON response containing the case root directory.
    """
    return fast_jsonify({"caseDir": CASE_ROOT})


@app.route("/set_case", methods=["POST"])
def set_case() -> Union[Response, Tuple[Response, int]]:
    """Set the case root directory.

    Returns:
        JSON response with status and case directory information.
    """
    global CASE_ROOT

    data = request.get_json()
    if not data or "caseDir" not in data or not data["caseDir"]:
        return fast_jsonify({"output": "[FOAMFlask] [Error] No caseDir provided"}), 400

    try:
        case_dir_path = Path(data["caseDir"]).resolve()

        # Security: Prevent setting CASE_ROOT to system directories
        resolved_str = str(case_dir_path)

        if not is_safe_case_root(resolved_str):
            logger.warning(f"Security: Attempt to set case root to system directory blocked: {resolved_str}")
            return fast_jsonify({"output": "[FOAMFlask] [Error] Cannot set case root to system directory"}), 400

        case_dir_path.mkdir(parents=True, exist_ok=True)
        CASE_ROOT = str(case_dir_path)
        save_config({"CASE_ROOT": CASE_ROOT})

        return fast_jsonify(
            {
                "output": f"INFO::[FOAMFlask] Case root set to: {CASE_ROOT}",
                "caseDir": CASE_ROOT,
            }
        )
    except Exception as e:
        logger.error("Error setting case directory: %s", str(e))
        return fast_jsonify({"output": f"[FOAMFlask] [Error] {sanitize_error(e)}"}), 400


@app.route("/open_case_root", methods=["POST"])
def open_case_root() -> Response:
    """Open the current case root in the system file explorer."""
    if not CASE_ROOT:
        return fast_jsonify({"output": "Case root is not set"}), 400

    try:
        path = os.path.abspath(CASE_ROOT)
        if not os.path.exists(path):
            return fast_jsonify({"output": f"Directory not found: {path}"}), 404

        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            import subprocess
            subprocess.run(["open", path], check=True)
        else:  # Linux and others
            import subprocess
            subprocess.run(["xdg-open", path], check=True)
            
        return fast_jsonify({"output": f"Opened {path} in file explorer"})
        
    except Exception as e:
        logger.error(f"Failed to open file explorer: {e}")
        return fast_jsonify({"output": f"Error opening file explorer: {str(e)}"}), 500


@app.route("/api/cases/list", methods=["GET"])
def api_list_cases() -> Response:
    """List available cases in the CASE_ROOT."""
    if not CASE_ROOT:
         return fast_jsonify({"cases": []})

    root = Path(CASE_ROOT)
    if not root.exists():
         return fast_jsonify({"cases": []})

    # List subdirectories that look like cases (or just all dirs)
    # ⚡ Bolt Optimization: Use os.scandir instead of Path.iterdir()
    # This avoids creating Path objects for every entry and can save sys calls on some OSes
    cases = []
    try:
        with os.scandir(str(root)) as entries:
            for entry in entries:
                if entry.is_dir():
                    cases.append(entry.name)
    except OSError as e:
        logger.error(f"Error listing cases in {root}: {e}")
        return fast_jsonify({"cases": []})

    return fast_jsonify({"cases": sorted(cases)})

@app.route("/api/case/create", methods=["POST"])
@rate_limit(limit=5, window=60)
def api_create_case() -> Union[Response, Tuple[Response, int]]:
    """
    Create a new OpenFOAM case with minimal structure.

    Returns:
        JSON response with status and path.
    """
    data = request.get_json()
    case_name = data.get("caseName")

    if not case_name:
        return fast_jsonify({"success": False, "message": "No case name provided"}), 400

    try:
        # Use globally set CASE_ROOT
        if not CASE_ROOT:
             return fast_jsonify({"success": False, "message": "Case root not set"}), 500

        try:
            # Security: Validate path is within CASE_ROOT
            # validate_safe_path resolves the path, checking for traversal
            full_path = validate_safe_path(CASE_ROOT, case_name)
        except ValueError as e:
            return fast_jsonify({"success": False, "message": str(e)}), 400

        result = CaseManager.create_case_structure(full_path)

        if result["success"]:
            return fast_jsonify(result)
        else:
            return fast_jsonify(result), 500

    except Exception as e:
        logger.error(f"Error in api_create_case: {e}")
        return fast_jsonify({"success": False, "message": sanitize_error(e)}), 500


# --- Geometry Routes ---

@app.route("/api/geometry/upload", methods=["POST"])
@rate_limit(limit=10, window=60)
def api_upload_geometry() -> Union[Response, Tuple[Response, int]]:
    """Upload an STL file to the current case."""
    if "file" not in request.files:
        return fast_jsonify({"success": False, "message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return fast_jsonify({"success": False, "message": "No selected file"}), 400

    # Get the current case path from request or global state
    # Ideally, the frontend should send the current case directory or name
    # But we also have global CASE_ROOT.
    # Let's rely on the frontend sending 'caseDir' or using the set case.

    # Check if 'caseDir' is in form data?
    case_dir_raw = request.form.get("caseDir")
    case_name = request.form.get("caseName")

    # Security: Always validate the target path
    # If caseDir is provided, it might be an absolute path or relative path
    # We must ensure it resolves to something inside CASE_ROOT
    try:
        if case_dir_raw:
            # If caseDir is provided, we treat it as potentially relative to CASE_ROOT
            # or if it's absolute, validate_safe_path will check if it's inside CASE_ROOT
            # But validate_safe_path takes (base, relative).
            # If relative is absolute, Path(base) / relative might behave differently depending on OS,
            # but usually Path("/a") / "/b" -> "/b".
            # validate_safe_path implementation:
            # base = Path(base_dir).resolve()
            # target = (base / relative_path).resolve()
            # if not target.is_relative_to(base): raise...

            # If case_dir_raw is absolute "/etc/passwd", target becomes "/etc/passwd".
            # is_relative_to(CASE_ROOT) will fail. Safe.

            case_dir_path = validate_safe_path(CASE_ROOT, case_dir_raw)
            case_dir = str(case_dir_path)

        elif case_name:
            # If only caseName provided
            case_dir_path = validate_safe_path(CASE_ROOT, case_name)
            case_dir = str(case_dir_path)
        else:
             return fast_jsonify({"success": False, "message": "No case name or directory specified"}), 400

    except ValueError as e:
        logger.warning(f"Security: Blocked upload attempt: {e}")
        return fast_jsonify({"success": False, "message": str(e)}), 400

    result = GeometryManager.upload_stl(case_dir, file, file.filename)
    if result["success"]:
        return fast_jsonify(result)
    else:
        return fast_jsonify(result), 500

@app.route("/api/geometry/list", methods=["GET"])
def api_list_geometry() -> Union[Response, Tuple[Response, int]]:
    """List STL files in the current case."""
    case_name = request.args.get("caseName")
    if not case_name:
         return fast_jsonify({"success": False, "message": "No case name specified"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        case_dir_path = validate_safe_path(CASE_ROOT, case_name)
        case_dir = str(case_dir_path)
    except ValueError as e:
        return fast_jsonify({"success": False, "message": str(e)}), 400

    result = GeometryManager.list_stls(case_dir)

    if result["success"]:
        return fast_jsonify(result)
    else:
        return fast_jsonify(result), 500

@app.route("/api/geometry/delete", methods=["POST"])
def api_delete_geometry() -> Union[Response, Tuple[Response, int]]:
    """Delete an STL file."""
    data = request.get_json()
    case_name = data.get("caseName")
    filename = data.get("filename")

    if not case_name or not filename:
        return fast_jsonify({"success": False, "message": "Missing parameters"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        case_dir_path = validate_safe_path(CASE_ROOT, case_name)
        case_dir = str(case_dir_path)
    except ValueError as e:
        return fast_jsonify({"success": False, "message": str(e)}), 400

    result = GeometryManager.delete_stl(case_dir, filename)

    if result["success"]:
        return fast_jsonify(result)
    else:
        return fast_jsonify(result), 500

def validate_geometry_path(case_name: str, filename: str) -> Union[Path, Tuple[Response, int]]:
    """
    Validate and resolve geometry file path with security checks.

    Returns:
        Resolved Path object or error response tuple.
    """
    if not case_name or not filename:
        return fast_jsonify({"success": False, "message": "Missing parameters"}), 400

    # Sanitize inputs
    case_name = secure_filename(case_name)
    filename = secure_filename(filename)

    file_path = Path(CASE_ROOT) / case_name / "constant" / "triSurface" / filename
    
    # Security: Ensure resolved path is within valid directories
    resolved_path = file_path.resolve()
    base_path = Path(CASE_ROOT).resolve()
    
    if not resolved_path.is_relative_to(base_path):
        logger.warning(f"Security: Path traversal attempt blocked. Path: {resolved_path}, Base: {base_path}")
        return fast_jsonify({"success": False, "message": "Access denied"}), 400
    
    return resolved_path

@app.route("/api/geometry/view", methods=["POST"])
def api_view_geometry() -> Union[Response, Tuple[Response, int]]:
    """Get interactive HTML viewer for an STL."""
    data = request.get_json()
    case_name = data.get("caseName")
    filename = data.get("filename")
    color = data.get("color", "lightblue")
    opacity = data.get("opacity", 1.0)
    optimize = data.get("optimize", False)

    path_or_error = validate_geometry_path(case_name, filename)
    if isinstance(path_or_error, tuple):
        return path_or_error
    
    resolved_path = path_or_error

    html_content = GeometryVisualizer.get_interactive_html(resolved_path, color, opacity, optimize)

    if html_content:
        response = Response(html_content, mimetype="text/html")
        # Optimization: Exclude visual graphics from compression
        response.headers["Content-Encoding"] = "identity"
        return response
    else:
        return fast_jsonify({"success": False, "message": "Failed to generate view"}), 500

@app.route("/api/geometry/info", methods=["POST"])
def api_info_geometry() -> Union[Response, Tuple[Response, int]]:
    """Get info (bounds, etc) for an STL."""
    data = request.get_json()
    case_name = data.get("caseName")
    filename = data.get("filename")

    path_or_error = validate_geometry_path(case_name, filename)
    if isinstance(path_or_error, tuple):
        return path_or_error
    
    resolved_path = path_or_error

    info = GeometryVisualizer.get_mesh_info(resolved_path)
    return fast_jsonify(info)


# --- Meshing Routes ---

@app.route("/api/meshing/blockMesh/config", methods=["POST"])
def api_meshing_blockmesh_config() -> Union[Response, Tuple[Response, int]]:
    """Generate blockMeshDict."""
    data = request.get_json()
    case_name = data.get("caseName")
    config = data.get("config", {})

    if not case_name:
         return fast_jsonify({"success": False, "message": "No case name specified"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        case_path = validate_safe_path(CASE_ROOT, case_name)
    except ValueError as e:
        return fast_jsonify({"success": False, "message": str(e)}), 400

    result = MeshingRunner.configure_blockmesh(case_path, config)

    if result["success"]:
        return fast_jsonify(result)
    else:
        return fast_jsonify(result), 500

@app.route("/api/meshing/snappyHexMesh/config", methods=["POST"])
def api_meshing_snappyhexmesh_config() -> Union[Response, Tuple[Response, int]]:
    """Generate snappyHexMeshDict."""
    data = request.get_json()
    case_name = data.get("caseName")
    config = data.get("config", {})

    if not case_name:
         return fast_jsonify({"success": False, "message": "No case name specified"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        case_path = validate_safe_path(CASE_ROOT, case_name)
    except ValueError as e:
        return fast_jsonify({"success": False, "message": str(e)}), 400

    result = MeshingRunner.configure_snappyhexmesh(case_path, config)

    if result["success"]:
        return fast_jsonify(result)
    else:
        return fast_jsonify(result), 500

@app.route("/api/meshing/run", methods=["POST"])
@rate_limit(limit=10, window=60)
def api_meshing_run() -> Union[Response, Tuple[Response, int]]:
    """Run a meshing command."""
    data = request.get_json()
    case_name = data.get("caseName")
    command = data.get("command") # "blockMesh" or "snappyHexMesh"

    if not case_name or not command:
         return fast_jsonify({"success": False, "message": "Missing parameters"}), 400

    if command not in ["blockMesh", "snappyHexMesh"]:
        return fast_jsonify({"success": False, "message": "Invalid command"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        case_path = validate_safe_path(CASE_ROOT, case_name)
    except ValueError as e:
        return fast_jsonify({"success": False, "message": str(e)}), 400

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
        return fast_jsonify(result)
    else:
        return fast_jsonify(result), 500


@app.route("/get_docker_config", methods=["GET"])
def get_docker_config() -> Response:
    """Get the Docker configuration.

    Returns:
        JSON response containing Docker image and OpenFOAM version.
    """
    return fast_jsonify({"dockerImage": DOCKER_IMAGE, "openfoamVersion": OPENFOAM_VERSION})


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
            fast_jsonify({"output": "[FOAMFlask] [Error] No configuration data provided"}),
            400,
        )

    updates = {}
    if "dockerImage" in data and data["dockerImage"]:
        # Security: Validate docker image string
        # Allow alphanumeric, underscore, hyphen, dot, slash, colon
        image_str = str(data["dockerImage"])
        if not re.match(r'^[a-zA-Z0-9_./:-]+$', image_str):
            return fast_jsonify({"output": "[FOAMFlask] [Error] Invalid Docker image string"}), 400

        DOCKER_IMAGE = image_str
        updates["DOCKER_IMAGE"] = DOCKER_IMAGE

    if "openfoamVersion" in data and data["openfoamVersion"]:
        # Security: Validate version string to prevent command injection
        # Allow alphanumeric, dot, hyphen
        version_str = str(data["openfoamVersion"])
        if not re.match(r'^[a-zA-Z0-9.-]+$', version_str):
             return fast_jsonify({"output": "[FOAMFlask] [Error] Invalid OpenFOAM version string"}), 400

        OPENFOAM_VERSION = version_str
        updates["OPENFOAM_VERSION"] = OPENFOAM_VERSION

    if updates:
        save_config(updates)

    return fast_jsonify(
        {
            "output": "INFO::[FOAMFlask] Docker config updated",
            "dockerImage": DOCKER_IMAGE,
            "openfoamVersion": OPENFOAM_VERSION,
        }
    )


@app.route("/load_tutorial", methods=["POST"])
@rate_limit(limit=5, window=60)
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
        return fast_jsonify({"output": "[FOAMFlask] [Error] No tutorial selected"})

    # SECURITY FIX: Validate tutorial path to prevent command injection
    if not is_safe_tutorial_path(tutorial):
        logger.warning(f"Security: Invalid tutorial path rejected: {tutorial}")
        return fast_jsonify({"output": "[FOAMFlask] [Error] Invalid tutorial path detected"}), 400

    client = get_docker_client()
    if client is None:
        return docker_unavailable_response()

    bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
    container_run_path = "/tmp/FOAM_Run" # nosec B108
    
    # Flatten structure: use only the leaf name of the tutorial for the local case directory
    tutorial_name = posixpath.basename(tutorial)
    container_case_path = posixpath.join(container_run_path, tutorial_name)

    # Convert Windows paths to POSIX style for Docker
    host_path = Path(CASE_ROOT).resolve()
    is_windows = platform.system() == "Windows"
    # Docker expects POSIX paths for bind mounts on Windows (e.g. /c/Users/...)
    # We use as_posix() to ensure forward slashes.
    host_path_str = host_path.as_posix() if is_windows else str(host_path)

    # Base docker command: create directory and copy tutorial
    # Security: Use list format for command to prevent shell injection
    shell_cmd = (
        "source \"$1\" && "
        "mkdir -p \"$2\" && "
        "cp -r $FOAM_TUTORIALS/\"$3\"/* \"$2\""
    )

    # On Linux/macOS, add chmod; on Windows skip it
    if not is_windows:
        shell_cmd += " && chmod +x \"$2\"/Allrun"

    docker_cmd = [
        "bash", "-c",
        shell_cmd,
        "load_tutorial",  # $0
        bashrc,           # $1
        container_case_path, # $2
        tutorial          # $3
    ]

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

        return fast_jsonify({"output": output, "caseDir": CASE_ROOT})

    except Exception as e:
        logger.error(f"Error loading tutorial: {e}", exc_info=True)
        return fast_jsonify({"output": f"[FOAMFlask] [Error] {sanitize_error(e)}"}), 500

    finally:
        if container:
            try:
                container.reload()
                if container.status == "running":
                    container.kill()
            except Exception as e:
                logger.debug(f"[FOAMFlask] Error killing container: {e}")
            try:
                container.remove()
            except Exception as e:
                logger.debug(f"[FOAMFlask] Error removing container: {e}")


@app.route("/run", methods=["POST"])
@rate_limit(limit=5, window=60)
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

    # Security: Validate tutorial path
    if not is_safe_tutorial_path(tutorial):
        return {"error": "Invalid tutorial path"}, 400

    # Security: Validate path is within CASE_ROOT
    try:
        # We don't use the return value here as the generator re-resolves it,
        # but this ensures the path is valid before starting the stream.
        validate_safe_path(CASE_ROOT, case_dir)
    except ValueError as e:
        logger.warning(f"Security violation in run_case: {e}")
        return {"error": str(e)}, 400

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

        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"

        # Convert Windows path to POSIX for Docker volumes
        host_path = Path(case_dir).resolve()
        host_path_str = host_path.as_posix() if platform.system() == "Windows" else str(host_path)

        # DEBUG: Check if we are pointing to the case itself or its parent
        tutorial_name = Path(tutorial).name
        # If case_dir ends with the tutorial name, we assume it IS the case directory
        is_direct_case_path = host_path.name == tutorial_name

        logger.info(f"[FOAMFlask] run_case: tutorial='{tutorial}', case_dir='{case_dir}'")
        logger.info(f"[FOAMFlask] run_case: is_direct_case_path={is_direct_case_path}")

        if is_direct_case_path:
             # Mount the case directory directly to /tmp/FOAM_Run
             # So inside container: /tmp/FOAM_Run contains the case files (0, constant, system) directly
             container_bind_path = "/tmp/FOAM_Run"
             container_case_path = "/tmp/FOAM_Run" # Working dir is the mount point
        else:
             # Mount the parent directory (presumably) so tutorial structure is preserved
             # e.g. /tmp/FOAM_Run/tutorial/case
             container_bind_path = "/tmp/FOAM_Run"
             container_case_path = posixpath.join("/tmp/FOAM_Run", tutorial_name) # nosec B108

        logger.info(f"[FOAMFlask] run_case: container_case_path='{container_case_path}'")

        volumes = {
            host_path_str: {
                "bind": container_bind_path, # nosec B108
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
            yield f"[FOAMFlask] [Error] Unsafe command detected: {escape(command)}<br>"
            yield "[FOAMFlask] [Error] Commands containing shell metacharacters are not allowed.<br>"
            return

        # Determine if command is an OpenFOAM command or a script file
        openfoam_commands = ["blockMesh", "simpleFoam", "pimpleFoam", "decomposePar", "reconstructPar", "foamToVTK", "paraFoam"]
        
        if command.startswith("./") or command in openfoam_commands:
            if command.startswith("./"):
                # Script file - validate path and execute safely
                script_name = command[2:]  # Remove "./" prefix
                if not is_safe_script_name(script_name):
                    yield f"[FOAMFlask] [Error] Unsafe script name: {escape(script_name)}<br>"
                    yield "[FOAMFlask] [Error] Script names must be alphanumeric with underscores/hyphens only.<br>"
                    return
                
                # Security: Use positional arguments for bash -c to prevent injection
                docker_cmd = [
                    "bash", "-c",
                    "source \"$1\" && cd \"$2\" && chmod +x \"$3\" && ./\"$3\"",
                    "run_script",        # $0
                    bashrc,              # $1
                    container_case_path, # $2
                    script_name          # $3
                ]
            else:
                # OpenFOAM command - Security: Use positional arguments
                docker_cmd = [
                    "bash", "-c",
                    "source \"$1\" && cd \"$2\" && $3",
                    "run_foam_cmd",      # $0
                    bashrc,              # $1
                    container_case_path, # $2
                    command              # $3
                ]
        else:
            # Fallback - treat as script with validation
            if not is_safe_script_name(command):
                yield f"[FOAMFlask] [Error] Unsafe command name: {escape(command)}<br>"
                yield "[FOAMFlask] [Error] Command names must be alphanumeric with underscores/hyphens only.<br>"
                return
            
            # Security: Use positional arguments
            docker_cmd = [
                "bash", "-c",
                "source \"$1\" && cd \"$2\" && chmod +x \"$3\" && ./\"$3\"",
                "run_script_fallback", # $0
                bashrc,                # $1
                container_case_path,   # $2
                command                # $3
            ]

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
                        yield f"{escape(subline)}<br>"
            except Exception as e:
                yield f"[FOAMFlask] [Error] Failed to stream container logs: {escape(str(e))}<br>"

        except Exception as e:
            logger.error(f"Error running container: {e}", exc_info=True)
            yield f"[FOAMFlask] [Error] Failed to start container: {escape(sanitize_error(e))}<br>"
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
        return fast_jsonify({"error": "No tutorial specified"}), 400

    try:
        tutorial_name = posixpath.basename(tutorial)
        case_dir = validate_safe_path(CASE_ROOT, tutorial_name)
    except ValueError as e:
        return fast_jsonify({"error": str(e)}), 400

    if not case_dir.exists():
        return fast_jsonify({"error": "Case directory not found"}), 404

    try:
        fields = get_available_fields(str(case_dir))
        return fast_jsonify({"fields": fields})
    except Exception as e:
        logger.error(f"Error in available_fields: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


def check_cache(path_to_check: Path) -> Tuple[bool, Optional[str], Optional[os.stat_result]]:
    """
    Check if the resource at path_to_check has been modified since the
    time specified in the If-Modified-Since header.

    Args:
        path_to_check: Path to the file or directory to check.

    Returns:
        Tuple[bool, str, os.stat_result]: (is_not_modified, last_modified_http_date, stat_result)
        is_not_modified: True if client cache is valid (return 304), False otherwise.
        last_modified_http_date: The HTTP-formatted Last-Modified date string.
        stat_result: The os.stat result object (or None if error), allowing callers to reuse it.
    """
    try:
        # ⚡ Bolt Optimization: Use os.stat() to reduce system calls (exists+is_file+stat -> single stat)
        # This reduces syscall overhead by ~2.4x, critical for high-frequency polling endpoints.
        st = os.stat(str(path_to_check))
        mtime = st.st_mtime

        last_modified_str = email.utils.formatdate(mtime, usegmt=True)
        if_modified_since = request.headers.get("If-Modified-Since")

        if if_modified_since and if_modified_since == last_modified_str:
            return True, last_modified_str, st

        return False, last_modified_str, st
    except OSError:
        # File not found or permission error
        return False, None, None


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
        return fast_jsonify({"error": "No tutorial specified"}), 400

    try:
        tutorial_name = posixpath.basename(tutorial)
        case_dir = validate_safe_path(CASE_ROOT, tutorial_name)
    except ValueError as e:
        return fast_jsonify({"error": str(e)}), 400

    if not case_dir.exists():
        return fast_jsonify({"error": "Case directory not found"}), 404

    try:
        # Optimization: Check if data has changed (proxy: postProcessing directory or log file)
        # Checking postProcessing directory recursively is slow.
        # Checking 'log.foamRun' is a good proxy because the solver writes to it step-by-step.
        # If log hasn't changed, plots likely haven't either.
        log_file = case_dir / "log.foamRun"
        is_not_modified, last_modified, _ = check_cache(log_file)
        if is_not_modified:
             return Response(status=304)

        # ⚡ Bolt Optimization: Secondary check using ETag based on directory mtimes.
        # Even if log changed (simulation running), field data might not have been written yet.
        # We check case_dir mtime (for new time dirs) and latest_time_dir mtime (for new fields).

        parser = OpenFOAMFieldParser(str(case_dir))

        # ⚡ Bolt Optimization: Stat case directory once
        # Move this up to avoid calling os.stat twice (inside get_time_directories and here)
        case_mtime = None
        try:
            case_mtime = os.stat(str(case_dir)).st_mtime
        except OSError:
            pass

        # Get time directories (cached if case mtime matches)
        time_dirs = parser.get_time_directories(known_mtime=case_mtime)

        etag = None
        if time_dirs and case_mtime is not None:
            latest_time = time_dirs[-1]
            latest_time_path = case_dir / latest_time

            # Get mtimes for ETag
            # We use case_dir mtime and latest_time_dir mtime.
            try:
                # case_mtime is already known
                latest_dir_mtime = os.stat(str(latest_time_path)).st_mtime

                # Construct ETag
                etag = f'"{case_mtime}-{latest_dir_mtime}"'

                if request.headers.get("If-None-Match") == etag:
                     response = Response(status=304)
                     response.headers["ETag"] = etag
                     return response

            except OSError:
                pass

        data = parser.get_all_time_series_data(max_points=100, known_case_mtime=case_mtime)
        response = fast_jsonify(data)
        if last_modified:
            response.headers["Last-Modified"] = last_modified
        if etag:
            response.headers["ETag"] = etag
        return response
    except Exception as e:
        logger.error(f"Error getting plot data: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


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
        return fast_jsonify({"error": "No tutorial specified"}), 400

    try:
        tutorial_name = posixpath.basename(tutorial)
        case_dir = validate_safe_path(CASE_ROOT, tutorial_name)
    except ValueError as e:
        return fast_jsonify({"error": str(e)}), 400

    if not case_dir.exists():
        return fast_jsonify({"error": "Case directory not found"}), 404

    try:
        parser = OpenFOAMFieldParser(str(case_dir))
        data = parser.get_latest_time_data()
        return fast_jsonify(data if data else {})
    except Exception as e:
        logger.error(f"Error getting latest data: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


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
        return fast_jsonify({"error": "No tutorial specified"}), 400

    try:
        tutorial_name = posixpath.basename(tutorial)
        case_dir = validate_safe_path(CASE_ROOT, tutorial_name)
    except ValueError as e:
        return fast_jsonify({"error": str(e)}), 400

    if not case_dir.exists():
        return fast_jsonify({"error": "Case directory not found"}), 404

    try:
        # Optimization: Check if log file has changed
        # We need to find the log file. It could be log.foamRun or custom.
        # OpenFOAMFieldParser.get_residuals_from_log searches for 'log.foamRun' or 'log.*'.
        # We'll explicitly check 'log.foamRun' here as the primary target.
        log_file = case_dir / "log.foamRun"
        is_not_modified, last_modified, stat_result = check_cache(log_file)
        if is_not_modified:
             return Response(status=304)

        parser = OpenFOAMFieldParser(str(case_dir))
        # ⚡ Bolt Optimization: Pass the stat result from check_cache to avoid re-stat call
        residuals = parser.get_residuals_from_log(known_stat=stat_result)
        response = fast_jsonify(residuals)
        if last_modified:
             response.headers["Last-Modified"] = last_modified
        return response
    except Exception as e:
        logger.error(f"Error getting residuals: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


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
        return fast_jsonify({"error": "No tutorial specified"}), 400

    try:
        # Validate that the tutorial path is safe
        validate_safe_path(CASE_ROOT, tutorial)

        # mesh_visualizer expects strings for paths currently
        tutorial_name = posixpath.basename(tutorial)
        mesh_files = mesh_visualizer.get_available_meshes(CASE_ROOT, tutorial_name)
        return fast_jsonify({"meshes": mesh_files})
    except ValueError as e:
        return fast_jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting available meshes: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


@app.route("/api/load_mesh", methods=["POST"])
@rate_limit(limit=10, window=60)
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
        return fast_jsonify({"error": "No file path provided"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        try:
            validated_path = validate_safe_path(CASE_ROOT, file_path)
        except ValueError as e:
            return fast_jsonify({"error": str(e)}), 400

        logger.info("[FOAMFlask] [api_load_mesh] Mesh loading called")
        mesh_info = mesh_visualizer.load_mesh(validated_path)

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
                return fast_jsonify({"error": str(e)}), 500

        return fast_jsonify(mesh_info)
    except Exception as e:
        logger.error(f"Error loading mesh: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


@app.route("/api/mesh_screenshot", methods=["POST"])
@rate_limit(limit=10, window=60)
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
        return fast_jsonify({"error": "No file path provided"}), 400

    # Security: Validate dimensions to prevent DoS
    if not isinstance(width, int) or not isinstance(height, int):
        return fast_jsonify({"error": "Width and height must be integers"}), 400

    MAX_DIMENSION = 4096
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        return fast_jsonify({"error": f"Dimensions too large (max {MAX_DIMENSION}px)"}), 400

    if width < 1 or height < 1:
        return fast_jsonify({"error": "Dimensions must be positive"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        try:
            validated_path = validate_safe_path(CASE_ROOT, file_path)
        except ValueError as e:
            return fast_jsonify({"error": str(e)}), 400

        img_str = mesh_visualizer.get_mesh_screenshot(
            validated_path, width, height, show_edges, color, camera_position
        )

        if img_str:
            response = fast_jsonify({"success": True, "image": img_str})
            # Optimization: Exclude visual graphics from compression
            response.headers["Content-Encoding"] = "identity"
            return response
        else:
            return (
                fast_jsonify({"success": False, "error": "Failed to generate screenshot"}),
                500,
            )
    except Exception as e:
        logger.error(f"Error generating mesh screenshot: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


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
        return fast_jsonify({"error": "No file path provided"}), 400

    try:
        # Security: Validate path is within CASE_ROOT
        try:
            validated_path = validate_safe_path(CASE_ROOT, file_path)
        except ValueError as e:
            return fast_jsonify({"error": str(e)}), 400

        html_content = mesh_visualizer.get_interactive_viewer_html(
            validated_path, show_edges, color
        )

        if html_content:
            response = Response(html_content, mimetype="text/html")
            # Optimization: Exclude visual graphics from compression
            response.headers["Content-Encoding"] = "identity"
            return response
        else:
            return (
                fast_jsonify(
                    {"success": False, "error": "Failed to generate interactive viewer"}
                ),
                500,
            )
    except Exception as e:
        logger.error(f"Error generating interactive viewer: {e}", exc_info=True)
        return fast_jsonify({"success": False, "error": sanitize_error(e)}), 500


@app.route("/run_foamtovtk", methods=["POST"])
@rate_limit(limit=10, window=60)
def run_foamtovtk() -> Union[Response, Tuple[Dict, int]]:
    """
    Run foamToVTK command in the Docker container.
    """
    data = request.json
    tutorial = data.get("tutorial")
    case_dir = data.get("caseDir")

    if not tutorial or not case_dir:
        return {"error": "Missing tutorial or caseDir"}, 400

    # Security: Validate tutorial path
    if not is_safe_tutorial_path(tutorial):
        return {"error": "Invalid tutorial path"}, 400

    # Security: Validate path is within CASE_ROOT
    try:
        validate_safe_path(CASE_ROOT, case_dir)
    except ValueError as e:
        logger.warning(f"Security violation in run_foamtovtk: {e}")
        return {"error": str(e)}, 400

    def stream_foamtovtk_logs() -> Generator[str, None, None]:
        """Stream logs for foamToVTK conversion process.
        
        Yields:
            Log lines as HTML-formatted strings.
        """
        client = get_docker_client()
        if client is None:
            yield "[FOAMFlask] [Error] Docker daemon not available. Please start Docker Desktop and try again.<br>"
            return

        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"

        # Convert Windows path to POSIX for Docker volumes
        host_path = Path(case_dir).resolve()
        host_path_str = host_path.as_posix() if platform.system() == "Windows" else str(host_path)

        # DEBUG: Check if we are pointing to the case itself or its parent
        tutorial_name = Path(tutorial).name
        # If case_dir ends with the tutorial name, we assume it IS the case directory
        is_direct_case_path = host_path.name == tutorial_name

        logger.info(f"[FOAMFlask] run_foamtovtk: tutorial='{tutorial}', case_dir='{case_dir}'")
        logger.info(f"[FOAMFlask] run_foamtovtk: is_direct_case_path={is_direct_case_path}")

        if is_direct_case_path:
             # Mount the case directory directly to /tmp/FOAM_Run
             # So inside container: /tmp/FOAM_Run contains the case files (0, constant, system) directly
             container_bind_path = "/tmp/FOAM_Run"
             container_case_path = "/tmp/FOAM_Run" # Working dir is the mount point
        else:
             # Mount the parent directory (presumably) so tutorial structure is preserved
             # e.g. /tmp/FOAM_Run/tutorial/case
             container_bind_path = "/tmp/FOAM_Run"
             container_case_path = posixpath.join("/tmp/FOAM_Run", tutorial_name) # nosec B108

        logger.info(f"[FOAMFlask] run_foamtovtk: container_case_path='{container_case_path}'")

        volumes = {
            host_path_str: {
                "bind": container_bind_path, # nosec B108
                "mode": "rw",
            }
        }

        # Security: Use positional arguments
        docker_cmd = [
            "bash", "-c",
            "source \"$1\" && cd \"$2\" && source \"$1\" && foamToVTK -case \"$2\"",
            "foamtovtk_runner",  # $0
            bashrc,              # $1
            container_case_path  # $2
        ]

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
                    yield f"{escape(subline)}<br>"

        except Exception as e:
            logger.error(f"Error running foamToVTK: {e}", exc_info=True)
            yield f"[FOAMFlask] [Error] {escape(sanitize_error(e))}<br>"

        finally:
            if 'container' in locals():
                try:
                    container.kill()
                except Exception as e:
                    logger.debug(f"[FOAMFlask] Error killing container: {e}")
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
        return fast_jsonify({"status": "success", "message": "Post processing endpoint"})
    except Exception as e:
        logger.error(f"Error during post-processing: {e}", exc_info=True)
        return fast_jsonify({"error": sanitize_error(e)}), 500


@app.route("/api/slice/create", methods=["POST"])
def create_slice() -> Union[Response, Tuple[Response, int]]:
    """Placeholder for slice creation."""
    data = request.get_json() or {}
    parent_id = data.get("parent_id")
    # For now, just pass to placeholder class to verify signature
    result = SliceVisualizer().process("", {}, parent_id=parent_id)
    return fast_jsonify({"status": "coming_soon", "message": "Slice visualization coming soon", "details": result}), 501

@app.route("/api/streamline/create", methods=["POST"])
def create_streamline() -> Union[Response, Tuple[Response, int]]:
    """Placeholder for streamline creation."""
    data = request.get_json() or {}
    parent_id = data.get("parent_id")
    result = StreamlineVisualizer().process("", {}, parent_id=parent_id)
    return fast_jsonify({"status": "coming_soon", "message": "Streamline visualization coming soon", "details": result}), 501

@app.route("/api/surface_projection/create", methods=["POST"])
def create_surface_projection() -> Union[Response, Tuple[Response, int]]:
    """Placeholder for surface projection creation."""
    data = request.get_json() or {}
    parent_id = data.get("parent_id")
    result = SurfaceProjectionVisualizer().process("", {}, parent_id=parent_id)
    return fast_jsonify({"status": "coming_soon", "message": "Surface projection visualization coming soon", "details": result}), 501


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
                fast_jsonify(
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
        num_isosurfaces = int(request_data.get("num_isosurfaces", 0))
        vtk_file_path = request_data.get("vtkFilePath")

        logger.info(
            f"[FOAMFlask] [create_contour] Parsed parameters: "
            f"tutorial={tutorial}, caseDir={case_dir_str}, "
            f"scalarField={scalar_field}, numIsosurfaces={num_isosurfaces}, "
            f"vtkFilePath={vtk_file_path}"
        )

        if not tutorial:
            error_msg = "Tutorial not specified"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return fast_jsonify({"success": False, "error": error_msg}), 400

        if not case_dir_str:
            error_msg = "Case directory not specified"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return fast_jsonify({"success": False, "error": error_msg}), 400

        # Normalize and validate path
        try:
            case_dir = validate_safe_path(CASE_ROOT, case_dir_str)
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"[FOAMFlask] [create_contour] Security: {error_msg}")
            return fast_jsonify({"success": False, "error": error_msg}), 400

        logger.info(
            f"[FOAMFlask] [create_contour] Normalized case directory: {case_dir}"
        )

        if not case_dir.exists():
            error_msg = f"Case directory not found: {case_dir}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return fast_jsonify({"success": False, "error": error_msg}), 404

        logger.info(f"[FOAMFlask] [create_contour] Case directory exists")

        target_vtk_file = None

        if vtk_file_path:
            # If specific file provided, validate and use it
            try:
                # Ensure the path is within the case directory or at least safe
                # We can reuse validate_safe_path but we need to match it against CASE_ROOT
                valid_vtk_path = validate_safe_path(CASE_ROOT, vtk_file_path)
                
                # Check if it actually exists
                if not valid_vtk_path.exists():
                     return fast_jsonify({"success": False, "error": f"Specified VTK file not found: {vtk_file_path}"}), 404
                
                target_vtk_file = str(valid_vtk_path)
                logger.info(f"[FOAMFlask] [create_contour] Using specified VTK file: {target_vtk_file}")

            except ValueError as e:
                return fast_jsonify({"success": False, "error": f"Invalid VTK file path: {str(e)}"}), 400
        else:
            # Fallback: Find latest VTK file
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
                return fast_jsonify({"success": False, "error": error_msg}), 404

            # Get latest VTK file
            target_vtk_file = max(vtk_files, key=os.path.getmtime)
            logger.info(f"[FOAMFlask] [create_contour] Using latest VTK file: {target_vtk_file}")

        # Load mesh
        logger.info(f"[FOAMFlask] [create_contour] Loading mesh...")
        mesh_info = isosurface_visualizer.load_mesh(target_vtk_file)

        if not mesh_info.get("success"):
            error_msg = f"Failed to load mesh: {mesh_info.get('error')}"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return fast_jsonify({"success": False, "error": error_msg}), 500

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
            return fast_jsonify({"success": False, "error": error_msg}), 400

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

        # Get specific isovalues if provided (for interactive slider)
        isovalues = request_data.get("isovalues")
        if isovalues:
            logger.info(f"[FOAMFlask] [create_contour] Using specific isovalues: {isovalues}")

        # Generate isosurfaces
        logger.info(
            f"[FOAMFlask] [create_contour] Generating {num_isosurfaces} isosurfaces..."
        )
        isosurface_info = isosurface_visualizer.generate_isosurfaces(
            scalar_field=scalar_field,
            num_isosurfaces=num_isosurfaces,
            custom_range=custom_range,
            isovalues=isovalues,
        )

        if not isosurface_info.get("success"):
            error_msg = (
                f"Failed to generate isosurfaces: {isosurface_info.get('error')}"
            )
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return fast_jsonify({"success": False, "error": error_msg}), 500

        logger.info(
            f"[FOAMFlask] [create_contour] Isosurfaces generated: {isosurface_info['n_points']} points"
        )

        # Get isovalue widget setting
        show_isovalue_widget = request_data.get("showIsovalueWidget", True)
        logger.info(f"[FOAMFlask] [create_contour] Show isovalue widget: {show_isovalue_widget}")

        # Generate HTML
        # Generate Trame Visualization (Embedded)
        logger.info(f"[FOAMFlask] [create_contour] Starting Trame visualization...")
        
        colormap = request_data.get("colormap", "viridis")
        logger.info(f"[FOAMFlask] [create_contour] Using colormap: {colormap}")

        # Start Trame server
        viz_info = isosurface_visualizer.start_trame_visualization(
            scalar_field=scalar_field,
            show_base_mesh=True,
            base_mesh_opacity=0.25,
            contour_opacity=0.8,
            contour_color="red",
            colormap=colormap,
            show_isovalue_slider=True,
            custom_range=custom_range,
            num_isosurfaces=num_isosurfaces,
            isovalues=isovalues,
        )
        
        # Return iframe configuration
        return fast_jsonify(viz_info)

        if not html_content:
            error_msg = "Empty HTML content generated"
            logger.error(f"[FOAMFlask] [create_contour] {error_msg}")
            return fast_jsonify({"success": False, "error": error_msg}), 500

        logger.info(
            f"[FOAMFlask] [create_contour] HTML generated: {len(html_content)} bytes"
        )

        # Return HTML
        logger.info(f"[FOAMFlask] [create_contour] Returning HTML response")
        response = Response(html_content, mimetype="text/html")
        # Optimization: Exclude visual graphics from compression
        response.headers["Content-Encoding"] = "identity"
        return response

    except Exception as e:
        logger.error(f"[FOAMFlask] [create_contour] Exception: {str(e)}")
        logger.error(f"[FOAMFlask] [create_contour] Exception type: {type(e).__name__}")
        import traceback

        logger.error(
            f"[FOAMFlask] [create_contour] Traceback:\n{traceback.format_exc()}"
        )

        return fast_jsonify({"success": False, "error": f"Server error: {sanitize_error(e)}"}), 500


@app.route("/api/upload_vtk", methods=["POST"])
def upload_vtk() -> Union[Response, Tuple[Response, int]]:
    """Upload VTK files for visualization.
    
    Returns:
        JSON response with upload status or error.
    """
    logger.info("[FOAMFlask] [upload_vtk] Received file upload request")
    if "file" not in request.files:
        return fast_jsonify({"success": False, "error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return fast_jsonify({"success": False, "error": "No selected file"}), 400

    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)

    if not file.filename:
        return fast_jsonify({"success": False, "error": "Invalid filename"}), 400

    filepath = temp_dir / secure_filename(file.filename)

    try:
        # Save the file temporarily
        file.save(str(filepath))

        # Use IsosurfaceVisualizer to handle the mesh loading
        visualizer = IsosurfaceVisualizer()
        result = visualizer.load_mesh(str(filepath))

        if not result.get("success", False):
            return (
                fast_jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Failed to load mesh"),
                    }
                ),
                400,
            )

        return fast_jsonify(
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
            fast_jsonify({"success": False, "error": f"Error processing file: {sanitize_error(e)}"}),
            500,
        )
    finally:
        # Clean up the temporary file
        try:
            if 'filepath' in locals() and filepath.exists():
                filepath.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up file {filepath}: {e}")


# --- Caching for Resource Geometry ---
_RESOURCE_GEOMETRY_CACHE: Dict[str, Union[str, List[str]]] = {}

@app.route("/api/resources/geometry/list", methods=["GET"])
def api_list_resource_geometry() -> Union[Response, Tuple[Response, int]]:
    """List available geometry files in $FOAM_TUTORIALS/resources/geometry."""
    global _RESOURCE_GEOMETRY_CACHE
    
    refresh = request.args.get("refresh", "false").lower() == "true"
    
    # Check cache if not refreshing
    if not refresh and _RESOURCE_GEOMETRY_CACHE.get("files"):
        logger.debug("[FOAMFlask] Returning cached resource geometry list")
        return fast_jsonify({"files": _RESOURCE_GEOMETRY_CACHE["files"]})

    try:
        client = get_docker_client()
        if client is None:
             return docker_unavailable_response()

        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
        # Security: Use list-based command construction to prevent shell injection
        # Even though there is no user input here, we maintain consistency
        docker_cmd = [
            "bash", "-c",
            "source \"$1\" && ls -1 $FOAM_TUTORIALS/resources/geometry",
            "list_geometry", # $0
            bashrc          # $1
        ]

        result = client.containers.run(
            DOCKER_IMAGE,
            docker_cmd,
            remove=True,
            stdout=True,
            stderr=True,
            tty=True
        )

        output = result.decode().strip()
        if not output:
             files = []
        else:
             files = [f.strip() for f in output.splitlines() if f.strip().lower().endswith(('.stl', '.obj', '.gz'))]
        
        files = sorted(files)
        
        # Update cache
        _RESOURCE_GEOMETRY_CACHE["files"] = files
        
        return fast_jsonify({"files": files})

    except Exception as e:
        logger.error(f"Error listing resource geometry: {e}")
        return fast_jsonify({"error": sanitize_error(e)}), 500


@app.route("/api/resources/geometry/fetch", methods=["POST"])
def api_fetch_resource_geometry() -> Union[Response, Tuple[Response, int]]:
    """Fetch a geometry file from resources to the case."""
    data = request.get_json()
    filename = data.get("filename")
    case_name = data.get("caseName")

    if not filename or not case_name:
        logger.error(f"Fetch failed: Missing filename ({filename}) or caseName ({case_name})")
        return fast_jsonify({"success": False, "message": "Missing filename or caseName"}), 400

    if not is_safe_script_name(filename):
         logger.error(f"Fetch failed: Invalid filename ({filename})")
         return fast_jsonify({"success": False, "message": "Invalid filename"}), 400

    try:
        case_dir_path = validate_safe_path(CASE_ROOT, case_name)
        tri_surface_dir = case_dir_path / "constant" / "triSurface"
        tri_surface_dir.mkdir(parents=True, exist_ok=True)
    except ValueError as e:
        logger.error(f"Fetch failed: Path validation error ({e})")
        return fast_jsonify({"success": False, "message": str(e)}), 400

    try:
        client = get_docker_client()
        if client is None:
             return docker_unavailable_response()

        bashrc = f"/opt/openfoam{OPENFOAM_VERSION}/etc/bashrc"
        host_path = tri_surface_dir.resolve()
        host_path_str = host_path.as_posix() if platform.system() == "Windows" else str(host_path)

        volumes = {
            host_path_str: {"bind": "/output", "mode": "rw"}
        }

        # Security: Use list-based command construction to prevent shell injection
        # Pass filename and bashrc as positional arguments to bash -c
        docker_cmd = [
            "bash", "-c",
            "source \"$1\" && cp $FOAM_TUTORIALS/resources/geometry/\"$2\" /output/",
            "fetcher",   # $0
            bashrc,      # $1
            filename     # $2
        ]
        
        run_kwargs = {
            "volumes": volumes,
            "remove": True,
            "stdout": True,
            "stderr": True
        }
        run_kwargs.update(get_docker_user_config())

        client.containers.run(
            DOCKER_IMAGE,
            docker_cmd,
            **run_kwargs
        )

        expected_file = tri_surface_dir / filename
        if expected_file.exists():
             return fast_jsonify({"success": True, "message": f"Fetched {filename}"})
        else:
             return fast_jsonify({"success": False, "message": "File copy failed"}), 500

    except Exception as e:
        logger.error(f"Error fetching resource geometry: {e}")
        return fast_jsonify({"success": False, "message": sanitize_error(e)}), 500


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

    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = 5000
    print(f"FOAMFlask listening on: {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
