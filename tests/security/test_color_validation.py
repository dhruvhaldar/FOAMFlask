import pytest
from backend.utils import is_safe_color

class TestIsSafeColor:
    def test_valid_colors(self):
        valid_colors = [
            "red",
            "lightblue",
            "tab:blue",
            "viridis",
            "#FFF",
            "#FFFFFF",
            "#000000",
            "#123456",
            [1.0, 0.0, 0.0],
            (0, 255, 0),
            [0, 0, 0, 1],
            "viridis-r",
            "twilight_shifted"
        ]
        for color in valid_colors:
            assert is_safe_color(color), f"Expected safe: {color}"

    def test_invalid_colors(self):
        invalid_colors = [
            "<script>alert(1)</script>",
            "red; alert(1)",
            "'red'",
            '"red"',
            "rgb(0,0,0)", # Currently only lists/tuples or hex/names are allowed
            "rgba(0,0,0,1)",
            "url(javascript:alert(1))",
            {"r": 1}, # dicts not allowed
            None,
            123,
            " red", # leading space
            "red ", # trailing space
            "red/blue",
            "red&blue"
        ]
        for color in invalid_colors:
            assert not is_safe_color(color), f"Expected unsafe: {color}"

def test_api_view_geometry_unsafe_color(client, mocker):
    # Mock validate_geometry_path to avoid filesystem checks if needed,
    # but validation should fail before that.
    mocker.patch("app.validate_geometry_path", return_value="some/path.stl")

    response = client.post("/api/geometry/view", json={
        "caseName": "case",
        "filename": "file.stl",
        "color": "<script>"
    })
    assert response.status_code == 400
    assert "Invalid color format" in response.json["message"]

def test_api_mesh_interactive_unsafe_color(client):
    response = client.post("/api/mesh_interactive", json={
        "file_path": "file.stl",
        "color": "<script>"
    })
    assert response.status_code == 400
    assert "Invalid color format" in response.json["error"]

def test_api_mesh_screenshot_unsafe_color(client):
    response = client.post("/api/mesh_screenshot", json={
        "file_path": "file.stl",
        "color": "<script>"
    })
    assert response.status_code == 400
    assert "Invalid color format" in response.json["error"]

def test_create_contour_unsafe_colormap(client):
    response = client.post("/api/contours/create", json={
        "tutorial": "tut",
        "caseDir": "dir",
        "colormap": "<script>"
    })
    assert response.status_code == 400
    assert "Invalid colormap format" in response.json["error"]
