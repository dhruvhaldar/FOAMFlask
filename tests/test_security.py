import os
import pytest
from pathlib import Path
from backend.security import validate_path, is_safe_command, is_safe_script_name

# --- Tests for validate_path ---

def test_validate_path_valid():
    base = Path("/tmp/base")
    # We mock existence checks or use real temporary dirs
    # For validate_path, we can use a temporary directory structure
    pass

def test_validate_path_traversal():
    base = Path("/tmp/base").resolve()
    # ../ attempts
    with pytest.raises(PermissionError):
        validate_path(base / "../outside", base, allow_new=True)

def test_validate_path_absolute_outside():
    base = Path("/tmp/base").resolve()
    outside = Path("/etc/passwd").resolve()
    with pytest.raises(PermissionError):
        validate_path(outside, base, allow_new=True)

def test_validate_path_inside(tmp_path):
    base = tmp_path
    child = base / "child"
    child.touch()
    assert validate_path(child, base) == child

def test_validate_path_new_file(tmp_path):
    base = tmp_path
    new_file = base / "newfile.txt"
    assert validate_path(new_file, base, allow_new=True) == new_file

def test_validate_path_not_exists(tmp_path):
    base = tmp_path
    non_existent = base / "fake.txt"
    with pytest.raises(FileNotFoundError):
        validate_path(non_existent, base, allow_new=False)

# --- Tests for is_safe_command ---

def test_is_safe_command_valid():
    assert is_safe_command("blockMesh")
    assert is_safe_command("simpleFoam -parallel")
    # Note: my implementation allows spaces but blocks dangerous chars

def test_is_safe_command_metachars():
    assert not is_safe_command("command; rm -rf /")
    assert not is_safe_command("command | other")
    assert not is_safe_command("command && other")
    assert not is_safe_command("command > output")
    assert not is_safe_command("command < input")

def test_is_safe_command_redos_prevention():
    # Long string check
    long_cmd = "a" * 101
    assert not is_safe_command(long_cmd)

def test_is_safe_command_explicit_block():
    assert not is_safe_command("2>")
    assert not is_safe_command("1<")

# --- Tests for is_safe_script_name ---

def test_is_safe_script_name_valid():
    assert is_safe_script_name("run_case.sh")
    assert is_safe_script_name("Allrun")
    assert is_safe_script_name("script-1.sh")

def test_is_safe_script_name_invalid():
    assert not is_safe_script_name("../script.sh")
    assert not is_safe_script_name("/bin/sh")
    assert not is_safe_script_name(".hidden")
    assert not is_safe_script_name("script with spaces.sh")
    assert not is_safe_script_name("script;whoami.sh")
