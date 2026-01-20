import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["ENABLE_CSRF"] = False  # Disable CSRF for testing
    with app.test_client() as client:
        yield client

def test_slice_placeholder(client):
    response = client.post("/api/slice/create", json={"parent_id": "123"})
    assert response.status_code == 501
    data = response.get_json()
    assert data["status"] == "coming_soon"
    assert "Slice" in data["message"]
    # Check if parent_id was processed
    assert data["details"]["parent_id"] == "123"

def test_streamline_placeholder(client):
    response = client.post("/api/streamline/create", json={"parent_id": "456"})
    assert response.status_code == 501
    data = response.get_json()
    assert data["status"] == "coming_soon"
    assert "Streamline" in data["message"]
    assert data["details"]["parent_id"] == "456"

def test_surface_projection_placeholder(client):
    response = client.post("/api/surface_projection/create", json={"parent_id": "789"})
    assert response.status_code == 501
    data = response.get_json()
    assert data["status"] == "coming_soon"
    assert "Surface projection" in data["message"]
    assert data["details"]["parent_id"] == "789"
