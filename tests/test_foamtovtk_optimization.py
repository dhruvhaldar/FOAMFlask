
import pytest
import json
from unittest.mock import patch, MagicMock
from app import app, get_docker_client, CASE_ROOT

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['ENABLE_CSRF'] = False
    with app.test_client() as client:
        yield client

def test_run_foamtovtk_response_type(client, tmp_path):
    """
    Test that run_foamtovtk returns text/plain (optimized) instead of text/html.
    And verifies the content format is newline delimited, not <br> delimited.
    """
    tutorial = "test_tutorial"
    case_dir = str(tmp_path / tutorial)
    (tmp_path / tutorial).mkdir(exist_ok=True, parents=True)

    with patch('app.get_docker_client') as mock_docker, \
         patch('app.CASE_ROOT', str(tmp_path)):

        # Setup mock container logs
        mock_client = MagicMock()
        mock_container = MagicMock()
        # Mock logs yielding byte lines
        mock_container.logs.return_value = [b"Line 1\n", b"Line 2\n"]
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client

        response = client.post('/run_foamtovtk', json={
            "tutorial": tutorial,
            "caseDir": case_dir
        })

        assert response.status_code == 200

        # Check Content-Type
        # BEFORE OPTIMIZATION: This expects text/html
        # AFTER OPTIMIZATION: This should be text/plain

        # Current behavior check (should FAIL if I optimize, PASS currently)
        # But I want to fail first if I'm doing TDD?
        # The prompt asks me to "Verify the optimization works as expected".

        # Let's write the test for the DESIRED behavior.
        # It should fail now because current implementation returns text/html.

        assert response.mimetype == "text/plain"

        # Check content format
        data = response.get_data(as_text=True)
        assert "Line 1\n" in data
        assert "Line 2\n" in data
        assert "<br>" not in data
