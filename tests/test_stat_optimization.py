import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import logging

# Configure logger to suppress output during tests
logging.basicConfig(level=logging.ERROR)

from backend.plots.realtime_plots import OpenFOAMFieldParser, _FILE_CACHE

# Setup mock data
@pytest.fixture
def parser(tmp_path):
    # Create dummy case structure
    case_dir = tmp_path / "case"
    case_dir.mkdir()

    # Create time directories 0, 1, 2, 3
    for t in ["0", "1", "2", "3"]:
        t_dir = case_dir / t
        t_dir.mkdir()
        # Create scalar field 'p'
        p_file = t_dir / "p"
        # Must include class volScalarField for discovery
        content = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2012                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 100;

boundaryField
{
}

// ************************************************************************* //
"""
        p_file.write_text(content)

    return OpenFOAMFieldParser(case_dir)

def test_stat_calls_reduction(parser):
    # Clear cache
    _FILE_CACHE.clear()

    # 1. First call - Population
    real_stat = Path.stat

    with patch('pathlib.Path.stat', autospec=True) as mock_stat:
        def side_effect(self, *args, **kwargs):
            return real_stat(self, *args, **kwargs)

        mock_stat.side_effect = side_effect

        # Call get_all_time_series_data for last 4 points
        data = parser.get_all_time_series_data(max_points=4)

        # Verify data is loaded
        assert len(data['p']) == 4
        assert data['p'] == [100.0, 100.0, 100.0, 100.0]

        # Count stat calls on 'p' files
        p_calls_initial = 0
        for call in mock_stat.mock_calls:
            if call.args and str(call.args[0]).endswith('p'):
                p_calls_initial += 1

        print(f"Initial stat calls for 'p': {p_calls_initial}")
        # Note: field_path.exists() calls stat() internally too!
        # So we might see double calls (once for exists(), once for stat() inside parse_scalar_field)
        # With optimization, this should be very low (ideally 1 for the latest file, or 0 if we passed known_mtime correctly everywhere)
        # But let's check what we got.
        # In the optimization:
        # get_all_time_series_data uses os.scandir for discovery.
        # Then it iterates time dirs.
        # For historical time dirs:
        # It calls parse_scalar_field(check_mtime=False).
        # parse_scalar_field checks cache. Empty.
        # Then it skips stat.
        # Then it reads file.
        # So 0 stat calls for historical files?
        # For latest time dir:
        # It calls parse_scalar_field(check_mtime=True).
        # It calls stat().

        # So we expect 1 stat call for the latest file 'p'.
        assert p_calls_initial <= 2

    # 2. Second call - Cached
    with patch('pathlib.Path.stat', autospec=True) as mock_stat:
        mock_stat.side_effect = side_effect

        data = parser.get_all_time_series_data(max_points=4)

        assert len(data['p']) == 4

        p_calls_cached = 0
        for call in mock_stat.mock_calls:
            if call.args and str(call.args[0]).endswith('p'):
                p_calls_cached += 1

        print(f"Cached stat calls for 'p': {p_calls_cached}")

        # Should be minimal
        assert p_calls_cached <= 2
