import pytest
import re
from backend.utils import sanitize_error
from docker.errors import DockerException

def test_sanitize_special_chars_paths():
    """Test that paths with special characters are correctly redacted."""
    sensitive_paths = [
        "/home/user/my@email.com/data",
        "/tmp/token-abc+123/file",
        "/var/lib/docker/volumes/hash#123/_data",
        "/opt/app/config/key=value.json",
        "/path/with~tilde/file",
        "/path/with%percent/file"
    ]

    for path in sensitive_paths:
        msg = f"Error: File {path} not found"
        e = DockerException(msg)
        sanitized = sanitize_error(e)

        # Verify the path is redacted
        assert path not in sanitized, f"Path {path} leaked!"
        assert "[REDACTED_PATH]" in sanitized

        # Verify no partial leaks
        # E.g. if path is /a/b@c, and regex stops at @, it leaks @c
        # We check if any significant suffix of the path remains.

        # Note: The current heuristic regex is greedy with spaces and might consume trailing text.
        # This is an existing limitation. We focus on ensuring the SENSITIVE part is gone.
        # For /home/user/my@email.com/data, if it leaks @email.com/data, that's bad.

        # We strip [REDACTED_PATH] and check if the remainder contains sensitive parts of the path.
        # This is hard to do generically.
        # But we know what we expect NOT to see.

        # Check if the path suffix (after special chars) is present
        # e.g. for /home/user/my@email.com/data, check "@email.com/data"

        special_char_part = re.search(r"[@+=%~#].*", path)
        if special_char_part:
            suffix = special_char_part.group(0)
            assert suffix not in sanitized, f"Suffix '{suffix}' leaked in {sanitized}"

def test_sanitize_urls_preserved():
    """Test that URLs are still preserved (no regression)."""
    urls = [
        "http://example.com/foo/bar",
        "https://registry.hub.docker.com/v2/repositories/library/ubuntu",
        "ftp://server.com/resource"
    ]

    for url in urls:
        msg = f"Connect to {url} failed"
        e = DockerException(msg)
        sanitized = sanitize_error(e)

        assert url in sanitized, f"URL {url} was redacted!"

def test_sanitize_windows_paths_special_chars():
    """Test Windows paths with special characters."""
    paths = [
        r"C:\Users\Admin\my@email.com\Data",
        r"D:\Backups\project+v1\data"
    ]

    for path in paths:
        msg = f"Access denied to {path}"
        e = DockerException(msg)
        sanitized = sanitize_error(e)

        assert path not in sanitized
        assert "[REDACTED_PATH]" in sanitized
        assert sanitized == "Access denied to [REDACTED_PATH]"

def test_sanitize_mixed_content():
    """Test mixed content with paths and other text."""
    path = "/var/log/app.log"
    msg = f"Failed to write to {path} due to disk full"
    e = DockerException(msg)
    sanitized = sanitize_error(e)

    assert path not in sanitized
    assert "[REDACTED_PATH]" in sanitized
    # Note: Over-redaction of " due to disk full" is a known issue with the heuristic
    # We just ensure the path itself is redacted.
