import os
import pytest
from pathlib import Path
from backend.security import validate_path, is_safe_command, is_safe_script_name, safe_join

# --- Tests for validate_path ---

def test_validate_path_valid():
    base = Path("/tmp/base")
    # We mock existence checks or use real temporary dirs
    # For validate_path, we can use a temporary directory structure
    pass

def test_validate_path_traversal(tmp_path):
    base = tmp_path
    # ../ attempts using string traversal logic
    with pytest.raises(ValueError, match="Invalid path: traversal characters detected"):
        validate_path("../outside", base, allow_new=True)

def test_validate_path_absolute_outside(tmp_path):
    base = tmp_path
    # Outside absolute path
    outside = Path("/etc/passwd")
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

# --- Tests for safe_join ---

def test_safe_join_valid(tmp_path):
    base = tmp_path
    # Create structure
    (base / "subdir").mkdir()
    target = base / "subdir" / "file.txt"
    target.touch()

    joined = safe_join(base, "subdir", "file.txt")
    assert joined == target

def test_safe_join_traversal(tmp_path):
    base = tmp_path
    with pytest.raises(ValueError, match="traversal detected"):
        safe_join(base, "subdir", "..", "file.txt")

def test_safe_join_absolute_component(tmp_path):
    base = tmp_path
    # os.path.join with absolute path discards previous
    # but validate_path should catch it if it's outside

    # If absolute path is inside base (unlikely on linux without common root issues)
    # /etc/passwd is definitely out

    # We expect validate_path to catch it because allow_new=True but permission error
    # Wait, safe_join does: candidate = os.path.join(...)
    # If we pass "/etc/passwd", candidate becomes "/etc/passwd"
    # validate_path("/etc/passwd", base) -> PermissionError

    with pytest.raises(PermissionError):
        safe_join(base, "/etc/passwd")

# --- Tests for is_safe_command ---

def test_is_safe_command_valid():
    assert is_safe_command("blockMesh")
    assert is_safe_command("simpleFoam -parallel")

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
