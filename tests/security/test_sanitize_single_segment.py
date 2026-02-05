import pytest
from backend.utils import sanitize_error
from docker.errors import DockerException

def test_sanitize_single_segment_unix():
    """Test redaction of single-segment Unix paths (e.g. /secret)."""
    sensitive_path = "/secret"
    error_msg = f"Error: {sensitive_path} not found"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized

def test_sanitize_root_unix():
    """Test that root path '/' is NOT redacted."""
    error_msg = "Error: / is not writable"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert "/" in sanitized
    assert "[REDACTED_PATH]" not in sanitized

def test_sanitize_url_unix():
    """Test that URLs starting with / (e.g. after domain) are handled correctly (preserved)."""
    # Note: The regex uses negative lookbehind for :// and :/ so URLs are preserved
    url = "http://example.com/foo"
    error_msg = f"Connect to {url}"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert url in sanitized

def test_sanitize_single_segment_windows():
    """Test redaction of single-segment Windows paths (e.g. C:\\Secret)."""
    sensitive_path = r"C:\Secret"
    error_msg = f"Error: {sensitive_path} not found"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized

def test_sanitize_multi_segment_preserved():
    """Verify that multi-segment paths are still redacted (regression test)."""
    sensitive_path = "/a/b/c"
    error_msg = f"Error: {sensitive_path}"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized
