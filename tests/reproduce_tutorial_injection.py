
import pytest
from unittest.mock import MagicMock, patch
import app
import json

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client

def test_tutorial_command_injection_prevented(client):
    """
    Test that the load_tutorial endpoint correctly rejects malicious input
    and does NOT execute docker commands.
    """
    # Mock the docker client
    mock_docker_client = MagicMock()
    mock_container = MagicMock()
    mock_docker_client.containers.run.return_value = mock_container

    with patch('app.get_docker_client', return_value=mock_docker_client):
        # Malicious payload
        payload = {
            "tutorial": "basic/pitzDaily; echo 'INJECTED' > /tmp/hacked; #"
        }

        response = client.post('/load_tutorial',
                             data=json.dumps(payload),
                             content_type='application/json')

        # Verify the request was rejected
        assert response.status_code == 400
        assert b"Invalid tutorial path" in response.data

        # Verify docker command was NEVER called
        assert not mock_docker_client.containers.run.called
