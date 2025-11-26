#!/usr/bin/env python3
"""
Security tests for command validation functions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import is_safe_command, is_safe_script_name


def test_is_safe_command():
    """Test safe command validation."""
    
    # Safe commands
    safe_commands = [
        "blockMesh",
        "simpleFoam", 
        "pimpleFoam",
        "./Allrun",
        "./Allclean",
        "decomposePar",
        "reconstructPar",
        "foamToVTK",
        "paraFoam",
        "myScript",
        "script-with-dashes",
        "script_with_underscores"
    ]
    
    for cmd in safe_commands:
        assert is_safe_command(cmd), f"Command '{cmd}' should be safe"
    
    # Unsafe commands
    unsafe_commands = [
        "blockMesh; rm -rf /",
        "simpleFoam &",
        "pimpleFoam|cat /etc/passwd",
        "decomposePar`whoami`",
        "reconstructPar$(ls)",
        "foamToVTK > /tmp/output",
        "paraFoam < input.txt",
        "blockMesh && echo 'hacked'",
        "simpleFoam || echo 'fail'",
        "../etc/passwd",
        "blockMesh\"; rm -rf /",
        "simpleFoam'; drop table users; --",
        "very_long_command_name_that_exceeds_the_maximum_allowed_length_for_security_reasons_and_should_be_rejected"
    ]
    
    for cmd in unsafe_commands:
        assert not is_safe_command(cmd), f"Command '{cmd}' should be unsafe"
    
    # Edge cases
    assert not is_safe_command(""), "Empty string should be unsafe"
    assert not is_safe_command(None), "None should be unsafe"
    assert not is_safe_command(123), "Non-string should be unsafe"
    
    print("✅ All is_safe_command tests passed!")


def test_is_safe_script_name():
    """Test safe script name validation."""
    
    # Safe script names
    safe_names = [
        "Allrun",
        "Allclean", 
        "myScript",
        "script-with-dashes",
        "script_with_underscores",
        "script123",
        "myscript.sh",
        "test-file.py"
    ]
    
    for name in safe_names:
        assert is_safe_script_name(name), f"Script name '{name}' should be safe"
    
    # Unsafe script names
    unsafe_names = [
        "../etc/passwd",
        "script; rm -rf /",
        "script|cat /etc/passwd",
        "script`whoami`",
        "script$(ls)",
        ".hidden",
        "script with spaces",
        "script/with/slashes",
        "script\\with\\backslashes",
        "very_long_script_name_that_exceeds_the_maximum_allowed_length_for_security_reasons_and_should_be_rejected"
    ]
    
    for name in unsafe_names:
        assert not is_safe_script_name(name), f"Script name '{name}' should be unsafe"
    
    # Edge cases
    assert not is_safe_script_name(""), "Empty string should be unsafe"
    assert not is_safe_script_name(None), "None should be unsafe"
    assert not is_safe_script_name(123), "Non-string should be unsafe"
    
    print("✅ All is_safe_script_name tests passed!")


def test_wrapper_script_security():
    """Test that wrapper scripts are constructed safely."""
    
    # Test safe command wrapper creation
    from app import is_safe_command, is_safe_script_name
    
    safe_command = "blockMesh"
    assert is_safe_command(safe_command)
    
    safe_script = "./Allrun"
    assert is_safe_command(safe_script)
    script_name = safe_script[2:]  # Remove "./"
    assert is_safe_script_name(script_name)
    
    # Test that wrapper script construction doesn't introduce vulnerabilities
    # This is a basic test - the real security comes from the validation functions
    bashrc = "/opt/openfoam12/etc/bashrc"
    container_case_path = "/home/foam/OpenFOAM/12/run/incompressible/simpleFoam/airFoil2D"
    
    # Test script wrapper construction
    wrapper_script = "#!/bin/bash\n"
    wrapper_script += "source " + bashrc + "\n"
    wrapper_script += "cd " + container_case_path + "\n"
    wrapper_script += safe_command + "\n"
    
    # Verify no shell metacharacters are introduced
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'"]
    for char in dangerous_chars:
        assert char not in wrapper_script, f"Dangerous character '{char}' found in wrapper script"
    
    print("✅ All wrapper script security tests passed!")


if __name__ == "__main__":
    test_is_safe_command()
    test_is_safe_script_name()
    test_wrapper_script_security()
    print("🌟 All security tests passed!")
