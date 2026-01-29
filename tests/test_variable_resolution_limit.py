
import mmap
import pytest
from backend.plots.realtime_plots import OpenFOAMFieldParser

def test_resolve_variable_limit(tmp_path):
    # Create a mock file
    file_path = tmp_path / "testLimit"

    # Structure:
    # Variable defined before internalField (typical case)
    # internalField ...
    # Variable defined after internalField (unusual but used to test limit)

    content = b"""
    Header
    varInHeader 10;

    internalField uniform $varInHeader;

    // Junk

    varAfterLimit 20;
    """

    file_path.write_bytes(content)

    parser = OpenFOAMFieldParser(str(tmp_path))

    with open(file_path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            idx = mm.find(b"internalField")
            assert idx != -1

            # 1. Resolve variable defined BEFORE limit -> Should succeed
            val = parser._resolve_variable(mm, b"varInHeader", search_limit=idx)
            assert val == "10"

            # 2. Resolve variable defined AFTER limit -> Should fail (return None)
            # This confirms that the search was actually limited
            val_after = parser._resolve_variable(mm, b"varAfterLimit", search_limit=idx)
            assert val_after is None

            # 3. Resolve without limit -> Should succeed (sanity check)
            val_no_limit = parser._resolve_variable(mm, b"varAfterLimit")
            assert val_no_limit == "20"
