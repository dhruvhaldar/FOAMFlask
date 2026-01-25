import logging
import re
from typing import Any
from docker.errors import DockerException

logger = logging.getLogger("FOAMFlask")

def sanitize_error(e: Exception) -> str:
    """
    Sanitize exception messages to prevent information leakage.
    Returns a generic message for unexpected errors, or the specific message
    for safe errors (like ValueError from validation).
    """
    # Safe validation errors that we want to show to the user
    if isinstance(e, (ValueError, TypeError)):
        return str(e)

    # Docker errors might be safe if they are connection errors, but API errors can leak paths.
    # We'll trust DockerException messages for now as they are often needed for debugging config.
    if isinstance(e, DockerException):
        # Additional check: If it contains "Bind mount failed", it might leak paths.
        # But we need to balance debuggability.
        # For Sentinel purposes, we can try to mask paths if we detect them?
        # For now, we follow the existing pattern in app.py which allowed DockerException.
        return str(e)

    # Check for OSError/IOError which might contain paths (e.g. PermissionError, FileNotFoundError)
    if isinstance(e, OSError):
        # We mask the specific path information
        return "An I/O error occurred. Please check the logs."

    # Generic fallback for other exceptions
    return "An internal server error occurred."

def is_safe_color(color: Any) -> bool:
    """
    Validate color input to prevent XSS and injection.

    Args:
        color: Color string (name or hex) or RGB(A) list/tuple

    Returns:
        True if color is safe, False otherwise
    """
    # Allow RGB/RGBA lists or tuples
    if isinstance(color, (list, tuple)):
        return all(isinstance(c, (int, float)) for c in color)

    if not isinstance(color, str):
        return False

    # Allow hex strings (e.g. #FFF, #FFFFFF)
    if re.match(r'^#[0-9a-fA-F]{3,8}$', color):
        return True

    # Allow alphanumeric color names (e.g. "red", "lightblue", "tab:blue")
    # Also allow underscores/hyphens for colormaps (e.g. "viridis")
    if re.match(r'^[a-zA-Z0-9_:-]+$', color):
        return True

    return False

def is_safe_command(command: str) -> bool:
    """
    Validate command input to prevent shell injection.

    Args:
        command: User-provided command string

    Returns:
        True if command is safe, False otherwise
    """
    if not command or not isinstance(command, str):
        return False

    # Check for dangerous shell metacharacters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'"]
    # Add newline characters to prevent command injection
    dangerous_chars.extend(['\n', '\r'])
    # Add brace expansion to prevent unexpected file creation
    dangerous_chars.extend(['{', '}'])

    if any(char in command for char in dangerous_chars):
        return False

    # Check for path traversal attempts
    if '..' in command:
        return False

    # Check for command substitution
    if '$(' in command or '`' in command:
        return False

    # Check for file descriptor redirection
    if re.search(r'[0-9]+[<>]', command):
        return False

    # Check for background/foreground operators
    if '&' in command or '%' in command:
        return False

    # Length check to prevent extremely long commands
    if len(command) > 100:
        return False

    return True
