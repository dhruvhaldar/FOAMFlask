import pytest
from backend.case.manager import CaseManager

class TestCaseManager:
    def test_create_case_structure_new(self, tmp_path):
        case_path = tmp_path / "new_case"

        result = CaseManager.create_case_structure(case_path)

        assert result["success"] is True
        assert (case_path / "0").is_dir()
        assert (case_path / "constant").is_dir()
        assert (case_path / "system").is_dir()
        assert (case_path / "system" / "controlDict").exists()
        assert (case_path / "system" / "fvSchemes").exists()
        assert (case_path / "system" / "fvSolution").exists()
        assert (case_path / "constant" / "transportProperties").exists()

    def test_create_case_structure_existing_valid(self, tmp_path):
        case_path = tmp_path / "existing"
        (case_path / "system").mkdir(parents=True)
        (case_path / "constant").mkdir(parents=True)
        (case_path / "0").mkdir(parents=True)
        (case_path / "dummy").touch()

        result = CaseManager.create_case_structure(case_path)

        assert result["success"] is True
        assert "exists" in result["message"]

    def test_create_case_structure_existing_invalid(self, tmp_path):
        # Empty directory
        case_path = tmp_path / "empty"
        case_path.mkdir()

        result = CaseManager.create_case_structure(case_path)
        assert result["success"] is True
        # Should populate it
        assert (case_path / "system" / "controlDict").exists()

    def test_create_case_structure_exception(self, mocker):
        mocker.patch('pathlib.Path.resolve', side_effect=Exception("Error"))
        result = CaseManager.create_case_structure("path")
        assert result["success"] is False
