import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import os
from backend.geometry.manager import GeometryManager

class TestGeometryManager:
    @pytest.fixture
    def mock_path(self, tmp_path):
        return tmp_path

    def test_upload_stl_success(self, mock_path):
        case_path = mock_path / "case"
        case_path.mkdir()
        file_mock = MagicMock()
        file_mock.filename = "test.stl"

        result = GeometryManager.upload_stl(case_path, file_mock, "test.stl")

        assert result["success"] is True
        assert result["filename"] == "test.stl"
        assert (case_path / "constant" / "triSurface").exists()
        file_mock.save.assert_called()

    def test_upload_stl_invalid_extension(self, mock_path):
        case_path = mock_path / "case"
        file_mock = MagicMock()

        result = GeometryManager.upload_stl(case_path, file_mock, "test.txt")
        assert result["success"] is False
        assert "allowed" in result["message"]

    def test_upload_stl_invalid_filename(self, mock_path):
        case_path = mock_path / "case"
        file_mock = MagicMock()

        # secure_filename removes paths
        result = GeometryManager.upload_stl(case_path, file_mock, "../../../etc/passwd")
        # secure_filename turns this into "passwd" which has no extension
        assert result["success"] is False
        # If secure_filename returns empty string? No, "passwd".
        # But "passwd" has no extension, so it fails extension check.

        result = GeometryManager.upload_stl(case_path, file_mock, "")
        assert result["success"] is False
        assert "Invalid filename" in result["message"]

    def test_upload_stl_exception(self, mock_path):
        file_mock = MagicMock()
        file_mock.save.side_effect = Exception("Save failed")

        result = GeometryManager.upload_stl(mock_path, file_mock, "test.stl")
        assert result["success"] is False
        # Updated to check for sanitized error
        assert "An internal server error occurred" in result["message"]

    def test_list_stls_success(self, mock_path):
        case_path = mock_path / "case"
        tri_surface = case_path / "constant" / "triSurface"
        tri_surface.mkdir(parents=True)

        (tri_surface / "a.stl").write_text("dummy")
        (tri_surface / "b.obj").write_text("dummy")
        (tri_surface / "c.txt").write_text("dummy")

        result = GeometryManager.list_stls(case_path)

        assert result["success"] is True
        files = result["files"]
        assert len(files) == 2
        assert files[0]["name"] == "a.stl"
        assert files[1]["name"] == "b.obj"
        assert "size" in files[0]

    def test_list_stls_no_directory(self, mock_path):
        result = GeometryManager.list_stls(mock_path / "nonexistent")
        assert result["success"] is True
        assert result["files"] == []

    def test_list_stls_exception(self, mocker):
        mocker.patch('pathlib.Path.resolve', side_effect=Exception("Error"))
        result = GeometryManager.list_stls("path")
        assert result["success"] is False
        assert "An internal server error occurred" in result["message"]

    def test_delete_stl_success(self, mock_path):
        case_path = mock_path / "case"
        tri_surface = case_path / "constant" / "triSurface"
        tri_surface.mkdir(parents=True)
        (tri_surface / "test.stl").write_text("dummy")

        result = GeometryManager.delete_stl(case_path, "test.stl")
        assert result["success"] is True
        assert not (tri_surface / "test.stl").exists()

    def test_delete_stl_not_found(self, mock_path):
        case_path = mock_path / "case"
        result = GeometryManager.delete_stl(case_path, "test.stl")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_delete_stl_exception(self, mocker):
        mocker.patch('pathlib.Path.resolve', side_effect=Exception("Error"))
        result = GeometryManager.delete_stl("path", "file")
        assert result["success"] is False
