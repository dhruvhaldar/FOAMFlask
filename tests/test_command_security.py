import pytest
from app import is_safe_command

def test_is_safe_command_blocks_braces():
    """Verify that is_safe_command blocks brace expansion."""
    assert is_safe_command("touch {a,b}") is False, "Brace expansion should be blocked"
    assert is_safe_command("echo {1..10}") is False, "Brace expansion should be blocked"
    assert is_safe_command("valid_command") is True, "Valid command should be allowed"
