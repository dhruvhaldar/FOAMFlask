import pytest
from app import is_safe_command

def test_is_safe_command_blocks_braces():
    """Verify that is_safe_command blocks brace expansion."""
    assert is_safe_command("touch {a,b}") is False, "Brace expansion should be blocked"
    assert is_safe_command("echo {1..10}") is False, "Brace expansion should be blocked"
    assert is_safe_command("valid_command") is True, "Valid command should be allowed"

def test_is_safe_command_blocks_advanced_metachars():
    """Verify that is_safe_command blocks advanced shell metacharacters."""
    dangerous = ["\\", "#"]
    for char in dangerous:
        assert is_safe_command(f"command{char}arg") is False, f"Character '{char}' should be blocked"

def test_is_safe_command_allows_common_chars():
    """Verify that is_safe_command allows common argument characters."""
    safe_chars = [":", "=", "^", ",", "@"]
    for char in safe_chars:
        assert is_safe_command(f"command{char}arg") is True, f"Character '{char}' should be allowed"
