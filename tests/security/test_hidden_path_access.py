
import pytest
from app import is_safe_case_root
import os

def test_hidden_directories_are_blocked():
    """
    Test that is_safe_case_root blocks paths containing hidden directories
    (starting with .), which are often used for sensitive configuration (e.g. .ssh, .aws).
    """
    # Should ideally be blocked, but currently might pass if not explicitly in blacklist
    # We want to assert False eventually

    # Examples of sensitive hidden directories
    assert is_safe_case_root("/home/user/.ssh") is False, "Should block .ssh"
    assert is_safe_case_root("/home/user/.aws") is False, "Should block .aws"
    assert is_safe_case_root("/home/user/.kube") is False, "Should block .kube"
    assert is_safe_case_root("/home/user/.config") is False, "Should block .config"

    # General hidden directory
    assert is_safe_case_root("/home/user/.hidden_project") is False, "Should block arbitrary hidden directories"

def test_standard_directories_are_allowed():
    assert is_safe_case_root("/home/user/documents") is True
    assert is_safe_case_root("/opt/openfoam") is True
