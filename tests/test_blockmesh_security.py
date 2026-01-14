import os
import pytest
from pathlib import Path
from backend.meshing.blockmesh import BlockMeshGenerator

def test_blockmesh_numeric_validation(tmp_path):
    """
    Test that BlockMeshGenerator rejects non-numeric inputs in vector fields,
    preventing dictionary injection (e.g. #codeStream).
    """
    case_dir = tmp_path / "test_case_secure"
    case_dir.mkdir()
    (case_dir / "system").mkdir()

    # 1. Test Malicious Input
    # Payload trying to close the vertex list and start a codeStream
    malicious_min = ("0", "0", "0); #codeStream ...")
    max_point = (1, 1, 1)
    cells = (10, 10, 10)

    success = BlockMeshGenerator.generate_dict(case_dir, malicious_min, max_point, cells)
    assert success is False, "Generator should fail with malicious string input"

    dict_path = case_dir / "system" / "blockMeshDict"
    # Ensure file was not created (or at least valid one wasn't overwriten if it existed,
    # but here we started fresh so it shouldn't exist)
    assert not dict_path.exists(), "blockMeshDict should not be created on validation failure"

    # 2. Test Valid Numeric Input (Integers as strings should be converted safely)
    valid_min_str = ("-1", "-1", "-1") # "Clean" strings that are numbers
    success = BlockMeshGenerator.generate_dict(case_dir, valid_min_str, max_point, cells)
    assert success is True, "Generator should accept valid numeric strings and convert them"

    content = dict_path.read_text()
    assert "(-1.0 -1.0 -1.0)" in content
    assert "#codeStream" not in content

    # 3. Test Invalid Types (e.g. lists instead of numbers inside the tuple)
    invalid_cells = (10, 10, [10]) # Nested list is invalid for int conversion
    success = BlockMeshGenerator.generate_dict(case_dir, (-1,-1,-1), max_point, invalid_cells)
    assert success is False

    # 4. Test Invalid Length
    invalid_len_point = (0, 0) # Missing Z
    success = BlockMeshGenerator.generate_dict(case_dir, invalid_len_point, max_point, cells)
    assert success is False
