import pytest
from backend.utils import sanitize_error
from docker.errors import DockerException

def test_sanitize_unquoted_unix_path_with_spaces():
    """Test that unquoted Unix paths with spaces are redacted."""
    sensitive_path = "/home/user/my secret documents/data"
    error_msg = f"bind: {sensitive_path}: permission denied"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)

    # Assert full path is gone
    assert sensitive_path not in sanitized, "Full sensitive path was found in sanitized message"

    # Assert partial parts are gone (checking 'secret documents' specifically)
    assert "secret documents" not in sanitized, "Partial path leaked in sanitized message"

    # Assert placeholder is present
    assert "[REDACTED_PATH]" in sanitized

def test_sanitize_unquoted_windows_path_with_spaces():
    """Test that unquoted Windows paths with spaces are redacted."""
    sensitive_path = r"C:\Users\Admin\My Secret Documents\Data"
    error_msg = f"Access denied to {sensitive_path}"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)

    assert sensitive_path not in sanitized
    assert "Secret Documents" not in sanitized
    assert "[REDACTED_PATH]" in sanitized

def test_sanitize_mixed_paths_with_spaces():
    """Test mixed quoted and unquoted paths with spaces."""
    path1 = "/home/user/secret one/data"
    path2 = "/home/user/secret two/data"
    error_msg = f"Failed copy from {path1} to \"{path2}\""
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)

    assert path1 not in sanitized
    assert path2 not in sanitized
    assert "secret one" not in sanitized
    assert "secret two" not in sanitized
    assert sanitized.count("[REDACTED_PATH]") >= 2

def test_sanitize_path_with_spaces_at_end():
    """Test path ending with space? Usually stripped but good to check regex behavior."""
    # This might match 'path ' if followed by something.
    # But usually paths don't end in space in error messages without a separator.
    sensitive_path = "/home/user/space end /file"
    error_msg = f"Error: {sensitive_path}"
    e = DockerException(error_msg)
    sanitized = sanitize_error(e)

    assert sensitive_path not in sanitized
    assert "[REDACTED_PATH]" in sanitized
