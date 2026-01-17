from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
import app

@pytest.fixture
def mock_docker_client():
    with patch('app.get_docker_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

def test_api_fetch_resource_geometry_secure_command(mock_docker_client):
    """
    Verify that api_fetch_resource_geometry uses list-based command construction
    to prevent shell injection, rather than string interpolation.
    """
    # Setup
    with app.app.test_request_context(
        json={"filename": "motorBike.obj.gz", "caseName": "test_case"}
    ):
        with patch('app.validate_safe_path') as mock_validate:
            mock_path = MagicMock()
            mock_path.resolve.return_value = Path("/tmp/test_case/constant/triSurface")
            # Mock as_posix to return a string
            # mock_path.resolve.return_value.as_posix.return_value = "/tmp/test_case/constant/triSurface"
            mock_validate.return_value = mock_path

            # Execute
            app.api_fetch_resource_geometry()

            # Verify
            mock_docker_client.containers.run.assert_called_once()
            args, kwargs = mock_docker_client.containers.run.call_args

            command = args[1]
            # Crucial check: Command should be a list, not a string
            assert isinstance(command, list), "Command must be a list for security"

            # Verify structure: bash -c '...' -bash   ...
            assert command[0] == "bash"
            assert command[1] == "-c"

            # Verify arguments are passed as positional params
            # Index 3 is typically the first argument after script name (-bash) and bashrc ()
            # The exact indices depend on how many args we pass.
            # Expected: ["bash", "-c", "source \"\" && cp ... \"\" ...", "fetcher", bashrc, filename]

            assert "motorBike.obj.gz" in command[3:], "Filename should be passed as an argument"
            assert "/opt/openfoam12/etc/bashrc" in command[3:], "Bashrc should be passed as an argument"
