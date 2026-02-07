import pytest
from unittest.mock import MagicMock, patch
import pyvista as pv
from backend.mesh.mesher import MeshVisualizer
import os

@pytest.fixture
def mesh_visualizer():
    return MeshVisualizer()

@pytest.fixture
def mock_mesh():
    mesh = MagicMock(spec=pv.PolyData)
    mesh.n_points = 1000
    mesh.n_cells = 500000
    mesh.bounds = [0, 1, 0, 1, 0, 1]
    mesh.center = [0.5, 0.5, 0.5]
    mesh.length = 1.0
    mesh.point_data = {}
    mesh.cell_data = {}
    mesh.array_names = []
    return mesh

@patch('backend.mesh.mesher.BaseVisualizer.validate_file')
@patch('backend.mesh.mesher.BaseVisualizer.load_mesh_safe')
def test_interactive_viewer_caching(mock_load_mesh_safe, mock_validate_file, mesh_visualizer, mock_mesh):
    # Setup mocks
    file_path = "dummy.vtk"
    mock_validate_file.return_value = MagicMock()
    mock_validate_file.return_value.__str__.return_value = file_path
    mock_validate_file.return_value.stat.return_value.st_mtime = 123456.0

    mock_load_mesh_safe.return_value = mock_mesh

    # Mock decimate_mesh on the instance directly
    decimated_mesh = MagicMock(spec=pv.PolyData)
    decimated_mesh.n_cells = 200000
    mesh_visualizer.decimate_mesh = MagicMock(return_value=decimated_mesh)

    # Mock generate_html_content on the instance directly
    mesh_visualizer.generate_html_content = MagicMock(return_value="<html></html>")

    # 1. First call: Should load mesh, decimate, and generate HTML
    html1 = mesh_visualizer.get_interactive_viewer_html(file_path, show_edges=True, color="blue")

    assert html1 == "<html></html>"
    mock_load_mesh_safe.assert_called_once()
    mesh_visualizer.decimate_mesh.assert_called_once()
    mesh_visualizer.generate_html_content.assert_called_once()

    # Reset mocks to verify caching
    mock_load_mesh_safe.reset_mock()
    mesh_visualizer.decimate_mesh.reset_mock()
    mesh_visualizer.generate_html_content.reset_mock()

    # 2. Second call (same params): Should use HTML cache
    html2 = mesh_visualizer.get_interactive_viewer_html(file_path, show_edges=True, color="blue")

    assert html2 == "<html></html>"
    # load_mesh_safe NOT called because load_mesh checks cache and mtime matches
    mock_load_mesh_safe.assert_not_called()
    # decimate_mesh NOT called because HTML cache hit
    mesh_visualizer.decimate_mesh.assert_not_called()
    mesh_visualizer.generate_html_content.assert_not_called()

    # 3. Third call (different color): Should reuse decimated mesh but regenerate HTML
    html3 = mesh_visualizer.get_interactive_viewer_html(file_path, show_edges=True, color="red")

    assert html3 == "<html></html>"

    mesh_visualizer.decimate_mesh.assert_not_called() # Should use cached decimated mesh
    mesh_visualizer.generate_html_content.assert_called_once() # Should regenerate HTML

    # Verify cache clearing on new mesh
    # Change mtime to simulate new file content
    mock_validate_file.return_value.stat.return_value.st_mtime = 123457.0

    # Reset again
    mesh_visualizer.decimate_mesh.reset_mock()
    mesh_visualizer.generate_html_content.reset_mock()

    html4 = mesh_visualizer.get_interactive_viewer_html(file_path, show_edges=True, color="blue")

    # Should reload mesh (load_mesh_safe called), clear caches, decimate again
    mock_load_mesh_safe.assert_called_once()
    assert mesh_visualizer.decimate_mesh.call_count == 1
    assert mesh_visualizer.generate_html_content.call_count == 1

if __name__ == "__main__":
    pytest.main([__file__])
