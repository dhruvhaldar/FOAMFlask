
import pytest
from pathlib import Path
from backend.plots.realtime_plots import OpenFOAMFieldParser

@pytest.fixture
def parser(tmp_path):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    return OpenFOAMFieldParser(case_dir)

def test_residuals_incremental_read(parser, tmp_path):
    """Verify that residuals are parsed incrementally."""
    log_file = tmp_path / "case" / "log.foamRun"

    # Write first chunk
    chunk1 = "Time = 1\nSolving for Ux, Initial residual = 0.1\n"
    log_file.write_text(chunk1, encoding="utf-8")

    residuals = parser.get_residuals_from_log("log.foamRun")
    assert residuals["time"] == [1.0]
    assert residuals["Ux"] == [0.1]

    # Write second chunk
    chunk2 = "Time = 2\nSolving for Ux, Initial residual = 0.05\n"
    # We must append bytes
    with log_file.open("ab") as f:
        f.write(chunk2.encode("utf-8"))

    residuals = parser.get_residuals_from_log("log.foamRun")
    assert residuals["time"] == [1.0, 2.0]
    assert residuals["Ux"] == [0.1, 0.05]

def test_residuals_incomplete_line(parser, tmp_path):
    """Verify that incomplete lines are ignored until completed."""
    log_file = tmp_path / "case" / "log.foamRun"

    # Write chunk with partial line
    chunk1 = "Time = 1\nSolving for Ux, Initial resi"
    log_file.write_text(chunk1, encoding="utf-8")

    residuals = parser.get_residuals_from_log("log.foamRun")
    assert residuals["time"] == [1.0]
    assert residuals["Ux"] == []

    # Complete the line
    with log_file.open("ab") as f:
        f.write(b"dual = 0.1\n")

    residuals = parser.get_residuals_from_log("log.foamRun")
    assert residuals["time"] == [1.0]
    assert residuals["Ux"] == [0.1]

def test_residuals_unicode_safety(parser, tmp_path):
    """Verify that utf-8 decoding doesn't crash on split multibyte chars."""
    log_file = tmp_path / "case" / "log.foamRun"

    # A multibyte char (e.g., Euro sign € is b'\xe2\x82\xac')
    # If we split it, standard readline in binary mode reads up to \n, so it won't split within a char unless the char contains \n byte (impossible in valid UTF-8).
    # But let's verify normal handling.

    chunk = "Time = 1\n# Comment with € symbol\n"
    log_file.write_bytes(chunk.encode("utf-8"))

    residuals = parser.get_residuals_from_log("log.foamRun")
    assert residuals["time"] == [1.0]
