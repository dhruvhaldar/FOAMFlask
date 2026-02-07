import pytest
from unittest.mock import MagicMock, patch
import json
from pathlib import Path

class TestAppExtended:
    def test_api_create_case_success(self, client):
        with patch('backend.case.manager.CaseManager.create_case_structure', return_value={"success": True, "path": "/path"}), \
             patch('app.CASE_ROOT', "/tmp/cases"):
            response = client.post('/api/case/create', json={"caseName": "newcase"})
            assert response.status_code == 200
            assert response.json["success"] is True

    def test_api_create_case_missing_name(self, client):
        response = client.post('/api/case/create', json={})
        assert response.status_code == 400
        assert "No case name" in response.json["message"]

    def test_api_create_case_invalid_name(self, client):
        response = client.post('/api/case/create', json={"caseName": 123})
        assert response.status_code == 400
        assert "must be a string" in response.json["message"]

    def test_api_create_case_no_root(self, client):
        with patch('app.CASE_ROOT', None):
            response = client.post('/api/case/create', json={"caseName": "newcase"})
            assert response.status_code == 500
            assert "Case root not set" in response.json["message"]

    def test_api_create_case_invalid_path(self, client):
        with patch('app.CASE_ROOT', "/tmp/cases"):
            response = client.post('/api/case/create', json={"caseName": "../outside"})
            assert response.status_code == 400
            assert "Access denied" in response.json["message"]

    def test_api_upload_geometry_success(self, client, tmp_path):
        with patch('backend.geometry.manager.GeometryManager.upload_stl', return_value={"success": True}), \
             patch('app.CASE_ROOT', str(tmp_path)):

            data = {'file': (MagicMock(), 'test.stl'), 'caseName': 'case'}
            response = client.post('/api/geometry/upload', data=data, content_type='multipart/form-data')
            assert response.status_code == 200
            assert response.json["success"] is True

    def test_api_upload_geometry_no_file(self, client):
        response = client.post('/api/geometry/upload', data={}, content_type='multipart/form-data')
        assert response.status_code == 400
        assert "No file part" in response.json["message"]

    def test_api_upload_geometry_no_filename(self, client):
        data = {'file': (MagicMock(), '')}
        response = client.post('/api/geometry/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert "No selected file" in response.json["message"]

    def test_api_meshing_run_success(self, client):
        with patch('backend.meshing.runner.MeshingRunner.run_meshing_command', return_value={"success": True}), \
             patch('app.CASE_ROOT', "/tmp/cases"), \
             patch('app.get_docker_client'), \
             patch('app.validate_safe_path', return_value=Path("/tmp/cases/case")):

            response = client.post('/api/meshing/run', json={"caseName": "case", "command": "blockMesh"})
            assert response.status_code == 200
            assert response.json["success"] is True

    def test_api_meshing_run_invalid_command(self, client):
        response = client.post('/api/meshing/run', json={"caseName": "case", "command": "rm -rf"})
        assert response.status_code == 400
        assert "Invalid command" in response.json["message"]

    def test_api_plot_data_cache_hit(self, client):
        # Test 304 response
        with patch('app.CASE_ROOT', "/tmp/cases"), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('app.OpenFOAMFieldParser') as mock_parser, \
             patch('os.stat') as mock_stat:

            # Setup mock stat results
            mock_stat_result = MagicMock()
            mock_stat_result.st_mtime = 1000
            mock_stat.return_value = mock_stat_result

            # Mock parser returning time dirs
            mock_parser.return_value.get_time_directories.return_value = ["0", "1"]

            # Set headers
            etag = '"1000-1000"'
            response = client.get('/api/plot_data?tutorial=case', headers={"If-None-Match": etag})
            assert response.status_code == 304

    def test_api_plot_data_cache_miss(self, client):
        with patch('app.CASE_ROOT', "/tmp/cases"), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('app.OpenFOAMFieldParser') as mock_parser, \
             patch('os.stat') as mock_stat:

            mock_stat_result = MagicMock()
            mock_stat_result.st_mtime = 2000
            mock_stat.return_value = mock_stat_result

            mock_parser.return_value.get_time_directories.return_value = ["0", "1"]
            mock_parser.return_value.get_all_time_series_data.return_value = {}

            etag = '"1000-1000"' # Old etag
            response = client.get('/api/plot_data?tutorial=case', headers={"If-None-Match": etag})
            assert response.status_code == 200
            assert response.headers["ETag"] == '"2000-2000"'

    def test_run_foamtovtk_streaming(self, client):
        with patch('app.get_docker_client') as mock_docker, \
             patch('app.CASE_ROOT', "/tmp/cases"), \
             patch('app.validate_safe_path'):

            mock_container = MagicMock()
            mock_container.logs.return_value = [b"line1\n", b"line2\n"]
            mock_docker.return_value.containers.run.return_value = mock_container

            response = client.post('/run_foamtovtk', json={"tutorial": "case", "caseDir": "/tmp/cases/case"})
            assert response.status_code == 200
            data = response.data.decode()
            assert "line1" in data
            assert "line2" in data

    def test_run_foamtovtk_error(self, client):
        with patch('app.get_docker_client') as mock_docker, \
             patch('app.CASE_ROOT', "/tmp/cases"), \
             patch('app.validate_safe_path'):

            mock_docker.return_value.containers.run.side_effect = Exception("Docker failed")

            response = client.post('/run_foamtovtk', json={"tutorial": "case", "caseDir": "/tmp/cases/case"})
            assert response.status_code == 200
            # Should contain sanitized error
            assert "An internal server error occurred" in response.data.decode()
