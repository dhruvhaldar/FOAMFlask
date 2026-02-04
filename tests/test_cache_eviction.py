
import os
import pytest
from pathlib import Path
from backend.plots.realtime_plots import (
    _TIME_SERIES_CACHE, _TIME_DIRS_CACHE, _DIR_SCAN_CACHE,
    OpenFOAMFieldParser, clear_cache, MAX_CACHE_CASES
)

def test_cache_bounded_growth(tmp_path):
    # Clear caches to start fresh
    clear_cache()

    cases = []
    # Create 7 dummy cases (more than MAX_CACHE_CASES=5)
    for i in range(7):
        case_dir = tmp_path / f"case_{i}"
        case_dir.mkdir()

        # Create two time directories to ensure caching
        (case_dir / "0.1").mkdir()
        p_file = case_dir / "0.1" / "p"
        p_file.write_text("class volScalarField;\ninternalField uniform 1;")

        (case_dir / "0.2").mkdir()
        p_file_2 = case_dir / "0.2" / "p"
        p_file_2.write_text("class volScalarField;\ninternalField uniform 2;")

        cases.append(case_dir)

    # Access data for each case
    for idx, case_dir in enumerate(cases):
        parser = OpenFOAMFieldParser(case_dir)
        parser.get_all_time_series_data()

        # Check size incrementally
        current_size = len(_TIME_SERIES_CACHE)
        expected_size = min(idx + 1, MAX_CACHE_CASES)
        assert current_size == expected_size, f"Cache size mismatch at index {idx}. Expected {expected_size}, got {current_size}"

    # Verify final state
    assert len(_TIME_SERIES_CACHE) == MAX_CACHE_CASES

    # Verify LRU behavior: cases[0] and cases[1] should have been evicted
    # cases[2]...cases[6] should be present (5 items)
    assert str(cases[0]) not in _TIME_SERIES_CACHE
    assert str(cases[1]) not in _TIME_SERIES_CACHE
    assert str(cases[2]) in _TIME_SERIES_CACHE
    assert str(cases[6]) in _TIME_SERIES_CACHE

    # Also verify that clear_cache was called for evicted cases
    # _TIME_DIRS_CACHE should also be cleaned up
    assert len(_TIME_DIRS_CACHE) == MAX_CACHE_CASES
    assert str(cases[0]) not in _TIME_DIRS_CACHE
    assert str(cases[6]) in _TIME_DIRS_CACHE
