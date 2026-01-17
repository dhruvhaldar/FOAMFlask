import os
import time
import shutil
import tempfile
import threading
import requests
import pytest
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import numpy as np
from stl import mesh

# Add current directory to path
sys.path.append(os.getcwd())

# Import the real app
from app import app, CASE_ROOT, STARTUP_STATUS

# Setup a temporary case directory
TEMP_CASE_ROOT = Path(tempfile.mkdtemp(prefix="foamflask_benchmark_"))

# Configuration for benchmark
PORT = 5050
BASE_URL = f"http://127.0.0.1:{PORT}"

def generate_large_stl(filename, num_triangles=50000):
    """Generates a large random STL file for benchmarking."""
    print(f"Generating STL with {num_triangles} triangles...")
    # Define the 8 vertices of a cube
    data = np.zeros(num_triangles, dtype=mesh.Mesh.dtype)

    # Generate random triangles
    for i in range(num_triangles):
        data['vectors'][i] = np.random.rand(3, 3) * 100

    m = mesh.Mesh(data)
    m.save(filename)
    print(f"STL generated: {filename} ({os.path.getsize(filename)/1024/1024:.2f} MB)")

def run_app():
    """Runs the Flask app in a separate thread."""
    # Override global configuration for the test
    app.config['TESTING'] = True
    app.config['ENABLE_CSRF'] = False  # Disable CSRF for benchmark

    # Patch the global CASE_ROOT in app.py
    import app as app_module
    app_module.CASE_ROOT = str(TEMP_CASE_ROOT)

    # Mock startup check
    def mock_startup():
        app_module.STARTUP_STATUS["status"] = "success"
        app_module.STARTUP_STATUS["message"] = "Benchmark Ready"

    app_module.run_startup_check = mock_startup

    app.run(port=PORT, use_reloader=False)

@pytest.fixture(scope="module")
def benchmark_app():
    """Fixture to start/stop the app and clean up."""
    # Create a dummy case structure
    case_dir = TEMP_CASE_ROOT / "benchmark_case"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)

    # Generate large STL
    stl_path = case_dir / "constant" / "triSurface" / "large_model.stl"
    generate_large_stl(stl_path, num_triangles=100000) # ~5MB

    # Start app thread
    t = threading.Thread(target=run_app, daemon=True)
    t.start()

    # Wait for app to be ready
    for _ in range(10):
        try:
            requests.get(BASE_URL)
            break
        except requests.ConnectionError:
            time.sleep(1)

    yield

    # Cleanup
    shutil.rmtree(TEMP_CASE_ROOT)

def test_geometry_benchmark(benchmark_app):
    """
    Playwright test to benchmark geometry visualization speedup.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("\n--- Starting Benchmark ---")

        # Benchmark API Response Time directly
        # This bypasses UI issues but uses the real browser context

        # Set the case root explicitly via API to ensure it's correct
        page.request.post(f"{BASE_URL}/set_case", data={"caseDir": str(TEMP_CASE_ROOT)})

        # Payload for view
        payload = {
            "caseName": "benchmark_case",
            "filename": "large_model.stl",
            "color": "lightblue",
            "opacity": 1.0
        }

        # First Request (Uncached)
        print("Sending request 1 (Uncached)...")
        t0 = time.time()
        response1 = page.request.post(f"{BASE_URL}/api/geometry/view", data=payload)
        t1 = time.time()
        duration_uncached = t1 - t0
        print(f"Uncached Time: {duration_uncached:.4f}s")

        assert response1.ok, f"First request failed: {response1.status} {response1.status_text}"
        assert len(response1.body()) > 0

        # Second Request (Cached)
        print("Sending request 2 (Cached)...")
        t2 = time.time()
        response2 = page.request.post(f"{BASE_URL}/api/geometry/view", data=payload)
        t3 = time.time()
        duration_cached = t3 - t2
        print(f"Cached Time:   {duration_cached:.4f}s")

        assert response2.ok, f"Second request failed: {response2.status}"

        # Calculate Speedup
        speedup = duration_uncached / duration_cached if duration_cached > 0 else 999
        print(f"Speedup:       {speedup:.2f}x")

        # Assertions
        assert duration_cached < 1.0, "Cached response should be sub-second"
        assert speedup > 2.0, "Speedup should be significant (>2x)"

        print("--- Benchmark Complete ---")

if __name__ == "__main__":
    pytest.main([__file__])
