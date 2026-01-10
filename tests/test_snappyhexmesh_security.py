
import pytest
from pathlib import Path
from backend.meshing.snappyhexmesh import SnappyHexMeshGenerator

class TestSnappyHexMeshSecurity:

    def test_location_in_mesh_sanitization(self, tmp_path):
        """Test that location_in_mesh is sanitized."""
        case_dir = tmp_path / "case"
        system_dir = case_dir / "system"
        system_dir.mkdir(parents=True)

        # Malicious payload
        payload = '10); #codeStream { code #{ os.system("echo PWNED > pwned.txt"); #} }; ('

        config = {
            "global_settings": {
                "castellated_mesh": True
            },
            "objects": [],
            "location_in_mesh": [0, 0, payload]
        }

        success = SnappyHexMeshGenerator.generate_dict(case_dir, config)
        assert success

        content = (system_dir / "snappyHexMeshDict").read_text()

        # Should be default 0.0 0.0 0.0 because of invalid input
        assert "locationInMesh (0.0 0.0 0.0);" in content
        assert "echo PWNED" not in content

    def test_object_name_sanitization(self, tmp_path):
        """Test that object names are sanitized."""
        case_dir = tmp_path / "case"
        system_dir = case_dir / "system"
        system_dir.mkdir(parents=True)

        config = {
            "objects": [
                {
                    "name": "../../etc/passwd.stl",
                    "refinement_level_min": 2,
                    "refinement_level_max": 2,
                    "layers": 0
                }
            ]
        }

        success = SnappyHexMeshGenerator.generate_dict(case_dir, config)
        assert success

        content = (system_dir / "snappyHexMeshDict").read_text()

        # secure_filename should strip path traversal
        # ../../etc/passwd.stl -> passwd.stl (or similar depending on implementation)
        # werkzeug secure_filename usually handles this.

        assert "passwd.stl" in content
        assert "../" not in content
        assert "/etc/" not in content

    def test_global_settings_sanitization(self, tmp_path):
        """Test that global settings are cast to correct types."""
        case_dir = tmp_path / "case"
        system_dir = case_dir / "system"
        system_dir.mkdir(parents=True)

        config = {
            "global_settings": {
                "max_global_cells": "2000000; #codeStream",
                "tolerance": "2.0; #codeStream"
            }
        }

        # This will fail conversion to int/float and raise ValueError caught in _validate_config if implemented naively,
        # OR if we implemented try-except in _validate_config, it should fall back to defaults or fail safely.
        # My implementation raises ValueError for int() which is NOT caught in _validate_config (except for location_in_mesh).
        # Let's check my implementation.

        # My implementation:
        # "max_global_cells": int(raw_globals.get("max_global_cells", 2000000)),

        # If input is "2000000; #codeStream", int() raises ValueError.
        # This exception propagates to generate_dict which catches Exception and returns False.
        # So the generation should fail, which is also a secure outcome (Availability vs Integrity).

        success = SnappyHexMeshGenerator.generate_dict(case_dir, config)
        assert not success

    def test_valid_config(self, tmp_path):
        """Test that valid configuration works."""
        case_dir = tmp_path / "case"
        system_dir = case_dir / "system"
        system_dir.mkdir(parents=True)

        config = {
            "global_settings": {
                "max_global_cells": 1000,
                "tolerance": 1.5
            },
            "objects": [
                {
                    "name": "valid.stl",
                    "refinement_level_min": 1,
                    "refinement_level_max": 2,
                    "layers": 3
                }
            ],
            "location_in_mesh": [1.0, 2.0, 3.0]
        }

        success = SnappyHexMeshGenerator.generate_dict(case_dir, config)
        assert success

        content = (system_dir / "snappyHexMeshDict").read_text()
        assert "maxGlobalCells 1000;" in content
        assert "tolerance 1.5;" in content
        assert "valid.stl" in content
        assert "locationInMesh (1.0 2.0 3.0);" in content
