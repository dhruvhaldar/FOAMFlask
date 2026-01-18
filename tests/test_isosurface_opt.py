
import unittest
import pyvista as pv
from backend.post.isosurface import IsosurfaceVisualizer

class TestIsosurfaceOptimization(unittest.TestCase):
    def test_decimate_mesh_optimization(self):
        viz = IsosurfaceVisualizer()

        # Create a mesh that needs decimation
        # Sphere with high resolution
        mesh = pv.Sphere(radius=1.0, theta_resolution=100, phi_resolution=100)
        original_cells = mesh.n_cells
        target_faces = 5000

        # Ensure it's large enough to trigger decimation
        self.assertGreater(original_cells, target_faces)

        # Apply decimation
        decimated_mesh = viz._decimate_mesh(mesh, target_faces=target_faces)

        # Check that decimation happened
        self.assertLess(decimated_mesh.n_cells, original_cells)
        # Check that it's close to target (it won't be exact)
        # decimate_pro usually gets close.
        self.assertLess(decimated_mesh.n_cells, target_faces * 1.5)

        print(f"Decimated from {original_cells} to {decimated_mesh.n_cells} cells")

if __name__ == '__main__':
    unittest.main()
