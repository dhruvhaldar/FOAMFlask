
import pytest
from pathlib import Path
from backend.plots.realtime_plots import OpenFOAMFieldParser, _RESIDUALS_CACHE

@pytest.fixture(autouse=True)
def clear_cache():
    _RESIDUALS_CACHE.clear()
    yield
    _RESIDUALS_CACHE.clear()

def test_incremental_parsing_correctness(tmp_path):
    # 1. Create log file with initial data
    log_file = tmp_path / "log.foamRun"
    content1 = (
        b"Time = 1\n"
        b"Solving for Ux, Initial residual = 0.1, Final residual = 0.01, No Iterations 1\n"
        b"Solving for p, Initial residual = 0.2, Final residual = 0.02, No Iterations 1\n"
        b"ExecutionTime = 1 s\n"
    )
    log_file.write_bytes(content1)

    parser = OpenFOAMFieldParser(tmp_path)

    # 2. First parse
    residuals1 = parser.get_residuals_from_log()
    assert residuals1["time"] == [1.0]
    assert residuals1["Ux"] == [0.1]
    assert residuals1["p"] == [0.2]

    # 3. Append data
    content2 = (
        b"Time = 2\n"
        b"Solving for Ux, Initial residual = 0.05, Final residual = 0.005, No Iterations 1\n"
        b"Solving for p, Initial residual = 0.1, Final residual = 0.01, No Iterations 1\n"
        b"ExecutionTime = 2 s\n"
    )
    # Using open 'ab' to append
    with open(log_file, "ab") as f:
        f.write(content2)

    # 4. Second parse (incremental)
    residuals2 = parser.get_residuals_from_log()

    # Verify correctness
    assert residuals2["time"] == [1.0, 2.0]
    assert residuals2["Ux"] == [0.1, 0.05]
    assert residuals2["p"] == [0.2, 0.1]

    # Verify object identity (should be same list objects if extended in place,
    # but our new logic will still extend the same cached list objects)
    assert residuals1["time"] is residuals2["time"]

def test_partial_line_handling(tmp_path):
    log_file = tmp_path / "log.foamRun"

    # 1. Write data ending with incomplete line
    content = (
        b"Time = 1\n"
        b"Solving for Ux, Initial residual = 0.1, Final residual = 0.01\n" # Missing newline? No, valid line
        b"Solving for p, Initial " # Incomplete
    )
    log_file.write_bytes(content)

    parser = OpenFOAMFieldParser(tmp_path)
    residuals = parser.get_residuals_from_log()

    assert residuals["time"] == [1.0]
    assert residuals["Ux"] == [0.1]
    assert len(residuals["p"]) == 0 # p not parsed yet

    # 2. Complete the line and add more
    with open(log_file, "ab") as f:
        f.write(b"residual = 0.2, Final residual = 0.02\nTime = 2\n")

    residuals = parser.get_residuals_from_log()
    assert residuals["p"] == [0.2]
    assert residuals["time"] == [1.0, 2.0]

def test_dynamic_field_discovery(tmp_path):
    log_file = tmp_path / "log.foamRun"
    content = (
        b"Time = 1\n"
        b"Solving for CustomField, Initial residual = 0.5, Final residual = 0.05, No Iterations 1\n"
    )
    log_file.write_bytes(content)

    parser = OpenFOAMFieldParser(tmp_path)
    residuals = parser.get_residuals_from_log()

    assert "CustomField" in residuals
    assert residuals["CustomField"] == [0.5]
    assert residuals["time"] == [1.0]
