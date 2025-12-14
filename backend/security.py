import os
import re
import logging
from pathlib import Path
from typing import Optional, Union, List
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
    """
    if base_dir is None:
        raise ValueError("base_dir must be provided for path validation")

    # Pre-validation: Check for traversal characters in the input string
    str_path = str(path)
    if ".." in str_path:
        raise ValueError("Invalid path: traversal characters detected")

    # Resolve base_dir
    str_base = str(base_dir)
    try:
        abs_base = os.path.abspath(str_base)
        real_base = os.path.realpath(abs_base)
    except Exception as e:
        raise ValueError(f"Invalid base path: {e}")

    # Resolve target path
    try:
        if not os.path.isabs(str_path):
            abs_path = os.path.abspath(os.path.join(real_base, str_path))
        else:
            abs_path = os.path.abspath(str_path)

        real_path = os.path.realpath(abs_path)
    except Exception as e:
        raise ValueError(f"Invalid path structure: {e}")

    # Check common path
    try:
        common = os.path.commonpath([real_base, real_path])
        if os.path.normcase(common) != os.path.normcase(real_base):
             raise PermissionError(f"Access denied: Path {real_path} is outside allowed directory {real_base}")
    except ValueError:
        raise PermissionError(f"Access denied: Path {real_path} is on a different drive than {real_base}")

    if not allow_new and not os.path.exists(real_path):
        raise FileNotFoundError(f"File not found: {real_path}")

    return Path(real_path)

def safe_join(base: Union[str, Path], *paths: Union[str, Path]) -> Path:
    """
    Safely joins a base path with one or more path components, ensuring the result
    is within the base directory.

    Args:
        base: The trusted base directory.
        *paths: Path components to join.

    Returns:
        The validated Path object.
    """
    # 1. Join components to create candidate string
    # We validate each component for basic safety first
    for p in paths:
        if ".." in str(p):
             raise ValueError("Invalid path component: traversal detected")

    # Join using os.path.join
    try:
        candidate = os.path.join(str(base), *[str(p) for p in paths])
    except Exception as e:
        raise ValueError(f"Error joining paths: {e}")

    # 2. Validate the result against base
    # We pass allow_new=True because we might be constructing a path for a new file
    # or the caller will check existence later.
    # Actually, validate_path raises FileNotFoundError if not allow_new.
    # safe_join is often used for lookup. If we want to check existence, we can do it after.
    # Let's default to allow_new=True to be permissive about existence (only enforcing security),
    # and let the caller check .exists() if they need to read it.

    return validate_path(candidate, base_dir=base, allow_new=True)

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
