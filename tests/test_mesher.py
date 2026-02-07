import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
from io import BytesIO

import pytest
import numpy as np
import pyvista as pv
import logging

from backend.mesh.mesher import MeshVisualizer


@pytest.fixture
def visualizer():
    """Create a fresh MeshVisualizer instance for each test."""
    viz = MeshVisualizer()
    yield viz
    # Cleanup
    if viz.plotter is not None:
        viz.plotter.close()


@pytest.fixture
def sample_mesh():
    """Create a simple sample mesh for testing."""
    mesh = pv.Sphere()
    mesh.point_data["field1"] = np.random.rand(mesh.n_points)
    mesh.cell_data["cell_field"] = np.random.rand(mesh.n_cells)
    return mesh


@pytest.fixture
def temp_vtk_file(sample_mesh):
    """Create a temporary VTK file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as tmp:
        tmp_path = tmp.name
    sample_mesh.save(tmp_path)
    yield tmp_path
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
def temp_vtp_file(sample_mesh):
    """Create a temporary VTP file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".vtp", delete=False) as tmp:
        tmp_path = tmp.name
    sample_mesh.save(tmp_path)
    yield tmp_path
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


class TestMeshVisualizerInit:
    """Test MeshVisualizer initialization and cleanup."""

    def test_init(self):
        """Test initialization of MeshVisualizer."""
        viz = MeshVisualizer()
        assert viz.mesh is None
        assert viz.plotter is None

    def test_del_with_plotter(self, visualizer):
        """Test cleanup when plotter exists."""
        visualizer.plotter = MagicMock()
        del visualizer
        # Should not raise any exceptions

    def test_del_without_plotter(self, visualizer):
        """Test cleanup when plotter doesn't exist."""
        del visualizer
        # Should not raise any exceptions


class TestLoadMesh:
    """Test load_mesh method."""

    def test_load_mesh_success_vtk(self, visualizer, temp_vtk_file):
        """Test successful mesh loading from VTK file."""
        result = visualizer.load_mesh(temp_vtk_file)
        assert result["success"] is True
        assert result["n_points"] > 0
        assert result["n_cells"] > 0
        assert "bounds" in result
        assert "center" in result
        assert "length" in result
        assert visualizer.mesh is not None

    def test_load_mesh_success_vtp(self, visualizer, temp_vtp_file):
        """Test successful mesh loading from VTP file."""
        result = visualizer.load_mesh(temp_vtp_file)
        assert result["success"] is True
        assert visualizer.mesh is not None

    def test_load_mesh_file_not_found(self, visualizer):
        """Test loading non-existent file."""
        result = visualizer.load_mesh("/nonexistent/file.vtk")
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"]

    def test_load_mesh_array_names(self, visualizer, temp_vtk_file):
        """Test that array names are correctly reported."""
        result = visualizer.load_mesh(temp_vtk_file)
        assert "array_names" in result
        assert "point_arrays" in result
        assert "cell_arrays" in result
        assert isinstance(result["point_arrays"], list)
        assert isinstance(result["cell_arrays"], list)

    def test_load_mesh_for_contour_flag(self, visualizer, temp_vtk_file):
        """Test load_mesh with for_contour flag."""
        result = visualizer.load_mesh(temp_vtk_file, for_contour=True)
        assert result["success"] is True

    def test_load_mesh_with_kwargs(self, visualizer, temp_vtk_file):
        """Test load_mesh with additional kwargs."""
        result = visualizer.load_mesh(temp_vtk_file, extra_param="value")
        assert result["success"] is True

    def test_load_mesh_volume(self, visualizer, temp_vtk_file):
        """Test that volume is included in mesh info."""
        result = visualizer.load_mesh(temp_vtk_file)
        assert "volume" in result


class TestGetMeshScreenshot:
    """Test get_mesh_screenshot method."""

    def test_get_mesh_screenshot_success(self, visualizer, temp_vtk_file, mocker):
        """Test successful screenshot generation."""
        # Mock PIL.Image
        mock_image = MagicMock()
        mock_save = MagicMock()
        mock_image.save = mock_save
        
        # Patch PIL.Image where it's actually used (in backend.mesh.mesher)
        mocker.patch('PIL.Image.fromarray', return_value=mock_image)
        mocker.patch('base64.b64encode', return_value=b'base64string')
        
        # Mock pyvista Plotter
        mock_plotter = MagicMock()
        mock_plotter.screenshot.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_mesh_screenshot(temp_vtk_file)
        
        assert result is not None
        assert isinstance(result, str)
        mock_plotter.add_mesh.assert_called_once()
        mock_plotter.add_axes.assert_called_once()

    def test_get_mesh_screenshot_custom_dimensions(self, visualizer, temp_vtk_file, mocker):
        """Test screenshot with custom width and height."""
        mock_image = MagicMock()
        mocker.patch('PIL.Image.fromarray', return_value=mock_image)
        mocker.patch('base64.b64encode', return_value=b'base64string')
        
        mock_plotter = MagicMock()
        mock_plotter.screenshot.return_value = np.zeros((400, 1024, 3), dtype=np.uint8)
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_mesh_screenshot(temp_vtk_file, width=1024, height=400)
        
        assert result is not None

    def test_get_mesh_screenshot_camera_positions(self, visualizer, temp_vtk_file, mocker):
        """Test screenshot with different camera positions."""
        mock_image = MagicMock()
        mocker.patch('PIL.Image.fromarray', return_value=mock_image)
        mocker.patch('base64.b64encode', return_value=b'base64string')
        
        mock_plotter = MagicMock()
        mock_plotter.screenshot.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        visualizer.load_mesh(temp_vtk_file)
        
        # Test each camera position
        for cam_pos in ["xy", "xz", "yz", "iso"]:
            result = visualizer.get_mesh_screenshot(
                temp_vtk_file, camera_position=cam_pos
            )
            assert result is not None

    def test_get_mesh_screenshot_show_edges(self, visualizer, temp_vtk_file, mocker):
        """Test screenshot with and without edges."""
        mock_image = MagicMock()
        mocker.patch('PIL.Image.fromarray', return_value=mock_image)
        mocker.patch('base64.b64encode', return_value=b'base64string')
        
        mock_plotter = MagicMock()
        mock_plotter.screenshot.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_mesh_screenshot(temp_vtk_file, show_edges=False)
        
        assert result is not None
        call_kwargs = mock_plotter.add_mesh.call_args[1]
        assert call_kwargs["show_edges"] is False


    def test_get_mesh_screenshot_custom_color(self, visualizer, temp_vtk_file, mocker):
        """Test screenshot with custom color."""
        mock_image = MagicMock()
        mocker.patch('PIL.Image.fromarray', return_value=mock_image)
        mocker.patch('base64.b64encode', return_value=b'base64string')
        
        mock_plotter = MagicMock()
        mock_plotter.screenshot.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_mesh_screenshot(temp_vtk_file, color="red")
        
        assert result is not None
        call_kwargs = mock_plotter.add_mesh.call_args[1]
        assert call_kwargs["color"] == "red"

    def test_get_mesh_screenshot_file_not_found(self, visualizer):
        """Test screenshot with non-existent file."""
        result = visualizer.get_mesh_screenshot("/nonexistent/file.vtk")
        assert result is None

    def test_get_mesh_screenshot_exception(self, visualizer, temp_vtk_file, mocker):
        """Test screenshot generation with exception."""
        mocker.patch('pyvista.Plotter', side_effect=Exception("Plotter error"))
        result = visualizer.get_mesh_screenshot(temp_vtk_file)
        assert result is None


class TestGetInteractiveViewerHtml:
    """Test get_interactive_viewer_html method."""

    def test_get_interactive_viewer_html_success(self, visualizer, temp_vtk_file, mocker):
        """Test successful interactive viewer HTML generation."""
        mock_plotter = MagicMock()
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        fake_html = "<html><body>Interactive Viewer</body></html>"
        
        # We need to mock NamedTemporaryFile context manager
        mock_tmp_file = MagicMock()
        mock_tmp_file.name = "/tmp/fake.html"
        mock_named_temp = MagicMock()
        mock_named_temp.__enter__.return_value = mock_tmp_file
        
        mocker.patch('tempfile.NamedTemporaryFile', return_value=mock_named_temp)
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('os.path.getsize', return_value=100) # Ensure it's not empty

        # Mock builtins.open
        with patch('builtins.open', mock_open(read_data=fake_html)):
            visualizer.load_mesh(temp_vtk_file)
            result = visualizer.get_interactive_viewer_html(temp_vtk_file)

        assert result == fake_html
        mock_plotter.add_mesh.assert_called_once()
        mock_plotter.show_axes.assert_called_once()

    def test_get_interactive_viewer_html_file_not_found(self, visualizer):
        """Test interactive viewer with non-existent file."""
        result = visualizer.get_interactive_viewer_html("/nonexistent/file.vtk")
        assert result is None

    def test_get_interactive_viewer_html_smooth_shading(self, visualizer, temp_vtk_file, mocker):
        """Test interactive viewer with smooth shading."""
        mock_plotter = MagicMock()
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        fake_html = "<html>Test</html>"
        
        # Mock NamedTemporaryFile
        mock_tmp_file = MagicMock()
        mock_tmp_file.name = "/tmp/fake.html"
        mock_named_temp = MagicMock()
        mock_named_temp.__enter__.return_value = mock_tmp_file
        mocker.patch('tempfile.NamedTemporaryFile', return_value=mock_named_temp)
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('os.path.getsize', return_value=100)

        with patch('builtins.open', mock_open(read_data=fake_html)):
            visualizer.load_mesh(temp_vtk_file)
            result = visualizer.get_interactive_viewer_html(temp_vtk_file)
        
        assert result is not None
        call_kwargs = mock_plotter.add_mesh.call_args[1]
        assert call_kwargs["smooth_shading"] is True

    def test_get_interactive_viewer_html_export_failure(self, visualizer, temp_vtk_file, mocker):
        """Test interactive viewer when export fails."""
        mock_plotter = MagicMock()
        mock_plotter.export_html.side_effect = Exception("Export failed")
        mock_plotter.close = MagicMock()
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_interactive_viewer_html(temp_vtk_file)
        
        assert result is None
        mock_plotter.close.assert_called()

    def test_get_interactive_viewer_html_exception(self, visualizer, temp_vtk_file, mocker):
        """Test interactive viewer with general exception."""
        mocker.patch('pyvista.Plotter', side_effect=Exception("Plotter error"))
        result = visualizer.get_interactive_viewer_html(temp_vtk_file)
        assert result is None

    def test_get_interactive_viewer_html_unlink_failure(self, visualizer, temp_vtk_file, mocker):
        """Test that unlink failures don't break the function."""
        mock_plotter = MagicMock()
        mocker.patch('pyvista.Plotter', return_value=mock_plotter)
        
        fake_html = "<html>Test</html>"
        
        mock_tmp_file = MagicMock()
        mock_tmp_file.name = "/tmp/fake.html"
        mock_named_temp = MagicMock()
        mock_named_temp.__enter__.return_value = mock_tmp_file
        mocker.patch('tempfile.NamedTemporaryFile', return_value=mock_named_temp)
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('os.path.getsize', return_value=100)

        # Patch os.remove to raise an exception
        with patch('builtins.open', mock_open(read_data=fake_html)), \
             patch('os.remove', side_effect=OSError("Unlink failed")):

            visualizer.load_mesh(temp_vtk_file)
            result = visualizer.get_interactive_viewer_html(temp_vtk_file)
        
        # Should still return HTML despite unlink failure
        assert result is not None


class TestGetAvailableMeshes:
    """Test get_available_meshes method."""

    def test_get_available_meshes_success(self, visualizer, tmp_path):
        """Test successful retrieval of available meshes."""
        # Create test directory structure
        case_dir = tmp_path / "case"
        tutorial_dir = case_dir / "tutorial1"
        tutorial_dir.mkdir(parents=True)
        
        # Create test mesh files ONLY in tutorial root (not in subdirs)
        mesh_file1 = tutorial_dir / "mesh1.vtk"
        mesh_file1.write_text("dummy")
        
        mesh_file2 = tutorial_dir / "mesh2.vtp"
        mesh_file2.write_text("dummy")
        
        result = visualizer.get_available_meshes(str(case_dir), "tutorial1")
        
        assert isinstance(result, list)
        assert len(result) >= 2  # At least 2 files found
        mesh_names = [item["name"] for item in result]
        assert "mesh1.vtk" in mesh_names
        assert "mesh2.vtp" in mesh_names
        assert all("name" in item for item in result)
        assert all("path" in item for item in result)
        assert all("relative_path" in item for item in result)
        # assert all("size" in item for item in result) # Optimized out

    def test_get_available_meshes_vtu_files(self, visualizer, tmp_path):
        """Test that .vtu files are also found."""
        case_dir = tmp_path / "case"
        tutorial_dir = case_dir / "tutorial1"
        tutorial_dir.mkdir(parents=True)
        
        mesh_file = tutorial_dir / "mesh.vtu"
        mesh_file.write_text("dummy")
        
        result = visualizer.get_available_meshes(str(case_dir), "tutorial1")
        
        assert len(result) == 1
        assert result[0]["name"] == "mesh.vtu"

    def test_get_available_meshes_postprocessing_dir(self, visualizer, tmp_path):
        """Test that postProcessing directory is searched."""
        case_dir = tmp_path / "case"
        tutorial_dir = case_dir / "tutorial1"
        postproc_dir = tutorial_dir / "postProcessing"
        postproc_dir.mkdir(parents=True)
        
        mesh_file = postproc_dir / "mesh.vtk"
        mesh_file.write_text("dummy")
        
        result = visualizer.get_available_meshes(str(case_dir), "tutorial1")
        
        mesh_names = [item["name"] for item in result]
        assert "mesh.vtk" in mesh_names

    def test_get_available_meshes_vtk_dir(self, visualizer, tmp_path):
        """Test that VTK directory is searched."""
        case_dir = tmp_path / "case"
        tutorial_dir = case_dir / "tutorial1"
        vtk_dir = tutorial_dir / "VTK"
        vtk_dir.mkdir(parents=True)
        
        mesh_file = vtk_dir / "mesh.vtk"
        mesh_file.write_text("dummy")
        
        result = visualizer.get_available_meshes(str(case_dir), "tutorial1")
        
        mesh_names = [item["name"] for item in result]
        assert "mesh.vtk" in mesh_names

    def test_get_available_meshes_nonexistent_tutorial(self, visualizer, tmp_path):
        """Test with non-existent tutorial directory."""
        result = visualizer.get_available_meshes(str(tmp_path), "nonexistent")
        
        assert result == []

    def test_get_available_meshes_empty_directory(self, visualizer, tmp_path):
        """Test with empty tutorial directory."""
        case_dir = tmp_path / "case"
        tutorial_dir = case_dir / "tutorial1"
        tutorial_dir.mkdir(parents=True)
        
        result = visualizer.get_available_meshes(str(case_dir), "tutorial1")
        
        assert result == []

    def test_get_available_meshes_ignores_other_files(self, visualizer, tmp_path):
        """Test that non-mesh files are ignored."""
        case_dir = tmp_path / "case"
        tutorial_dir = case_dir / "tutorial1"
        tutorial_dir.mkdir(parents=True)
        
        # Create various files
        (tutorial_dir / "mesh.vtk").write_text("dummy")
        (tutorial_dir / "data.txt").write_text("dummy")
        (tutorial_dir / "readme.md").write_text("dummy")
        
        result = visualizer.get_available_meshes(str(case_dir), "tutorial1")
        
        assert len(result) == 1
        assert result[0]["name"] == "mesh.vtk"

    def test_get_available_meshes_nested_directories(self, visualizer, tmp_path):
        """Test finding meshes in nested subdirectories."""
        case_dir = tmp_path / "case"
        tutorial_dir = case_dir / "tutorial1"
        nested_dir = tutorial_dir / "subdir" / "nested"
        nested_dir.mkdir(parents=True)
        
        (nested_dir / "mesh.vtk").write_text("dummy")
        
        result = visualizer.get_available_meshes(str(case_dir), "tutorial1")
        
        assert len(result) >= 1

    def test_get_available_meshes_exception_returns_empty_list(self, visualizer, mocker):
        """Test that exception in os.walk is handled gracefully."""
        # In the new Path implementation, we use rglob which calls os.scandir/os.walk internally
        # We'll mock Path.rglob or iterdir to raise an exception
        
        with patch('pathlib.Path.rglob', side_effect=OSError("Walk error")):
            result = visualizer.get_available_meshes("/path", "tutorial")

            # Should return empty list on exception
            assert isinstance(result, list)
            assert result == []


class TestGlobalInstance:
    """Test global instance creation."""

    def test_global_instance_exists(self):
        """Test that global mesh_visualizer instance exists."""
        # Import from the correct module where it's defined
        from backend.mesh.mesher import mesh_visualizer
        assert isinstance(mesh_visualizer, MeshVisualizer)
