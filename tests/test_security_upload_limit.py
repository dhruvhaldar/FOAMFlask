
import pytest
from app import app

def test_max_content_length_set():
    """Verify that MAX_CONTENT_LENGTH is set to 500MB."""
    # It should be 500 * 1024 * 1024
    expected = 500 * 1024 * 1024
    assert app.config.get("MAX_CONTENT_LENGTH") == expected
