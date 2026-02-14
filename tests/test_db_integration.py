
import pytest
from app import app, db, SimulationRun
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    """Configures the app for testing."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["ENABLE_CSRF"] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()

@patch("app.get_docker_client")
def test_simulation_run_lifecycle(mock_get_docker_client, client):
    """Test that a simulation run is created, updated, and completed correctly."""

    # Mock Docker Client and Container
    mock_docker = MagicMock()
    mock_container = MagicMock()
    mock_get_docker_client.return_value = mock_docker
    mock_docker.containers.run.return_value = mock_container

    # Mock logs streaming
    mock_container.logs.return_value = [b"Starting simulation...", b"Running...", b"Finished."]

    # Mock config
    with patch("app.CASE_ROOT", "/tmp/test_case_root"):
        with patch("app.validate_safe_path", return_value=True): # Bypass path validation for unit test simplicity

            # 1. Trigger Run
            payload = {
                "tutorial": "basic/pitzDaily",
                "command": "blockMesh",
                "caseDir": "/tmp/test_case_root/basic/pitzDaily"
            }

            response = client.post("/run", json=payload)
            assert response.status_code == 200

            # Consume the stream to ensure the generator completes
            list(response.response)

            # 2. Verify Database Record
            with app.app_context():
                # We expect one run, but scalar_one() raises if multiple found.
                # Since we reset DB in fixture, there should be only one.
                # However, if run_case was called multiple times or threads, maybe 2?
                # Let's inspect all results.
                runs = db.session.execute(db.select(SimulationRun)).scalars().all()
                assert len(runs) == 1, f"Expected 1 run, found {len(runs)}"
                run = runs[0]

                assert run.case_name == payload["caseDir"]
                assert run.tutorial == payload["tutorial"]
                assert run.command == payload["command"]
                assert run.status == "Completed"
                assert run.start_time is not None
                assert run.end_time is not None
                assert run.execution_duration is not None
                assert run.execution_duration >= 0

@patch("app.get_docker_client")
def test_simulation_run_failure(mock_get_docker_client, client):
    """Test that a failed simulation run updates the status to Failed."""

    # Mock Docker Client to raise an exception during run
    mock_docker = MagicMock()
    mock_get_docker_client.return_value = mock_docker
    mock_docker.containers.run.side_effect = Exception("Docker Error")

    with patch("app.CASE_ROOT", "/tmp/test_case_root"):
        with patch("app.validate_safe_path", return_value=True):

            payload = {
                "tutorial": "basic/pitzDaily",
                "command": "blockMesh",
                "caseDir": "/tmp/test_case_root/basic/pitzDaily"
            }

            response = client.post("/run", json=payload)

            # Consume stream (it will yield error messages)
            output = b"".join(response.response).decode()
            assert "Failed to start container" in output

            # Verify Database Record
            with app.app_context():
                run = db.session.execute(db.select(SimulationRun)).scalar_one()
                assert run.status == "Failed"
                assert run.end_time is not None
