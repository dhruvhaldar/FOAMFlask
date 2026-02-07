import pytest
from backend.meshing.snappyhexmesh import SnappyHexMeshGenerator

class TestSnappyHexMeshGenerator:
    def test_generate_dict_legacy(self, tmp_path):
        case_path = tmp_path / "case"
        (case_path / "system").mkdir(parents=True)

        config = {
            "stl_filename": "test.stl",
            "refinement_level": 3
        }

        success = SnappyHexMeshGenerator.generate_dict(case_path, config)
        assert success is True

        dict_path = case_path / "system" / "snappyHexMeshDict"
        assert dict_path.exists()
        content = dict_path.read_text()
        assert "test.stl" in content
        assert "level 3" in content

    def test_generate_dict_complex(self, tmp_path):
        case_path = tmp_path / "case"
        (case_path / "system").mkdir(parents=True)

        config = {
            "objects": [
                {"name": "obj1.stl", "refinement_level_min": 2, "refinement_level_max": 3, "layers": 2},
                {"name": "obj2.obj", "refinement_level_min": 1, "refinement_level_max": 2}
            ],
            "global_settings": {
                "castellated_mesh": True,
                "snap": False,
                "max_global_cells": 100000
            },
            "location_in_mesh": [1.0, 2.0, 3.0]
        }

        success = SnappyHexMeshGenerator.generate_dict(case_path, config)
        assert success is True

        content = (case_path / "system" / "snappyHexMeshDict").read_text()
        assert "obj1.stl" in content
        assert "obj2.obj" in content
        assert "maxGlobalCells 100000" in content
        assert "locationInMesh (1.0 2.0 3.0)" in content
        assert "snap            false" in content

    def test_generate_dict_invalid_location(self, tmp_path):
        case_path = tmp_path / "case"
        (case_path / "system").mkdir(parents=True)

        config = {
            "stl_filename": "test.stl",
            "location_in_mesh": "invalid"
        }

        success = SnappyHexMeshGenerator.generate_dict(case_path, config)
        assert success is True
        content = (case_path / "system" / "snappyHexMeshDict").read_text()
        assert "locationInMesh (0 0 0)" in content # Default

    def test_generate_dict_no_system_dir(self, tmp_path):
        success = SnappyHexMeshGenerator.generate_dict(tmp_path, {})
        assert success is False

    def test_generate_dict_empty_objects(self, tmp_path):
        case_path = tmp_path / "case"
        (case_path / "system").mkdir(parents=True)

        config = {"objects": []} # No legacy fallback
        success = SnappyHexMeshGenerator.generate_dict(case_path, config)
        assert success is True
        content = (case_path / "system" / "snappyHexMeshDict").read_text()
        assert "geometry" in content # Should still generate valid empty dict

    def test_generate_dict_sanitize(self, tmp_path):
        case_path = tmp_path / "case"
        (case_path / "system").mkdir(parents=True)

        config = {
            "objects": [
                {"name": "../hack.stl"}
            ]
        }

        success = SnappyHexMeshGenerator.generate_dict(case_path, config)
        assert success is True
        content = (case_path / "system" / "snappyHexMeshDict").read_text()
        assert "hack.stl" in content
        assert ".." not in content
