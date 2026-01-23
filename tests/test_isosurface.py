import os
import tempfile
import hashlib
import json
import logging
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

import pytest
import numpy as np
import pyvista as pv
from backend.post.isosurface import IsosurfaceVisualizer, _generate_isosurface_html_process

@pytest.fixture
def visualizer():
    return IsosurfaceVisualizer()

@pytest.fixture
def sample_mesh():
    mesh = pv.Sphere()
    mesh.point_data["U_Magnitude"] = np.random.rand(mesh.n_points)
    mesh.point_data["U"] = np.random.rand(mesh.n_points, 3)
    mesh.point_data["p"] = np.random.rand(mesh.n_points)
    return mesh

@pytest.fixture
def temp_vtk_file(sample_mesh):
    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as tmp:
        tmp_path = tmp.name
    sample_mesh.save(tmp_path)
    yield tmp_path
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

class TestIsosurfaceVisualizer:
    """Test IsosurfaceVisualizer methods."""

    def test_init(self, visualizer):
        """Test initialization of IsosurfaceVisualizer."""
        assert visualizer.mesh is None
        assert visualizer.contours is None
        assert visualizer.plotter is None
        assert visualizer.current_mesh_path is None
        assert visualizer.current_mesh_mtime is None

    def test_load_mesh_success(self, visualizer, temp_vtk_file):
        """Test successful mesh loading."""
        result = visualizer.load_mesh(temp_vtk_file)
        assert result["success"] is True
        assert visualizer.mesh is not None
        assert "U_Magnitude" in visualizer.mesh.point_data
        assert visualizer.current_mesh_path == temp_vtk_file
        assert visualizer.current_mesh_mtime is not None

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

    def test_generate_error_html(self, visualizer):
        """Test error HTML generation."""
        html = visualizer._generate_error_html("Test error message", "U_Magnitude")
        assert "error" in html.lower()
        assert "visualization error" in html.lower()
        assert "test error message" in html.lower()
        assert "U_Magnitude" in html

    def test_generate_error_html_escapes_xss(self, visualizer):
        """Test that error HTML generation escapes XSS payloads."""
        payload = "<script>alert('XSS')</script>"
        html = visualizer._generate_error_html("Error occurred", payload)

        # Verify payload is present but escaped
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

        # Verify error message is also escaped
        error_payload = "<b>Bold Error</b>"
        html_error = visualizer._generate_error_html(error_payload, "field")
        assert "&lt;b&gt;" in html_error
        assert "<b>" not in html_error

    def test_get_interactive_html_caching_and_process(self, visualizer, temp_vtk_file, mocker):
        """Test that get_interactive_html uses caching and subprocess."""
        visualizer.load_mesh(temp_vtk_file)
        
        # Mock caching internals
        mocker.patch('backend.post.isosurface._get_cache_dir', return_value=Path(tempfile.gettempdir()))
        mocker.patch('backend.post.isosurface._cleanup_cache')
        
        # Mock multiprocessing
        mock_process = mocker.MagicMock()
        mock_process_cls = mocker.patch('multiprocessing.Process', return_value=mock_process)
        mock_process.exitcode = 0
        # Configure is_alive to return False (process finished)
        mock_process.is_alive.return_value = False
        
        # Mock file writing by subprocess (since we don't run it for real here)
        # We need to ensure the temp file exists and has content so the visualizer picks it up
        html_content = "<html>Process Output</html>"
        
        # This is tricky because the temp file path is generated inside the method
        # We can mock NamedTemporaryFile to return a known path
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            known_temp_path = tmp.name
            with open(known_temp_path, 'w', encoding="utf-8") as f:
                f.write(html_content)

        mock_temp_file = mocker.MagicMock()
        mock_temp_file.__enter__.return_value.name = known_temp_path
        mocker.patch('tempfile.NamedTemporaryFile', return_value=mock_temp_file)
        
        # Call the method
        html = visualizer.get_interactive_html(scalar_field="U_Magnitude")
        
        # Verification
        assert html == html_content
        mock_process_cls.assert_called_once()
        mock_process.start.assert_called_once()
        mock_process.join.assert_called_once()
        
        # Verify arguments passed to subprocess
        args = mock_process_cls.call_args[1]['args']
        assert args[0] == str(Path(temp_vtk_file).resolve())
        # args[1] is output path
        # args[2] is params dict
        assert args[2]['scalar_field'] == "U_Magnitude"

        # Cleanup known temp path if it still exists (shutil.move might have moved it)
        if os.path.exists(known_temp_path):
            os.remove(known_temp_path)

    def test_subprocess_logic(self, temp_vtk_file):
        """Test the logic inside the subprocess function."""
        # We run the helper function directly in this test process
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            output_path = tmp.name

        params = {
            "scalar_field": "U_Magnitude",
            "show_base_mesh": True,
            "show_isovalue_slider": False,
            "num_isosurfaces": 2
        }
        
        _generate_isosurface_html_process(temp_vtk_file, output_path, params)
        
        assert os.path.exists(output_path)
        
        # Open with utf-8 encoding as specified in the source
        with open(output_path, 'r', encoding="utf-8") as f:
            content = f.read()
            assert "html" in content.lower()

        if os.path.exists(output_path):
            os.remove(output_path)
