import pytest
import sys
from pathlib import Path

# Ensure the app module can be imported (assuming running from repo root or tests dir)
# Adjust path to include repo root
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

import app as flask_app

def test_secret_key_is_set():
    """Test that the Flask app has a secret key configured."""
    # Check that secret_key is set and not empty
    assert flask_app.app.secret_key is not None
    assert len(str(flask_app.app.secret_key)) > 0
