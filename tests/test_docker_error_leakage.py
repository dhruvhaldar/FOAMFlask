import pytest
from backend.utils import sanitize_error
from docker.errors import DockerException

def test_sanitize_docker_error_leakage_unix():
    """
    Test that Unix paths are redacted in Docker exceptions.
    """
    sensitive_path = "/home/user/secret/case/data"
    error_msg = f"Bind mount failed: '{sensitive_path}' does not exist"
    e = DockerException(error_msg)

    sanitized = sanitize_error(e)

    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized
    assert "Bind mount failed" in sanitized

def test_sanitize_docker_error_leakage_windows():
    """
    Test that Windows paths are redacted in Docker exceptions.
    """
    sensitive_path = r"C:\Users\Admin\Secret\Case"
    error_msg = f"Bind mount failed: '{sensitive_path}' does not exist"
    e = DockerException(error_msg)

    sanitized = sanitize_error(e)

    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized
    assert "Bind mount failed" in sanitized

def test_sanitize_docker_error_leakage_with_spaces():
    """
    Test that paths with spaces are redacted.
    """
    sensitive_path = "/home/user/my secret project/case data"
    error_msg = f"Bind mount failed: '{sensitive_path}' does not exist"
    e = DockerException(error_msg)

    sanitized = sanitize_error(e)

    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized

def test_sanitize_docker_error_no_path():
    """
    Test that Docker exceptions without paths are preserved.
    """
    error_msg = "Connection refused"
    e = DockerException(error_msg)

    sanitized = sanitize_error(e)

    assert sanitized == error_msg

def test_sanitize_docker_error_leakage_unquoted_unix():
    """
    Test that unquoted Unix paths are redacted.
    """
    sensitive_path = "/home/user/secret/case/data"
    error_msg = f"bind source path does not exist: {sensitive_path}"
    e = DockerException(error_msg)

    sanitized = sanitize_error(e)

    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized

def test_sanitize_docker_error_leakage_unquoted_windows():
    """
    Test that unquoted Windows paths are redacted.
    """
    sensitive_path = r"C:\Users\Admin\Secret\Case"
    error_msg = f"bind source path does not exist: {sensitive_path}"
    e = DockerException(error_msg)

    sanitized = sanitize_error(e)

    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized
