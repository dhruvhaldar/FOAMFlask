import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
import numpy as np
import pyvista as pv

from backend.post.isosurface import IsosurfaceVisualizer


@pytest.fixture
def visualizer():
    """Create a fresh IsosurfaceVisualizer instance for each test."""
    return IsosurfaceVisualizer()


@pytest.fixture
def sample_mesh():
    """Create a simple sample mesh for testing."""
    mesh = pv.Sphere()
    mesh.point_data["U_Magnitude"] = np.random.rand(mesh.n_points)
    mesh.point_data["U"] = np.random.rand(mesh.n_points, 3)
    mesh.point_data["p"] = np.random.rand(mesh.n_points)
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


class TestIsosurfaceVisualizerInit:
    """Test IsosurfaceVisualizer initialization."""

    def test_init(self):
        """Test initialization of IsosurfaceVisualizer."""
        viz = IsosurfaceVisualizer()
        assert viz.mesh is None
        assert viz.contours is None
        assert viz.plotter is None


class TestLoadMesh:
    """Test load_mesh method."""

    def test_load_mesh_success(self, visualizer, temp_vtk_file):
        """Test successful mesh loading."""
        result = visualizer.load_mesh(temp_vtk_file)
        assert result["success"] is True
        assert result["n_points"] > 0
        assert result["n_cells"] > 0
        assert "point_arrays" in result
        assert visualizer.mesh is not None

    def test_load_mesh_file_not_found(self, visualizer):
        """Test loading non-existent file."""
        result = visualizer.load_mesh("/nonexistent/file.vtk")
        assert result["success"] is False
        assert "error" in result

    def test_load_mesh_computes_u_magnitude(self, visualizer, temp_vtk_file):
        """Test that U_Magnitude is computed from U field."""
        result = visualizer.load_mesh(temp_vtk_file)
        assert "U_Magnitude" in result["point_arrays"]
        assert "u_magnitude" in result
        assert "min" in result["u_magnitude"]
        assert "max" in result["u_magnitude"]
        assert "mean" in result["u_magnitude"]

    def test_load_mesh_returns_bounds(self, visualizer, temp_vtk_file):
        """Test that mesh bounds are returned."""
        result = visualizer.load_mesh(temp_vtk_file)
        assert "bounds" in result
        assert len(result["bounds"]) == 6

    def test_load_mesh_percentiles(self, visualizer, temp_vtk_file):
        """Test that percentiles are calculated for U_Magnitude."""
        result = visualizer.load_mesh(temp_vtk_file)
        percentiles = result["u_magnitude"]["percentiles"]
        assert "0" in percentiles
        assert "25" in percentiles
        assert "50" in percentiles
        assert "75" in percentiles
        assert "100" in percentiles


class TestGenerateIsosurfaces:
    """Test generate_isosurfaces method."""

    def test_generate_isosurfaces_no_mesh_loaded(self, visualizer):
        """Test error when no mesh is loaded."""
        result = visualizer.generate_isosurfaces()
        assert result["success"] is False
        assert "error" in result

    def test_generate_isosurfaces_success(self, visualizer, temp_vtk_file):
        """Test successful isosurface generation."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.generate_isosurfaces(
            scalar_field="U_Magnitude", num_isosurfaces=5
        )
        assert result["success"] is True
        assert result["num_isosurfaces"] == 5
        assert "isovalues" in result
        assert visualizer.contours is not None

    def test_generate_isosurfaces_invalid_field(self, visualizer, temp_vtk_file):
        """Test error with invalid scalar field."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.generate_isosurfaces(scalar_field="nonexistent_field")
        assert result["success"] is False
        assert "error" in result

    def test_generate_isosurfaces_with_custom_range(self, visualizer, temp_vtk_file):
        """Test isosurface generation with custom range."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.generate_isosurfaces(
            scalar_field="U_Magnitude", custom_range=[0.0, 1.0], num_isosurfaces=3
        )
        assert result["success"] is True
        assert result["num_isosurfaces"] == 3

    def test_generate_isosurfaces_with_explicit_isovalues(
        self, visualizer, temp_vtk_file
    ):
        """Test isosurface generation with explicit isovalues."""
        visualizer.load_mesh(temp_vtk_file)
        isovalues = [0.2, 0.5, 0.8]
        result = visualizer.generate_isosurfaces(
            scalar_field="U_Magnitude", isovalues=isovalues
        )
        assert result["success"] is True
        assert len(result["isovalues"]) == 3

    def test_generate_isosurfaces_invalid_range(self, visualizer, temp_vtk_file):
        """Test error with invalid custom range."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.generate_isosurfaces(
            scalar_field="U_Magnitude", custom_range=[0.0]
        )
        assert result["success"] is False


class TestGetScalarFieldInfo:
    """Test get_scalar_field_info method."""

    def test_get_scalar_field_info_no_mesh(self, visualizer):
        """Test error when no mesh is loaded."""
        result = visualizer.get_scalar_field_info()
        assert "error" in result

    def test_get_scalar_field_info_all_fields(self, visualizer, temp_vtk_file):
        """Test getting info for all scalar fields."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_scalar_field_info()
        assert "U_Magnitude" in result
        assert "p" in result

    def test_get_scalar_field_info_specific_field(self, visualizer, temp_vtk_file):
        """Test getting info for a specific scalar field."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_scalar_field_info(scalar_field="p")
        assert "p" in result
        assert result["p"]["type"] == "scalar"
        assert "min" in result["p"]
        assert "max" in result["p"]

    def test_get_scalar_field_info_vector_field(self, visualizer, temp_vtk_file):
        """Test getting info for a vector field."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_scalar_field_info(scalar_field="U")
        assert "U" in result
        assert result["U"]["type"] == "vector"
        assert "magnitude_stats" in result["U"]

    def test_get_scalar_field_info_nonexistent_field(self, visualizer, temp_vtk_file):
        """Test error with nonexistent field."""
        visualizer.load_mesh(temp_vtk_file)
        result = visualizer.get_scalar_field_info(scalar_field="nonexistent")
        assert "error" in result


class TestGetInteractiveHtml:
    """Test get_interactive_html method."""

    def test_get_interactive_html_no_mesh(self, visualizer):
        """Test error when no mesh is loaded."""
        html = visualizer.get_interactive_html()
        assert "error" in html.lower() or "visualization error" in html.lower()

    def test_get_interactive_html_invalid_field(self, visualizer, temp_vtk_file):
        """Test error with invalid scalar field."""
        visualizer.load_mesh(temp_vtk_file)
        html = visualizer.get_interactive_html(scalar_field="nonexistent_field")
        assert "error" in html.lower()

    @patch("pyvista.Plotter")
    def test_get_interactive_html_with_slider(self, mock_plotter_class, visualizer, temp_vtk_file):
        """Test HTML generation with interactive slider."""
        mock_plotter = MagicMock()
        mock_plotter_class.return_value = mock_plotter
        mock_plotter.export_html = MagicMock()

        visualizer.load_mesh(temp_vtk_file)

        with patch("builtins.open", mock_open(read_data="<html>test</html>")):
            html = visualizer.get_interactive_html(
                scalar_field="U_Magnitude", show_isovalue_slider=True
            )

        assert "html" in html.lower()
        mock_plotter.add_mesh_isovalue.assert_called_once()

    @patch("pyvista.Plotter")
    def test_get_interactive_html_without_base_mesh(self, mock_plotter_class, visualizer, temp_vtk_file):
        """Test HTML generation without base mesh."""
        mock_plotter = MagicMock()
        mock_plotter_class.return_value = mock_plotter
        mock_plotter.export_html = MagicMock()

        visualizer.load_mesh(temp_vtk_file)

        with patch("builtins.open", mock_open(read_data="<html>test</html>")):
            html = visualizer.get_interactive_html(
                scalar_field="U_Magnitude", show_base_mesh=False
            )

        assert "html" in html.lower()

    @patch("pyvista.Plotter")
    def test_get_interactive_html_custom_window_size(self, mock_plotter_class, visualizer, temp_vtk_file):
        """Test HTML generation with custom window size."""
        mock_plotter = MagicMock()
        mock_plotter_class.return_value = mock_plotter
        mock_plotter.export_html = MagicMock()

        visualizer.load_mesh(temp_vtk_file)

        with patch("builtins.open", mock_open(read_data="<html>test</html>")):
            html = visualizer.get_interactive_html(
                scalar_field="U_Magnitude", window_size=(800, 600)
            )

        mock_plotter_class.assert_called_with(notebook=False, window_size=[800, 600])


class TestExportContours:
    """Test export_contours method."""

    def test_export_contours_no_contours(self, visualizer):
        """Test error when no contours are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.vtk")
            result = visualizer.export_contours(output_path)
            assert result["success"] is False

    def test_export_contours_success(self, visualizer, temp_vtk_file):
        """Test successful contour export."""
        visualizer.load_mesh(temp_vtk_file)
        visualizer.generate_isosurfaces(scalar_field="U_Magnitude", num_isosurfaces=3)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "contours")
            result = visualizer.export_contours(output_path, file_format="vtk")
            assert result["success"] is True
            assert "file_size" in result
            assert os.path.exists(f"{output_path}.vtk")

    def test_export_contours_different_format(self, visualizer, temp_vtk_file):
        """Test contour export with different format."""
        visualizer.load_mesh(temp_vtk_file)
        visualizer.generate_isosurfaces(scalar_field="U_Magnitude", num_isosurfaces=3)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "contours")
            result = visualizer.export_contours(output_path, file_format="vtp")
            assert result["success"] is True


class TestGenerateErrorHtml:
    """Test _generate_error_html method."""

    def test_generate_error_html(self, visualizer):
        """Test error HTML generation."""
        html = visualizer._generate_error_html("Test error message", "U_Magnitude")
        assert "error" in html.lower()
        assert "visualization error" in html.lower()
        assert "test error message" in html.lower()
        assert "U_Magnitude" in html


class TestCleanup:
    """Test resource cleanup."""

    def test_del_with_plotter(self, visualizer):
        """Test cleanup when plotter exists."""
        visualizer.plotter = MagicMock()
        del visualizer
        # Should not raise any exceptions

    def test_del_without_plotter(self, visualizer):
        """Test cleanup when plotter doesn't exist."""
        del visualizer
        # Should not raise any exceptions
