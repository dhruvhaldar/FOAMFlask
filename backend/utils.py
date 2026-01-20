import logging
import re
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
