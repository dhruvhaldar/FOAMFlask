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
    """
    if base_dir is None:
        raise ValueError("base_dir must be provided for path validation")

    str_path = str(path)
    str_base = str(base_dir)

    # 1. Resolve base directory strictly
    try:
        real_base = os.path.realpath(os.path.abspath(str_base))
    except Exception as e:
        raise ValueError(f"Invalid base path: {e}")

    # 2. Pre-check for traversal chars in input
    if ".." in str_path:
         raise ValueError("Invalid path: traversal characters detected")

    try:
        # 3. Join and Normalize (String-level only)
        # Use abspath to normalize.
        if os.path.isabs(str_path):
            final_path = os.path.abspath(str_path)
        else:
            final_path = os.path.abspath(os.path.join(real_base, str_path))

        # 4. Check for Containment (String Prefix)
        # Ensure the final path starts with the real base path
        # We add os.sep to ensure /base/foo is not matched by /base/foobar
        base_prefix = real_base + os.sep

        # Handle exact match or prefix match
        if final_path != real_base and not final_path.startswith(base_prefix):
             raise PermissionError(f"Access denied: Path {final_path} is outside allowed directory {real_base}")

        # Check existence if required
        if not allow_new and not os.path.exists(final_path):
             raise FileNotFoundError(f"File not found: {final_path}")

    except Exception as e:
        if isinstance(e, (ValueError, PermissionError, FileNotFoundError)):
            raise
        raise ValueError(f"Invalid path structure: {e}")

    return Path(final_path)

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
    # Validate each component string for basic safety
    for p in paths:
        if ".." in str(p):
             raise ValueError("Invalid path component: traversal detected")

    # Join using os.path.join
    try:
        candidate = os.path.join(str(base), *[str(p) for p in paths])
    except Exception as e:
        raise ValueError(f"Error joining paths: {e}")

    # Validate the result against base
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

    if len(command) > 100:
        return False

    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'"]
    if any(char in command for char in dangerous_chars):
        return False

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

    # Simple alphanumeric + dot/dash/underscore check
    if not re.match(r'^[a-zA-Z0-9_.-]+$', script_name):
        return False

    if '..' in script_name or '/' in script_name or '\\' in script_name:
        return False

    if script_name.startswith('.'):
        return False

    if len(script_name) > 50:
        return False

    return True
