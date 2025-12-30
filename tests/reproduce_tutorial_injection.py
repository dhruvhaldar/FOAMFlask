
import pytest
from unittest.mock import MagicMock, patch
import app
import json

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client

def test_load_tutorial_command_injection_prevented(client):
    # Mock the docker client
    mock_docker_client = MagicMock()

    # Mock get_tutorials to return a list of valid tutorials
    # We must patch 'app.get_tutorials' because that's where the function is imported/used
    with patch('app.get_tutorials', return_value=["incompressible/icoFoam/cavity/cavity"]):
        with patch('app.get_docker_client', return_value=mock_docker_client):
            # Payload with command injection
            malicious_tutorial = "incompressible/icoFoam/cavity/cavity'; echo HACKED; #"

            response = client.post('/load_tutorial', json={
                'tutorial': malicious_tutorial
            })

            # Check that the request was rejected
            assert response.status_code == 400
            data = json.loads(response.data)
            assert "[Error] Invalid tutorial selected" in data["output"]

            # Check that docker container run was NEVER called
            mock_docker_client.containers.run.assert_not_called()

def test_load_tutorial_valid(client):
    # Verify a valid tutorial still works
    mock_docker_client = MagicMock()
    mock_container = MagicMock()
    mock_docker_client.containers.run.return_value = mock_container
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"logs"
    mock_container.status = "exited"

    valid_tutorial = "incompressible/icoFoam/cavity/cavity"

    with patch('app.get_tutorials', return_value=[valid_tutorial]):
        with patch('app.get_docker_client', return_value=mock_docker_client):
            response = client.post('/load_tutorial', json={
                'tutorial': valid_tutorial
            })

            assert response.status_code == 200
            # Docker should have been called
            mock_docker_client.containers.run.assert_called_once()
