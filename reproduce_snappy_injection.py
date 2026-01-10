
import os
import shutil
from pathlib import Path
from backend.meshing.snappyhexmesh import SnappyHexMeshGenerator

def reproduce():
    # Setup
    test_dir = Path("test_injection_reproduction")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()

    system_dir = test_dir / "system"
    system_dir.mkdir()

    # Malicious payload in location_in_mesh
    # We attempt to close the vector parenthesis and inject a codeStream or include
    payload = '10); #codeStream { code #{ os.system("echo PWNED > pwned.txt"); #} }; ('

    config = {
        "global_settings": {
            "castellated_mesh": True
        },
        "objects": [],
        "location_in_mesh": [0, 0, payload]
    }

    print(f"Attempting injection with payload: {payload}")

    # Generate
    success = SnappyHexMeshGenerator.generate_dict(test_dir, config)

    if not success:
        print("Generation failed.")
        return

    # Check content
    dict_path = system_dir / "snappyHexMeshDict"
    content = dict_path.read_text()

    print("-" * 20)
    print("Generated snappyHexMeshDict content (snippet):")
    # Show the locationInMesh line
    for line in content.splitlines():
        if "locationInMesh" in line:
            print(line)
    print("-" * 20)

    if 'echo PWNED' in content:
        print("VULNERABILITY CONFIRMED: Payload injected into snappyHexMeshDict.")
    else:
        print("Injection failed.")

    # Cleanup
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    reproduce()
