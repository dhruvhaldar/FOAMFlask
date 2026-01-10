import pytest
import json
from unittest.mock import patch, MagicMock
from app import app, CaseManager

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['ENABLE_CSRF'] = False  # Disable CSRF for testing
    with app.test_client() as client:
        yield client

def test_api_create_case_error_leakage(client):
    """
    Test that sensitive paths are not leaked in error messages.
    """
    # Mock CaseManager.create_case_structure to raise an OSError with a sensitive path
    sensitive_path = "/secret/path/to/case"
    with patch("backend.case.manager.CaseManager.create_case_structure") as mock_create:
        mock_create.side_effect = OSError(f"Permission denied: '{sensitive_path}'")

        # Valid input to pass validate_safe_path
        payload = {"caseName": "my_case"}

        response = client.post('/api/case/create',
                              data=json.dumps(payload),
                              content_type='application/json')

        # Should be 500
        assert response.status_code == 500

        data = json.loads(response.data)

        # Check that the error message does NOT contain the sensitive path
        error_msg = data.get("message", "")

        # Secure behavior: error_msg is generic
        assert sensitive_path not in error_msg, f"Sensitive path leaked in error: {error_msg}"
        assert "Permission denied" not in error_msg, "Specific error detail leaked"
        assert error_msg == "An I/O error occurred. Please check the logs."

def test_run_case_error_leakage(client):
    """
    Test that run_case doesn't leak paths in streamed output on error.
    """
    with patch("app.get_docker_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock containers.run to raise exception
        sensitive_path = "/secret/server/path"
        mock_client.containers.run.side_effect = Exception(f"Container failed at {sensitive_path}")

        payload = {
            "tutorial": "basic/pitzDaily",
            "command": "blockMesh",
            "caseDir": "pitzDaily"
        }

        # Need to mock validate_safe_path or provide valid paths
        # app.py: validate_safe_path(CASE_ROOT, case_dir)
        # We can just mock validate_safe_path to succeed
        with patch("app.validate_safe_path") as mock_validate:
            mock_validate.return_value = MagicMock()

            response = client.post('/run',
                                  data=json.dumps(payload),
                                  content_type='application/json')

            assert response.status_code == 200
            content = response.data.decode('utf-8')

            # Check for leakage
            assert sensitive_path not in content, "Sensitive path leaked in run stream"
            # It should contain the generic message
            assert "An internal server error occurred." in content or "An I/O error occurred" in content or "Failed to start container" in content
