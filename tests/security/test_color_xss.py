import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    from app import app
    app.config['TESTING'] = True
    app.config['ENABLE_CSRF'] = False
    with app.test_client() as client:
        yield client

@patch('backend.geometry.visualizer.GeometryVisualizer.get_interactive_html')
@patch('app.validate_geometry_path')
def test_geometry_view_color_xss(mock_validate, mock_get_html, client):
    """
    Test that malicious color payloads are rejected.
    """
    # Setup
    mock_validate.return_value = MagicMock() # Return a mock Path
    mock_get_html.return_value = "<html>Safe</html>"

    # Payload with XSS vector
    payload = '"><script>alert(1)</script>'

    response = client.post('/api/geometry/view', json={
        'caseName': 'test_case',
        'filename': 'test.stl',
        'color': payload
    })

    # Expect failure (400 Bad Request) due to validation
    # Currently it should fail (pass 200) because validation is missing
    # So we assert 400 to fail the test now.
    assert response.status_code == 400
    assert "Invalid color format" in response.json.get('message', '')

@patch('backend.mesh.mesher.mesh_visualizer.get_interactive_viewer_html')
@patch('app.validate_safe_path')
def test_mesh_interactive_color_xss(mock_validate, mock_get_html, client):
    """
    Test that malicious color payloads are rejected in mesh interactive view.
    """
    mock_validate.return_value = MagicMock()
    mock_get_html.return_value = "<html>Safe</html>"

    payload = "red; background: url('javascript:alert(1)')"

    response = client.post('/api/mesh_interactive', json={
        'file_path': 'test.vtk',
        'color': payload
    })

    assert response.status_code == 400
    assert "Invalid color format" in response.json.get('error', '')

@patch('backend.post.isosurface.isosurface_visualizer.start_trame_visualization')
@patch('app.validate_safe_path')
def test_create_contour_colormap_xss(mock_validate, mock_start, client):
    """
    Test that malicious colormap payloads are rejected.
    """
    mock_validate.return_value = MagicMock(exists=lambda: True)
    mock_start.return_value = {"src": "http://localhost:1234"}

    payload = "viridis<script>"

    response = client.post('/api/contours/create', json={
        'tutorial': 'tut',
        'caseDir': 'case',
        'colormap': payload
    })

    assert response.status_code == 400
    assert "Invalid colormap format" in response.json.get('error', '')
