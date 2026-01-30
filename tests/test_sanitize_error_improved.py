import pytest
from backend.utils import sanitize_error
from docker.errors import DockerException


def test_sanitize_double_quotes():
    """Test that double-quoted paths are redacted."""
    sensitive_path = "/home/user/secret/data"
    error_msg = f'Error: File "{sensitive_path}" not found'
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized


def test_sanitize_mixed_quotes():
    """Test mixed quotes in one message."""
    path1 = "/home/secret/1"
    path2 = "/home/secret/2"
    error_msg = f"Failed '{path1}' and \"{path2}\""
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert path1 not in sanitized
    assert path2 not in sanitized
    assert sanitized.count("[REDACTED_PATH]") >= 2


def test_sanitize_unquoted_path_unix():
    """Test redaction of unquoted absolute Unix paths."""
    sensitive_path = "/var/lib/docker/volumes/secret/_data"
    error_msg = f"bind: {sensitive_path}: permission denied"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized


def test_sanitize_unquoted_path_windows():
    """Test redaction of unquoted absolute Windows paths."""
    sensitive_path = r"C:\Users\Admin\Secret\Data"
    error_msg = f"Access denied to {sensitive_path}"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized


def test_sanitize_preserve_urls():
    """Test that URLs are NOT redacted."""
    url = "http://example.com/foo/bar"
    error_msg = f"Failed to connect to {url}"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert url in sanitized
    assert "[REDACTED_PATH]" not in sanitized


def test_sanitize_preserve_https_urls():
    """Test that HTTPS URLs are NOT redacted."""
    url = "https://registry.hub.docker.com/v2/repositories/library/ubuntu"
    error_msg = f"Get {url}: dial tcp: lookup registry...: no such host"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert url in sanitized


def test_sanitize_short_path():
    """Test redaction of short paths like /tmp/foo."""
    sensitive_path = "/tmp/foam_run"
    error_msg = f"Error at {sensitive_path}"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)
    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized
