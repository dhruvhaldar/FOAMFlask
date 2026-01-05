
import pytest
from unittest.mock import MagicMock, patch
from backend.mesh.mesher import MeshVisualizer
import numpy as np

def test_mesh_screenshot_large_dimensions():
    """
    Test that get_mesh_screenshot rejects large dimensions.
    """
    visualizer = MeshVisualizer()
    visualizer.mesh = MagicMock()

    with patch("pyvista.Plotter") as MockPlotter:
        mock_plotter_instance = MockPlotter.return_value

        # Attempt with huge dimensions
        huge_width = 100000
        huge_height = 100000

        with patch("pathlib.Path.exists", return_value=True):
             result = visualizer.get_mesh_screenshot("dummy.vtk", width=huge_width, height=huge_height)

        # Assert that the result is None (indicating failure/rejection)
        assert result is None, "Should reject large dimensions"

        # Assert that Plotter was NOT initialized
        MockPlotter.assert_not_called()

def test_mesh_screenshot_valid_dimensions():
    """
    Test that get_mesh_screenshot accepts valid dimensions.
    """
    visualizer = MeshVisualizer()
    visualizer.mesh = MagicMock()

    with patch("pyvista.Plotter") as MockPlotter:
        mock_plotter_instance = MockPlotter.return_value

        # Mock screenshot to return a numpy array (which pyvista uses)
        # Create a dummy image array (height, width, 3)
        dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_plotter_instance.screenshot.return_value = dummy_img

        # Attempt with valid dimensions
        valid_width = 800
        valid_height = 600

        with patch("pathlib.Path.exists", return_value=True):
             result = visualizer.get_mesh_screenshot("dummy.vtk", width=valid_width, height=valid_height)

        # Assert that the result is NOT None
        assert result is not None

        # Assert that Plotter WAS initialized
        MockPlotter.assert_called_with(off_screen=True, window_size=[valid_width, valid_height])
