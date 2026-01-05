
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure the app module can be imported
sys.path.append(str(Path(__file__).parent.parent))

# Create a proper Mock for docker module that includes a real Exception class for DockerException
mock_docker = MagicMock()
mock_docker_errors = MagicMock()

# Define a real exception class
class MockDockerException(Exception):
    pass

mock_docker_errors.DockerException = MockDockerException
mock_docker.errors = mock_docker_errors

sys.modules['docker'] = mock_docker
sys.modules['docker.errors'] = mock_docker_errors

import app as flask_app

@pytest.fixture
def app():
    flask_app.app.config.update({
        "TESTING": True,
    })
    yield flask_app.app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
