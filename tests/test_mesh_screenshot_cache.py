
import pytest
import tempfile
import os
import time
import pyvista as pv
from pathlib import Path
from backend.mesh.mesher import MeshVisualizer

@pytest.fixture
def temp_mesh_file():
    mesh = pv.Sphere()
    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as tmp:
        filename = tmp.name
        mesh.save(filename)
    yield filename
    if os.path.exists(filename):
        os.remove(filename)

def test_screenshot_caching(temp_mesh_file):
    visualizer = MeshVisualizer()

    # 1. First call - Miss
    start = time.time()
    img1 = visualizer.get_mesh_screenshot(temp_mesh_file, width=200, height=200)
    duration1 = time.time() - start
    assert img1 is not None
    assert len(visualizer._screenshot_cache) == 1

    # 2. Second call - Hit
    start = time.time()
    img2 = visualizer.get_mesh_screenshot(temp_mesh_file, width=200, height=200)
    duration2 = time.time() - start
    assert img2 == img1

    # Check timings (cache should be much faster)
    print(f"Duration1: {duration1}, Duration2: {duration2}")

    # 3. Different parameters - Miss
    img3 = visualizer.get_mesh_screenshot(temp_mesh_file, width=300, height=300)
    assert img3 != img1
    assert len(visualizer._screenshot_cache) == 2

    # 4. Modify file - Miss
    time.sleep(1.1)
    Path(temp_mesh_file).touch()

    img4 = visualizer.get_mesh_screenshot(temp_mesh_file, width=200, height=200)
    assert len(visualizer._screenshot_cache) == 3
    assert img4 is not None

def test_cache_lru(temp_mesh_file):
    visualizer = MeshVisualizer()
    visualizer._screenshot_cache_max_size = 2

    visualizer.get_mesh_screenshot(temp_mesh_file, width=100, height=100)
    visualizer.get_mesh_screenshot(temp_mesh_file, width=101, height=100)
    visualizer.get_mesh_screenshot(temp_mesh_file, width=102, height=100)

    assert len(visualizer._screenshot_cache) == 2
    # Check widths in keys (index 2)
    keys = [k[2] for k in visualizer._screenshot_cache.keys()]
    assert 100 not in keys
    assert 101 in keys
    assert 102 in keys

def test_cache_unhashable_args(temp_mesh_file):
    """Test that lists (unhashable) in arguments don't crash the cache."""
    visualizer = MeshVisualizer()

    # Pass color as list [R, G, B]
    color = [1.0, 0.0, 0.0]

    # This should succeed and return a string, not None
    result = visualizer.get_mesh_screenshot(temp_mesh_file, color=color)
    assert result is not None, "get_mesh_screenshot failed (returned None), possibly due to TypeError in cache key"

    # Ensure it's cached (it should be cached if successful)
    assert len(visualizer._screenshot_cache) == 1
