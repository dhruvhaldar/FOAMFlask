
import pytest
from unittest.mock import patch, MagicMock
from backend.plots.realtime_plots import OpenFOAMFieldParser

def test_residuals_parsing_optimization():
    # Content with spaces - this is the problematic case where manual parsing fails
    # Standard format: "Solving for Ux, Initial residual = 0.123, Final residual = ..."
    # "Initial residual =" is followed by a space, then value.
    content = [
        b"Time = 1\n",
        b"Solving for Ux, Initial residual = 0.123, Final residual = 0.001, No Iterations 1\n"
    ]

    # Mock open
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.__iter__.return_value = iter(content)
        mock_open.return_value = mock_file

        # Mock os.open/fdopen since the code uses low-level IO
        with patch("os.open") as mock_os_open, \
             patch("os.fstat") as mock_fstat, \
             patch("os.fdopen") as mock_fdopen:

            mock_os_open.return_value = 10
            mock_stat = MagicMock()
            mock_stat.st_mtime = 100
            mock_stat.st_size = sum(len(c) for c in content)
            mock_fstat.return_value = mock_stat

            mock_fd_file = MagicMock()
            mock_fd_file.__enter__.return_value = mock_fd_file
            mock_fd_file.__iter__.return_value = iter(content)
            mock_fdopen.return_value = mock_fd_file

            parser = OpenFOAMFieldParser("/tmp/test")

            # Patch regex to spy on calls
            with patch("backend.plots.realtime_plots.RESIDUAL_REGEX_BYTES") as mock_regex:
                # Mock search return value just in case fallback is triggered
                match = MagicMock()
                match.group.side_effect = [b"Ux", b"0.123"] # group(1), group(2)
                mock_regex.search.return_value = match

                residuals = parser.get_residuals_from_log()

                # Check results - verify parsing works (either via manual or regex)
                assert residuals["Ux"] == [0.123]

                # Verify regex usage
                # After fix: Should NOT be called
                assert mock_regex.search.call_count == 0, "Regex fallback triggered (Bug exists)"

if __name__ == "__main__":
    pytest.main([__file__])
