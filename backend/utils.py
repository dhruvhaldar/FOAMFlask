import logging
import re
from typing import Any
from docker.errors import DockerException

logger = logging.getLogger("FOAMFlask")


def safe_decompress(
    source_stream: Any, dest_stream: Any, max_size: int = 1073741824
) -> None:
    """
    Safely decompress data with a size limit to prevent zip bombs.

    Args:
        source_stream: Input stream (e.g. GzipFile).
        dest_stream: Output stream (e.g. file object).
        max_size: Maximum allowed decompressed size in bytes (default 1GB).

    Raises:
        ValueError: If decompressed size exceeds max_size.
    """
    chunk_size = 1024 * 1024  # 1MB
    total_size = 0

    while True:
        chunk = source_stream.read(chunk_size)
        if not chunk:
            break

        total_size += len(chunk)
        if total_size > max_size:
            raise ValueError(
                f"Security: Decompressed file size exceeds limit of {max_size} bytes"
            )

        dest_stream.write(chunk)


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
        msg = str(e)

        # 1. Redact quoted paths (single or double quotes)
        # Unix paths: Match start with / inside quotes
        # Matches: quote, /..., same quote
        msg = re.sub(r"(['\"])(/(?:(?!\1).)+)\1", r"\1[REDACTED_PATH]\1", msg)

        # Windows paths: Drive:\... or Drive:... inside quotes
        # Matches: quote, C:\..., same quote
        msg = re.sub(
            r"(['\"])([a-zA-Z]:\\\\?(?:(?!\1).)+)\1", r"\1[REDACTED_PATH]\1", msg
        )

        # 2. Redact unquoted absolute paths (heuristic)
        # Unix: /path/to/something
        # Look for / followed by allowed path characters.
        # Negative lookbehind ensures we don't break URLs (http://, https://)
        # Expanded allowed characters to include @, +, =, %, ~, # to prevent partial leakage
        chars = r"\w\.\-@+=%~#"
        unix_path_pattern = rf"(?<!\w)(?<!://)(?<!:/)(/(?:[{chars}][{chars} ]*/)*[{chars}][{chars} ]*)"
        msg = re.sub(unix_path_pattern, "[REDACTED_PATH]", msg)

        # Windows: C:\path\to...
        win_path_pattern = rf"([a-zA-Z]:\\\\?(?:[{chars}][{chars} ]*\\\\?)*[{chars}][{chars} ]*)"
        msg = re.sub(win_path_pattern, "[REDACTED_PATH]", msg)

        return msg

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
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'"]
    # Add globbing characters to prevent wildcard expansion
    dangerous_chars.extend(["*", "?", "[", "]"])
    # Add other shell metacharacters
    dangerous_chars.extend(["~", "!"])
    # Add newline characters to prevent command injection
    dangerous_chars.extend(["\n", "\r"])
    # Add brace expansion to prevent unexpected file creation
    dangerous_chars.extend(["{", "}"])
    # Add other potentially dangerous characters (comments, escaping)
    dangerous_chars.extend(["\\", "#"])

    if any(char in command for char in dangerous_chars):
        return False

    # Check for path traversal attempts
    if ".." in command:
        return False

    # Check for command substitution
    if "$(" in command or "`" in command:
        return False

    # Check for file descriptor redirection
    if re.search(r"[0-9]+[<>]", command):
        return False

    # Check for background/foreground operators
    if "&" in command or "%" in command:
        return False

    # Length check to prevent extremely long commands
    if len(command) > 100:
        return False

    return True


def is_safe_color(color: str) -> bool:
    """
    Validate color string to prevent XSS.
    Allows hex codes and alphanumeric color names.
    Also allows colormaps with alphanumeric characters, spaces, hyphens, and colons.
    """
    if not color or not isinstance(color, str):
        return False

    # Check length
    if len(color) > 50:
        return False

    # Allow alphanumeric, spaces, hyphens, underscores, dots, hashes, and colons.
    # Strict enough to prevent XSS (no < > " ' ; ( )).
    if re.match(r"^[a-zA-Z0-9\s#:_.-]+$", color):
        return True

    return False
