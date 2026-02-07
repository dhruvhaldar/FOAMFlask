import pytest
from unittest.mock import MagicMock, patch, mock_open
from backend.startup import run_initial_setup_checks, check_docker_permissions
import docker
from pathlib import Path

class TestStartup:
    def test_run_initial_setup_checks_already_done(self):
        config = {"initial_setup_done": True}
        result = run_initial_setup_checks(MagicMock(), "root", "img", MagicMock(), config)
        assert result["status"] == "completed"

    def test_run_initial_setup_checks_no_docker(self, mocker):
        mocker.patch("shutil.which", return_value=None)
        result = run_initial_setup_checks(MagicMock(), "root", "img", MagicMock(), {})
        assert result["status"] == "failed"
        assert "not installed" in result["message"]

    def test_run_initial_setup_checks_docker_permission_error(self, mocker):
        mocker.patch("shutil.which", return_value="/usr/bin/docker")
        get_client = MagicMock(return_value=None)

        # Mock docker.from_env to raise permission error
        mocker.patch("docker.from_env", side_effect=docker.errors.DockerException("permission denied"))

        result = run_initial_setup_checks(get_client, "root", "img", MagicMock(), {})
        assert result["status"] == "failed"
        assert "permission denied" in result["message"]

    def test_run_initial_setup_checks_image_pull(self, mocker):
        mocker.patch("shutil.which", return_value="/usr/bin/docker")
        client = MagicMock()
        get_client = MagicMock(return_value=client)

        # Image not found, then pull
        client.images.get.side_effect = docker.errors.ImageNotFound("msg")

        # Mock no Dockerfile
        # Use regex or simple check for 'Dockerfile' in path string to decide logic
        # Note: Path.exists is an instance method, so 'self' is the path object.
        # But when patching side_effect on the class method, the first arg is 'self'.
        def side_effect(self):
            if str(self).endswith("Dockerfile"):
                return False
            return True # Assume others exist to pass other checks if any

        mocker.patch("pathlib.Path.exists", side_effect=side_effect, autospec=True)

        # Mock check_docker_permissions to return success
        mocker.patch("backend.startup.check_docker_permissions", return_value={"status": "completed"})

        result = run_initial_setup_checks(get_client, "root", "img", MagicMock(), {})

        client.images.pull.assert_called_with("img")
        assert result["status"] == "completed"

    def test_run_initial_setup_checks_image_build(self, mocker):
        mocker.patch("shutil.which", return_value="/usr/bin/docker")
        client = MagicMock()
        get_client = MagicMock(return_value=client)
        client.images.get.side_effect = docker.errors.ImageNotFound("msg")

        # Mock Dockerfile exists
        def side_effect(self):
            if str(self).endswith("Dockerfile"):
                return True
            return True

        mocker.patch("pathlib.Path.exists", side_effect=side_effect, autospec=True)
        mocker.patch("builtins.open", mock_open())
        mocker.patch("backend.startup.check_docker_permissions", return_value={"status": "completed"})

        result = run_initial_setup_checks(get_client, "root", "img", MagicMock(), {})

        client.images.build.assert_called()
        assert result["status"] == "completed"

    def test_check_docker_permissions_non_linux(self, mocker):
        mocker.patch("platform.system", return_value="Windows")
        save_config = MagicMock()

        result = check_docker_permissions(MagicMock(), "root", "img", save_config, {})
        assert result["status"] == "completed"
        save_config.assert_called()

    def test_check_docker_permissions_linux_success(self, mocker, tmp_path):
        mocker.patch("platform.system", return_value="Linux")
        client = MagicMock()
        get_client = MagicMock(return_value=client)
        save_config = MagicMock()

        # Mock successful file write
        test_file = tmp_path / "test_file"
        # We need check_docker_permissions to use tmp_path
        # But it resolves case_root.
        # We can pass tmp_path as case_root.

        # Container run mock
        def side_effect(*args, **kwargs):
            # Create file
            # Since we can't easily map volumes in mock, we manually create the file on "host"
            # We need to know the filename.
            # The function generates a random name.
            # We can mock uuid
            pass

        mocker.patch("uuid.uuid4", return_value=MagicMock(hex="123"))

        # We expect it to look for case_root/.permission_test_123
        target_file = tmp_path / ".permission_test_123"

        def run_side_effect(*args, **kwargs):
            target_file.touch()
            return MagicMock()

        client.containers.run.side_effect = run_side_effect

        result = check_docker_permissions(get_client, str(tmp_path), "img", save_config, {})

        assert result["status"] == "completed"
        assert not target_file.exists() # Should be cleaned up
        save_config.assert_called_with({"initial_setup_done": True, "docker_run_as_user": False})

    def test_check_docker_permissions_linux_fail_retry_success(self, mocker, tmp_path):
        mocker.patch("platform.system", return_value="Linux")
        client = MagicMock()
        get_client = MagicMock(return_value=client)
        save_config = MagicMock()

        mocker.patch("uuid.uuid4", return_value=MagicMock(hex="123"))
        target_file = tmp_path / ".permission_test_123"

        # First run creates file but unlink fails (permission error simulation)
        # Second run (as user) creates file and unlink succeeds

        # We need to simulate unlink raising PermissionError
        # But only for the first attempt.

        # We can mock pathlib.Path.unlink
        unlink_mock = mocker.patch("pathlib.Path.unlink")
        unlink_mock.side_effect = [PermissionError("root owned"), None]

        # We also need container run to create the file both times
        def run_side_effect(*args, **kwargs):
            # Verify user arg
            if 'user' in kwargs:
                # Second run
                pass
            target_file.touch()
            return MagicMock()

        client.containers.run.side_effect = run_side_effect
        # Mock exists to be true
        mocker.patch("pathlib.Path.exists", return_value=True)

        result = check_docker_permissions(get_client, str(tmp_path), "img", save_config, {})

        assert result["status"] == "completed"
        assert "using host user" in result["message"]
        save_config.assert_called()
        assert save_config.call_args[0][0]["docker_run_as_user"] is True
