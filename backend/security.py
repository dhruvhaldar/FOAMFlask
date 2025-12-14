import os
import re
import logging
from pathlib import Path
from typing import Optional, Union
from werkzeug.utils import secure_filename as werkzeug_secure_filename

logger = logging.getLogger("FOAMFlask")

def validate_path(
    path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None,
    allow_new: bool = False
) -> Path:
    """
    Validates that a path is within the allowed base directory.

    Args:
        path: The path to validate.
        base_dir: The base directory to restrict access to. If None, it must be provided by the caller.
        allow_new: If True, allows the path to not exist (for file creation),
                   but the parent must be valid and within base_dir.

    Returns:
        The resolved Path object.

    Raises:
        ValueError: If base_dir is not provided.
        PermissionError: If the path is outside the base directory.
        FileNotFoundError: If the path does not exist (and allow_new is False).
    """
    if base_dir is None:
        raise ValueError("base_dir must be provided for path validation")

    # Resolve base_dir to absolute path
    base_path = Path(base_dir).resolve()

    # Resolve target path
    candidate_path = Path(path)
    if not candidate_path.is_absolute():
        candidate_path = (base_path / candidate_path)

    try:
        resolved_path = candidate_path.resolve()
    except OSError as e:
        raise ValueError(f"Invalid path structure: {e}")

    # Check if path starts with base_path
    try:
        resolved_path.relative_to(base_path)
    except ValueError:
        raise PermissionError(f"Access denied: Path {resolved_path} is outside allowed directory {base_path}")

    if not allow_new and not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {resolved_path}")

    return resolved_path

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to ensure it's safe to use.

    Args:
        filename: The input filename.

    Returns:
        A secure filename.
    """
    clean_name = werkzeug_secure_filename(filename)
    if not clean_name:
        raise ValueError("Invalid filename")
    return clean_name

def is_safe_command(command: str) -> bool:
    """
    Validate command input to prevent shell injection and ReDoS.

    Args:
        command: User-provided command string

    Returns:
        True if command is safe, False otherwise
    """
    if not command or not isinstance(command, str):
        return False

    # Length check to prevent ReDoS and buffer issues
    if len(command) > 100:
        return False

    # Check for dangerous shell metacharacters
    # Blocking < and > explicitly prevents the regex issue [0-9]+[<>]
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'"]
    if any(char in command for char in dangerous_chars):
        return False

    # Check for path traversal attempts
    if '..' in command:
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
