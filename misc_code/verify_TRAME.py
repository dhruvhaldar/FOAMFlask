import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

from backend.post.isosurface import IsosurfaceVisualizer

print("Checking IsosurfaceVisualizer...")
if hasattr(IsosurfaceVisualizer, 'start_trame_visualization'):
    print("SUCCESS: start_trame_visualization exists on class")
else:
    print("FAILURE: start_trame_visualization is MISSING from class")

viz = IsosurfaceVisualizer()
if hasattr(viz, 'start_trame_visualization'):
    print("SUCCESS: start_trame_visualization exists on instance")
else:
    print("FAILURE: start_trame_visualization is MISSING from instance")
