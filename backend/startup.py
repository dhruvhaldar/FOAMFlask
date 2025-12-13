
import os
import platform
import logging
import uuid
import time
from pathlib import Path
from typing import Dict, Any, Callable, Tuple, Optional

logger = logging.getLogger("FOAMFlask")

def check_docker_permissions(
    get_docker_client_func: Callable[[], Any],
    case_root: str,
    docker_image: str,
    save_config_func: Callable[[Dict[str, Any]], bool],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Checks if Docker creates files with root permissions and attempts to fix it.

    Args:
        get_docker_client_func: Function to get docker client
        case_root: Path to the case directory
        docker_image: Docker image name
        save_config_func: Function to save configuration
        config: Current configuration dictionary

    Returns:
        Dictionary with status and message
    """

    # Skip if already done
    if config.get("initial_setup_done"):
        return {"status": "completed", "message": "Initial setup already completed"}

    # Determine if we are on Linux
    is_linux = platform.system() == "Linux"
    if not is_linux:
        # On Windows/Mac (Docker Desktop), permissions are usually handled by the VM
        save_config_func({"initial_setup_done": True, "docker_run_as_user": False})
        return {"status": "completed", "message": "Non-Linux system, skipping permission check"}

    client = get_docker_client_func()
    if not client:
        return {"status": "failed", "message": "Docker not available"}

    logger.info("[FOAMFlask] Starting Docker permission check (Dry Run)...")

    # Ensure case root exists
    case_dir_path = Path(case_root).resolve()
    try:
        case_dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {"status": "failed", "message": f"Could not create case directory: {e}"}

    # Generate a unique test file name
    test_filename = f".permission_test_{uuid.uuid4().hex}"
    host_test_file = case_dir_path / test_filename
    container_run_path = "/tmp/foam_flask_check"

    # Volume mapping
    volumes = {
        str(case_dir_path): {
            "bind": container_run_path,
            "mode": "rw"
        }
    }

    # Attempt 1: Default run (usually root)
    try:
        logger.info("[FOAMFlask] Permission Check: Attempting default write...")
        # Command to touch a file
        cmd = f"touch {container_run_path}/{test_filename}"

        container = client.containers.run(
            docker_image,
            f"bash -c '{cmd}'",
            volumes=volumes,
            remove=True,
            detach=False # Wait for it to finish
        )

        # Check if file exists
        if not host_test_file.exists():
            return {"status": "failed", "message": "Docker container failed to write test file"}

        # Try to delete it
        try:
            host_test_file.unlink()
            # Success! No permission issues.
            logger.info("[FOAMFlask] Permission Check: Default write success. No permission issues.")
            save_config_func({"initial_setup_done": True, "docker_run_as_user": False})
            return {"status": "completed", "message": "Permission check passed (default)"}

        except PermissionError:
            logger.warning("[FOAMFlask] Permission Check: Default write caused PermissionError. Trying fix...")
            # We cannot delete the file. It's likely owned by root.
            # We need to clean it up later or try to use sudo (not possible here).
            # But let's try the fix now.

            # Note: We still have the root-owned file on disk which we can't delete.
            # Ideally, we should use a container to delete it if we can.
            try:
                cleanup_cmd = f"rm {container_run_path}/{test_filename}"
                client.containers.run(
                    docker_image,
                    f"bash -c '{cleanup_cmd}'",
                    volumes=volumes,
                    remove=True
                )
            except Exception as e:
                logger.error(f"[FOAMFlask] Failed to cleanup root file: {e}")

    except Exception as e:
        logger.warning(f"[FOAMFlask] Permission Check: Default write caused error: {e}")
        logger.warning("[FOAMFlask] Default permission check failed. Attempting automatic fix by switching to user mapping...")
        # Proceed to Attempt 2

    # Attempt 2: Run as user
    try:
        uid = os.getuid()
        gid = os.getgid()
        user_str = f"{uid}:{gid}"

        logger.info(f"[FOAMFlask] Permission Check: Attempting write as user {user_str}...")

        cmd = f"touch {container_run_path}/{test_filename}"

        client.containers.run(
            docker_image,
            f"bash -c '{cmd}'",
            volumes=volumes,
            user=user_str,
            remove=True,
            detach=False
        )

        if not host_test_file.exists():
             return {"status": "failed", "message": "Docker container failed to write test file as user"}

        # Try to delete it
        host_test_file.unlink()

        # Success!
        logger.info("[FOAMFlask] Permission Check: User write success.")
        save_config_func({
            "initial_setup_done": True,
            "docker_run_as_user": True,
            "docker_uid": uid,
            "docker_gid": gid
        })
        return {"status": "completed", "message": "Permission check passed (using host user)"}

    except Exception as e:
        logger.error(f"[FOAMFlask] Permission Check: Error during Attempt 2: {e}")
        return {"status": "failed", "message": f"Permission check failed even with user mapping: {e}"}
