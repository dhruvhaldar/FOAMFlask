import pytest
from unittest.mock import patch
from app import app, validate_safe_path
from pathlib import Path
import os

class TestHiddenPathAccess:

    @pytest.fixture
    def client(self):
        app.config.update({
            "TESTING": True,
            "ENABLE_CSRF": False
        })
        with app.test_client() as client:
            yield client

    def test_validate_safe_path_blocks_hidden_dirs(self, tmp_path):
        """Test that validate_safe_path raises ValueError for hidden directories."""
        base = tmp_path

        # Test direct hidden directory
        with pytest.raises(ValueError, match="Access denied: Hidden paths not allowed"):
            validate_safe_path(str(base), ".hidden_case")

        # Test nested hidden directory
        with pytest.raises(ValueError, match="Access denied: Hidden paths not allowed"):
            validate_safe_path(str(base), "visible_case/.hidden_sub")

        # Test hidden file
        with pytest.raises(ValueError, match="Access denied: Hidden paths not allowed"):
            validate_safe_path(str(base), "visible_case/.env")

    def test_validate_safe_path_allows_normal_paths(self, tmp_path):
        """Test that validate_safe_path allows normal paths."""
        base = tmp_path

        # Should not raise
        path = validate_safe_path(str(base), "normal_case")
        assert path.name == "normal_case"

        path = validate_safe_path(str(base), "normal_case/sub_folder")
        assert path.name == "sub_folder"

    def test_api_create_case_blocks_hidden_name(self, client):
        """Test that creating a case with a hidden name is blocked."""
        # Mocking CaseManager to avoid actual creation logic if validation passes (it shouldn't)
        with patch('backend.case.manager.CaseManager.create_case_structure') as mock_create:
            response = client.post('/api/case/create', json={'caseName': '.hidden_case'})

            assert response.status_code == 400
            data = response.get_json()
            assert "Hidden paths not allowed" in data['message']
            mock_create.assert_not_called()

    def test_api_create_case_blocks_nested_hidden(self, client):
        """Test that creating a case with nested hidden path is blocked."""
        with patch('backend.case.manager.CaseManager.create_case_structure') as mock_create:
            response = client.post('/api/case/create', json={'caseName': 'my_case/.git'})

            assert response.status_code == 400
            data = response.get_json()
            assert "Hidden paths not allowed" in data['message']
            mock_create.assert_not_called()
