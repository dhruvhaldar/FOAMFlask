
import pytest
from unittest.mock import MagicMock, patch, Mock
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
def test_switching_files_perf(mock_load_mesh_safe, mock_validate_file, mesh_visualizer, mock_mesh):
    """
    Test performance when switching between two different mesh files.
    The goal is to ensure that loading File A, then File B, then File A again
    results in a cache HIT for the second load of File A, avoiding disk I/O and processing.
    """
    # Setup mocks
    file_path_a = "file_a.vtk"
    file_path_b = "file_b.vtk"

    # Mock validate_file to handle both paths
    def side_effect_validate(path):
        m = MagicMock()
        m.__str__.return_value = str(path)
        # Unique mtime for each file
        if str(path) == file_path_a:
            m.stat.return_value.st_mtime = 1000.0
        else:
            m.stat.return_value.st_mtime = 2000.0
        return m

    mock_validate_file.side_effect = side_effect_validate
    mock_load_mesh_safe.return_value = mock_mesh

    # Mock decimate_mesh and generate_html_content
    decimated_mesh = MagicMock(spec=pv.PolyData)
    decimated_mesh.n_cells = 200000
    mesh_visualizer.decimate_mesh = MagicMock(return_value=decimated_mesh)
    mesh_visualizer.generate_html_content = MagicMock(return_value="<html></html>")

    # 1. Load File A
    mesh_visualizer.get_interactive_viewer_html(file_path_a, show_edges=True, color="blue")

    assert mock_load_mesh_safe.call_count == 1
    # Check that we loaded File A
    args, _ = mock_load_mesh_safe.call_args
    assert str(args[0]) == file_path_a

    # 2. Load File B (Switching context)
    mesh_visualizer.get_interactive_viewer_html(file_path_b, show_edges=True, color="blue")

    assert mock_load_mesh_safe.call_count == 2
    # Check that we loaded File B
    args, _ = mock_load_mesh_safe.call_args
    assert str(args[0]) == file_path_b

    # 3. Load File A AGAIN
    # Currently (before optimization), this should trigger load_mesh_safe again (count=3)
    # After optimization, it should remain 2 (cache hit)
    mesh_visualizer.get_interactive_viewer_html(file_path_a, show_edges=True, color="blue")

    # Assert behavior based on current implementation
    # Before optimization: EXPECT 3 calls
    # After optimization: EXPECT 2 calls

    # After optimization: Cache HIT for second access to A
    assert mock_load_mesh_safe.call_count == 2

if __name__ == "__main__":
    pytest.main([__file__])
