
import os
import time
import pytest
import pyvista as pv
import numpy as np
from pathlib import Path
import tempfile
from backend.mesh.mesher import MeshVisualizer
from backend.post.isosurface import IsosurfaceVisualizer
from backend.geometry.visualizer import GeometryVisualizer

@pytest.fixture(scope="module")
def large_vtk_file():
    """Generates a moderately large UnstructuredGrid VTK file."""
    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as tmp:
        path = tmp.name

    # Create a 50x50x50 grid (125k points, ~120k cells)
    # pv.ImageData is the new name for UniformGrid
    grid = pv.ImageData(dimensions=(50, 50, 50))
    # Convert to UnstructuredGrid to mimic OpenFOAM
    mesh = grid.cast_to_unstructured_grid()

    # Add some data
    mesh.point_data["U"] = np.random.rand(mesh.n_points, 3)
    mesh.point_data["p"] = np.random.rand(mesh.n_points)

    mesh.save(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture(scope="module")
def large_stl_file():
    """Generates a moderately large STL file."""
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        path = tmp.name

    # Create a high-res sphere
    # theta=300, phi=300 -> 90k points, 180k cells.
    sphere = pv.Sphere(theta_resolution=300, phi_resolution=300)
    sphere.save(path)

    yield path
    if os.path.exists(path):
        os.remove(path)

def test_mesh_visualizer_optimization(large_vtk_file):
    visualizer = MeshVisualizer()

    print(f"\n[MeshVisualizer] Testing with {large_vtk_file}")

    # 1. Load Time
    start = time.time()
    visualizer.load_mesh(large_vtk_file)
    load_time = time.time() - start
    print(f"[MeshVisualizer] Load time (1st): {load_time:.4f}s")

    # 2. Cache Hit Time
    start = time.time()
    visualizer.load_mesh(large_vtk_file)
    cache_time = time.time() - start
    print(f"[MeshVisualizer] Load time (2nd - Cached): {cache_time:.4f}s")

    # 3. HTML Generation Size/Time
    start = time.time()
    html = visualizer.get_interactive_viewer_html(large_vtk_file)
    gen_time = time.time() - start
    size_mb = len(html) / (1024 * 1024)
    print(f"[MeshVisualizer] HTML gen time: {gen_time:.4f}s")
    print(f"[MeshVisualizer] HTML size: {size_mb:.2f} MB")

def test_isosurface_visualizer_optimization(large_vtk_file):
    visualizer = IsosurfaceVisualizer()

    print(f"\n[IsosurfaceVisualizer] Testing with {large_vtk_file}")

    # 1. Load Time
    start = time.time()
    visualizer.load_mesh(large_vtk_file)
    load_time = time.time() - start
    print(f"[IsosurfaceVisualizer] Load time (1st): {load_time:.4f}s")

    # 2. Cache Hit Time
    start = time.time()
    visualizer.load_mesh(large_vtk_file)
    cache_time = time.time() - start
    print(f"[IsosurfaceVisualizer] Load time (2nd - Cached): {cache_time:.4f}s")

    # 3. HTML Generation
    start = time.time()
    html = visualizer.get_interactive_html(scalar_field="p", show_base_mesh=True)
    gen_time = time.time() - start
    size_mb = len(html) / (1024 * 1024)
    print(f"[IsosurfaceVisualizer] HTML gen time: {gen_time:.4f}s")
    print(f"[IsosurfaceVisualizer] HTML size: {size_mb:.2f} MB")

def test_geometry_visualizer_optimization(large_stl_file):
    visualizer = GeometryVisualizer()

    print(f"\n[GeometryVisualizer] Testing with {large_stl_file}")

    # HTML Generation
    start = time.time()
    html = visualizer.get_interactive_html(large_stl_file)
    gen_time = time.time() - start

    if html:
        size_mb = len(html) / (1024 * 1024)
        print(f"[GeometryVisualizer] HTML gen time: {gen_time:.4f}s")
        print(f"[GeometryVisualizer] HTML size: {size_mb:.2f} MB")
    else:
        print("[GeometryVisualizer] HTML generation failed")

if __name__ == "__main__":
    pytest.main([__file__])
