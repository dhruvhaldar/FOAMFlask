
import pytest
from unittest.mock import patch, MagicMock
from app import app
import json
from pathlib import Path

class TestCaseRootSecurity:

    @pytest.fixture
    def client(self):
        app.config.update({
            "TESTING": True,
            "ENABLE_CSRF": False
        })
        with app.test_client() as client:
            yield client

    def test_set_root_to_system_root_rejected(self, client):
        """Test that setting CASE_ROOT to '/' is rejected."""

        # Mock save_config to prevent actual file writes
        with patch('app.save_config', return_value=True):
            # We also need to patch CASE_ROOT if it's used, but the endpoint modifies the global
            # and then calls save_config.

            response = client.post('/set_case', json={'caseDir': '/'})

            assert response.status_code == 400
            data = response.get_json()
            assert "Cannot set case root to system directory" in data['output']

    def test_set_root_to_valid_non_hidden_path(self, client, tmp_path):
        """Test that setting CASE_ROOT to a valid, non-hidden path is accepted."""

        valid_dir = tmp_path / "valid_cases"
        valid_dir.mkdir()
        valid_dir_str = str(valid_dir)

        with patch('app.save_config', return_value=True) as mock_save:
            response = client.post('/set_case', json={'caseDir': valid_dir_str})

            assert response.status_code == 200
            data = response.get_json()
            assert data['caseDir'] == valid_dir_str
            assert "Case root set to" in data['output']
            mock_save.assert_called_once()

    def test_set_root_to_system_dir_rejected(self, client):
        """Test that setting CASE_ROOT to system directories (e.g., /etc) is rejected."""

        system_dirs = ['/etc', '/bin', '/usr', '/var', '/proc']

        with patch('app.save_config', return_value=True):
            for path in system_dirs:
                response = client.post('/set_case', json={'caseDir': path})

                assert response.status_code == 400
                data = response.get_json()
                assert "Cannot set case root to system directory" in data['output']

    def test_set_root_to_safe_dir_allowed(self, client, tmp_path):
        """Test that setting CASE_ROOT to a safe user directory is allowed."""

        safe_dir = tmp_path / "my_simulations"
        safe_dir.mkdir()
        safe_dir_str = str(safe_dir)

        with patch('app.save_config', return_value=True) as mock_save:
            response = client.post('/set_case', json={'caseDir': safe_dir_str})

            assert response.status_code == 200
            data = response.get_json()
            assert data['caseDir'] == safe_dir_str

            mock_save.assert_called_once()

    def test_set_root_to_home_rejected(self, client):
        """Test that setting CASE_ROOT to the user's home directory is rejected."""

        home_dir = str(Path.home().resolve())

        with patch('app.save_config', return_value=True):
            response = client.post('/set_case', json={'caseDir': home_dir})

            assert response.status_code == 400
            data = response.get_json()
            # The error message is generic "Cannot set case root to system directory"
            # or it might be failing the checks and returning 400.
            # is_safe_case_root returns False, so the endpoint returns 400 with generic message.
            assert "Cannot set case root to system directory" in data['output']

    def test_set_root_to_hidden_dir_rejected(self, client, tmp_path):
        """Test that setting CASE_ROOT to a hidden directory is rejected."""

        # Create a hidden directory in tmp_path
        hidden_dir = tmp_path / ".hidden_project"
        hidden_dir.mkdir()
        hidden_dir_str = str(hidden_dir)

        with patch('app.save_config', return_value=True):
            response = client.post('/set_case', json={'caseDir': hidden_dir_str})

            assert response.status_code == 400
            data = response.get_json()
            assert "Cannot set case root to system directory" in data['output']

    def test_set_root_to_subdir_of_hidden_rejected(self, client, tmp_path):
        """Test that setting CASE_ROOT to a subdirectory of a hidden directory is rejected."""

        hidden_parent = tmp_path / ".config"
        hidden_parent.mkdir()
        subdir = hidden_parent / "foam_cases"
        subdir.mkdir()
        subdir_str = str(subdir)

        with patch('app.save_config', return_value=True):
            response = client.post('/set_case', json={'caseDir': subdir_str})

            assert response.status_code == 400
            data = response.get_json()
            assert "Cannot set case root to system directory" in data['output']
