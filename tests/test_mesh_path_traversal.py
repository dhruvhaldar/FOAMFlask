import pytest
import json
from app import app, CASE_ROOT
from pathlib import Path

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_mesh_path_traversal(client):
    # Try to access /etc/passwd or app.py
    target_file = Path("app.py").resolve()

    payload = {
        "file_path": str(target_file),
        "width": 100,
        "height": 100
    }

    response = client.post('/api/mesh_screenshot',
                          data=json.dumps(payload),
                          content_type='application/json')

    # Assert that the request was blocked with 400 Bad Request
    assert response.status_code == 400

    # Check error message
    data = json.loads(response.data)
    assert "error" in data
    assert "Access denied" in data["error"] or "Invalid path" in data["error"]
