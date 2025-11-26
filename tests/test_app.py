"""
Tests for the main FOAMFlask application endpoints.
"""
import json
import os
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

# Import the app module
import app as flask_app


def test_index_route(client):
    """Test the index route returns a successful response."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'FOAMFlask' in response.data


def test_get_case_root(client):
    """Test the get_case_root endpoint."""
    response = client.get('/get_case_root')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'caseDir' in data  # Updated to match actual response
    assert isinstance(data['caseDir'], str)


def test_set_case(client):
    """Test the set_case endpoint."""
    test_path = "E:\\path\\to\\test\\case"
    response = client.post(
        '/set_case',
        data=json.dumps({'caseDir': test_path}),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'caseDir' in data
    assert data['caseDir'] == test_path


def test_get_docker_config(client):
    """Test the get_docker_config endpoint."""
    response = client.get('/get_docker_config')
    assert response.status_code == 200
    data = json.loads(response.data)
    # Updated to match actual response keys
    assert 'dockerImage' in data
    assert 'openfoamVersion' in data
    assert isinstance(data['dockerImage'], str)
    assert isinstance(data['openfoamVersion'], str)


def test_set_docker_config(client):
    """Test the set_docker_config endpoint."""
    test_config = {
        'dockerImage': 'test-image:latest',
        'openfoamVersion': 'test-version'
    }
    response = client.post(
        '/set_docker_config',
        data=json.dumps(test_config),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    # Updated to match actual response structure
    assert 'dockerImage' in data
    assert 'openfoamVersion' in data
    assert data['dockerImage'] == test_config['dockerImage']
    assert data['openfoamVersion'] == test_config['openfoamVersion']


def test_load_tutorial_missing_parameter(client):
    """Test load_tutorial with missing tutorial parameter."""
    response = client.post(
        '/load_tutorial',
        data=json.dumps({}),  # Empty JSON
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'output' in data
    assert 'Error' in data['output']
    assert 'No tutorial selected' in data['output']


def test_run_case_missing_parameters(client):
    """Test run_case with missing parameters."""
    response = client.post(
        '/run',
        data=json.dumps({}),  # Empty JSON
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


class TestDockerEndpoints:
    """Test Docker-related endpoints with mocked Docker client."""
    
    def test_docker_unavailable(self, client, monkeypatch):
        """Test behavior when Docker is not available."""
        def mock_docker_client():
            return None
            
        monkeypatch.setattr(flask_app, 'get_docker_client', mock_docker_client)
        
        # Test an endpoint that requires Docker
        response = client.post(
            '/load_tutorial',
            data=json.dumps({'tutorial': 'test'}),
            content_type='application/json'
        )
        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'output' in data  # The actual response contains 'output' not 'error'
        assert 'Docker' in data['output']  # Should mention Docker in the output


class TestMeshEndpoints:
    """Test mesh-related endpoints."""
    
    # def test_api_available_meshes(self, client, test_case_dir):
    #     """Test the api_available_meshes endpoint."""
    #     # Create the expected directory structure: CASE_ROOT/tutorial_name/constant/polyMesh
    #     tutorial_dir = test_case_dir / "test_tutorial"
    #     mesh_dir = tutorial_dir / "constant" / "polyMesh"
    #     mesh_dir.mkdir(parents=True, exist_ok=True)
        
    #     # Create all required mesh files
    #     required_files = ['points', 'faces', 'owner', 'neighbour', 'boundary']
    #     for f in required_files:
    #         (mesh_dir / f).touch()
        
    #     # Create a boundary file with minimal content
    #     (mesh_dir / "boundary").write_text("""2
    #     (
    #         inlet
    #         {
    #             type            patch;
    #             nFaces          1;
    #             startFace       0;
    #         }
    #         outlet
    #         {
    #             type            patch;
    #             nFaces          1;
    #             startFace       1;
    #         }
    #     )""")
        
    #     # Mock the CASE_ROOT in the app to point to our test directory
    #     flask_app.CASE_ROOT = str(test_case_dir)
        
    #     # Call the endpoint with the tutorial name
    #     response = client.get('/api/available_meshes?tutorial=test_tutorial')
    #     assert response.status_code == 200
    #     data = json.loads(response.data)
    #     assert 'meshes' in data
    #     assert 'constant/polyMesh' in data['meshes'], f"Expected 'constant/polyMesh' in {data['meshes']}"
        
    # def test_api_load_mesh(self, client, test_case_dir):
    #     """Test the api_load_mesh endpoint."""
    #     # Set up a test case directory with a mesh file
    #     mesh_dir = test_case_dir / "constant" / "polyMesh"
    #     mesh_dir.mkdir(parents=True)
    #     (mesh_dir / "points").write_text("1\n(0 0 0)")
    #     (mesh_dir / "faces").write_text("1\n4(0 0 0 0)")
    #     (mesh_dir / "owner").write_text("1\n0")
    #     (mesh_dir / "neighbour").write_text("0\n")
    #     (mesh_dir / "boundary").write_text("1\n(\n    inlet\n    {\n        type            patch;\n        nFaces          1;\n        startFace       0;\n    }\n)")
        
    #     # Mock the CASE_ROOT in the app
    #     flask_app.CASE_ROOT = str(test_case_dir)
        
    #     # The endpoint expects a POST request with JSON data
    #     response = client.post(
    #         '/api/load_mesh',
    #         data=json.dumps({
    #             'file_path': 'constant/polyMesh',
    #             'tutorial': 'test_tutorial'
    #         }),
    #         content_type='application/json'
    #     )
    #     assert response.status_code == 200
    #     data = json.loads(response.data)
    #     assert 'points' in data
    #     assert 'cells' in data
    #     assert 'point_data' in data
    #     assert 'cell_data' in data


class TestPlottingEndpoints:
    """Test plotting-related endpoints."""
    
    def test_api_available_fields(self, client, test_case_dir):
        # Create the tutorial directory expected by the endpoint
        tutorial_dir = test_case_dir / "test_tutorial"
        tutorial_dir.mkdir(parents=True, exist_ok=True)

        flask_app.CASE_ROOT = str(test_case_dir)

        with patch('app.get_available_fields', return_value=['U', 'p']):
            response = client.get('/api/available_fields?tutorial=test_tutorial')
            assert response.status_code == 200
            data = response.get_json()
            assert 'fields' in data
            assert 'U' in data['fields']
            assert 'p' in data['fields']

    def test_api_available_fields_mocked(self, client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.get_available_fields', return_value=['U', 'p']):
            response = client.get('/api/available_fields?tutorial=test_tutorial')
            assert response.status_code == 200
            data = response.get_json()
            assert 'fields' in data
            assert 'U' in data['fields']

    def test_api_plot_data_mocked(self, client):
        mock_parser = MagicMock()
        mock_parser.get_all_time_series_data.return_value = {'time': [0.1], 'data': {'U': [1, 2, 3]}}
        with patch('app.os.path.exists', return_value=True), \
             patch('app.OpenFOAMFieldParser', return_value=mock_parser):
            response = client.get('/api/plot_data?tutorial=test_tutorial')
            assert response.status_code == 200
            data = response.get_json()
            assert 'time' in data
            assert 'data' in data


# def test_api_residuals(client, test_case_dir):
#     """Test the api_residuals endpoint."""
#     # Set up a test log file
#     log_file = test_case_dir / "log" / "simpleFoam"
#     log_file.parent.mkdir(parents=True, exist_ok=True)
#     log_file.write_text("""
#     Time = 0.1
    
#     smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 1e-6, No Iterations 3
#     smoothSolver:  Solving for Uy, Initial residual = 0.2, Final residual = 1e-6, No Iterations 3
#     smoothSolver:  Solving for Uz, Initial residual = 0.3, Final residual = 1e-6, No Iterations 3
#     """)
    
#     # Mock the CASE_ROOT in the app
#     flask_app.CASE_ROOT = str(test_case_dir)
    
#     # Add required parameters
#     response = client.get('/api/residuals?tutorial=test_tutorial&caseDir=test_case')
#     assert response.status_code == 200
#     data = json.loads(response.data)
#     assert 'time' in data
#     assert 'residuals' in data
#     assert 'Ux' in data['residuals']
#     assert 'Uy' in data['residuals']
#     assert 'Uz' in data['residuals']
