
import pytest
from unittest.mock import MagicMock, patch
import app

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    app.CASE_ROOT = "/tmp/mock_case_root"
    with app.app.test_client() as client:
        yield client

@patch("app.validate_safe_path")
@patch("app.check_cache")
@patch("app.OpenFOAMFieldParser")
def test_residuals_missing_log_optimization(mock_parser_cls, mock_check_cache, mock_validate_path, client):
    """
    Verify that get_residuals_from_log is NOT called when check_cache indicates file is missing.
    """
    # Setup
    mock_validate_path.return_value = MagicMock(exists=lambda: True)
    # Simulate missing file: check_cache returns (False, None, None)
    mock_check_cache.return_value = (False, None, None)

    # Mock parser instance
    mock_parser_instance = mock_parser_cls.return_value
    mock_parser_instance.get_residuals_from_log.return_value = {}

    # Action
    response = client.get("/api/residuals?tutorial=mock/tutorial")

    # Assertions
    assert response.status_code == 200
    assert response.json == {}

    # CRITICAL: Verify optimization - parser should NOT be instantiated or called
    # If check_cache returns None for stat, we should return immediately.
    # Currently (before optimization), this assertion will FAIL because the code proceeds to call parser.
    # After optimization, this assertion should PASS.

    # We check if get_residuals_from_log was called.
    # If optimization is working, it should NOT be called.
    # If optimization is missing, it WILL be called (and return {} from mock).
    if mock_parser_instance.get_residuals_from_log.called:
        pytest.fail("Optimization failed: get_residuals_from_log was called despite missing file")

@patch("app.validate_safe_path")
@patch("app.check_cache")
@patch("app.OpenFOAMFieldParser")
def test_residuals_existing_log(mock_parser_cls, mock_check_cache, mock_validate_path, client):
    """
    Verify that get_residuals_from_log IS called when file exists.
    """
    # Setup
    mock_validate_path.return_value = MagicMock(exists=lambda: True)

    # Simulate existing file
    mock_stat = MagicMock()
    mock_stat.st_mtime = 12345.0
    mock_check_cache.return_value = (False, "Wed, 21 Oct 2015 07:28:00 GMT", mock_stat)

    mock_parser_instance = mock_parser_cls.return_value
    expected_data = {"time": [0, 1], "p": [1e-5, 1e-6]}
    mock_parser_instance.get_residuals_from_log.return_value = expected_data

    # Action
    response = client.get("/api/residuals?tutorial=mock/tutorial")

    # Assertions
    assert response.status_code == 200
    assert response.json == expected_data

    # Verify parser was called with correct stat
    mock_parser_instance.get_residuals_from_log.assert_called_once_with(known_stat=mock_stat)
