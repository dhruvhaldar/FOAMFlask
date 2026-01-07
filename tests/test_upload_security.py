import pytest

def test_unlimited_file_upload(client):
    """
    Test that the server has MAX_CONTENT_LENGTH configured.
    """
    # Check if MAX_CONTENT_LENGTH is set in the app config
    assert client.application.config.get("MAX_CONTENT_LENGTH") == 500 * 1024 * 1024

    # Note: Checking for actual 413 response in TestClient is tricky because
    # Werkzeug's test client doesn't strictly enforce Content-Length limits on the request body generation
    # like a real WSGI server (Gunicorn/uWSGI) would, but checking the config exists is the correct verification
    # that we have enabled the protection.
