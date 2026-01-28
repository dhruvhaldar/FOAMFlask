import pytest
from app import is_safe_tutorial_path

def test_is_safe_tutorial_path_vulnerabilities():
    # These should now FAIL (return False) because they are insecure
    assert is_safe_tutorial_path("-argument") is False, "Expected -argument to be rejected"
    assert is_safe_tutorial_path("/absolute/path") is False, "Expected absolute path to be rejected"

def test_load_tutorial_injection(client):
    """
    Test that the load_tutorial endpoint correctly rejects paths starting with - or /
    Uses the client fixture from conftest.py which handles CSRF disabling.
    """
    # payload starting with -
    payload = {"tutorial": "-rf"}
    response = client.post('/load_tutorial', json=payload)

    assert response.status_code == 400
    assert b"Invalid tutorial path detected" in response.data

    # payload starting with /
    payload = {"tutorial": "/etc/passwd"}
    response = client.post('/load_tutorial', json=payload)

    assert response.status_code == 400
    assert b"Invalid tutorial path detected" in response.data
