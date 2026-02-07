import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["ENABLE_CSRF"] = False  # Disable CSRF for testing
    with app.test_client() as client:
        yield client

def test_slice_placeholder(client, mocker):
    # Mock SliceVisualizer.process to return expected result
    mocker.patch('backend.post.slice.SliceVisualizer.process', return_value={"parent_id": "123"})

    response = client.post("/api/slice/create", json={"parent_id": "123"})
    assert response.status_code == 501
    data = response.get_json()
    assert data["status"] == "coming_soon"
    assert "Slice" in data["message"]
    # Check if parent_id was processed
    assert data["details"]["parent_id"] == "123"

def test_streamline_placeholder(client, mocker):
    mocker.patch('backend.post.streamline.StreamlineVisualizer.process', return_value={"parent_id": "456"})
    response = client.post("/api/streamline/create", json={"parent_id": "456"})
    assert response.status_code == 501
    data = response.get_json()
    assert data["status"] == "coming_soon"
    assert "Streamline" in data["message"]
    assert data["details"]["parent_id"] == "456"

def test_surface_projection_placeholder(client, mocker):
    mocker.patch('backend.post.surface_projection.SurfaceProjectionVisualizer.process', return_value={"parent_id": "789"})
    response = client.post("/api/surface_projection/create", json={"parent_id": "789"})
    assert response.status_code == 501
    data = response.get_json()
    assert data["status"] == "coming_soon"
    assert "Surface projection" in data["message"]
    assert data["details"]["parent_id"] == "789"
