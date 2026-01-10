import pytest
import json
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['ENABLE_CSRF'] = False
    with app.test_client() as client:
        yield client

def test_set_case_error_leakage(client):
    sensitive_path = "/secret/path/to/case"
    with patch("pathlib.Path.mkdir") as mock_mkdir:
        mock_mkdir.side_effect = OSError(f"Permission denied: '{sensitive_path}'")

        payload = {"caseDir": "/tmp/test"} # Valid path structure
        # Mock validate_safe_path or bypass checks logic in set_case
        # set_case does Path(data["caseDir"]).resolve()

        response = client.post('/set_case',
                              data=json.dumps(payload),
                              content_type='application/json')

        data = json.loads(response.data)
        error_msg = data.get("output", "")

        # Current behavior: Leaks str(e) -> "Permission denied: '/secret/path/to/case'"
        # Expected behavior: "An I/O error occurred. Please check the logs."
        assert sensitive_path not in error_msg, f"Sensitive path leaked in set_case: {error_msg}"

def test_load_tutorial_error_leakage(client):
    sensitive_path = "/secret/host/path"
    with patch("app.get_docker_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        # Mock run to fail with exception containing path
        mock_client.containers.run.side_effect = Exception(f"Bind mount failed at {sensitive_path}")

        # Valid tutorial path
        payload = {"tutorial": "basic/pitzDaily"}

        response = client.post('/load_tutorial',
                              data=json.dumps(payload),
                              content_type='application/json')

        data = json.loads(response.data)
        error_msg = data.get("output", "")

        assert sensitive_path not in error_msg, f"Sensitive path leaked in load_tutorial: {error_msg}"

def test_api_available_meshes_error_leakage(client):
    sensitive_path = "/secret/path"
    with patch("backend.mesh.mesher.mesh_visualizer.get_available_meshes") as mock_get:
        mock_get.side_effect = Exception(f"Failed to scan {sensitive_path}")

        response = client.get('/api/available_meshes?tutorial=basic/pitzDaily')

        data = json.loads(response.data)
        error_msg = data.get("error", "")

        assert sensitive_path not in error_msg, f"Sensitive path leaked in api_available_meshes: {error_msg}"
