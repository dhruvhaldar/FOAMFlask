from backend.geometry.manager import GeometryManager
from backend.geometry.visualizer import GeometryVisualizer
from pathlib import Path
import logging
import sys

# Setup basic logging
logging.basicConfig(level=logging.ERROR)

case_path = Path(r"e:\Misc\FOAMFlask\run_folder\fluid\aerofoilNACA0012Steady")

print("--- Testing Listing ---")
files = GeometryManager.list_stls(case_path)
print(files)

if files['success'] and "NACA0012.obj.gz" in files['files']:
    print("Found .obj.gz file!")
    file_path = case_path / "constant" / "triSurface" / "NACA0012.obj.gz"
    
    print("\n--- Testing Info ---")
    info = GeometryVisualizer.get_mesh_info(file_path)
    print(f"Info Success: {info.get('success')}")
    if 'bounds' in info:
        print(f"Bounds: {info['bounds']}")
    
    if info['success']:
        print("Successfully read info from .obj.gz")
    else:
        print(f"Failed to read info: {info.get('error')}")

    print("\n--- Testing HTML Generation ---")
    html = GeometryVisualizer.get_interactive_html(file_path)
    if html and len(html) > 0:
        print("Successfully generated HTML")
    else:
        print("Failed to generate HTML")
else:
    print("File not found in list")
    sys.exit(1)
