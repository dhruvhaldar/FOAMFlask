
import pytest
from app import app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_sensitive_endpoints_no_store(client):
    """Test that sensitive JSON endpoints have no-store cache control."""
    endpoints = [
        '/get_case_root',
        '/api/startup_status',
        '/get_docker_config',
        '/api/cases/list'
    ]

    # Mock necessary internals for some endpoints to return 200
    with patch('app.CASE_ROOT', '/tmp/test'):
        for endpoint in endpoints:
            response = client.get(endpoint)
            # We expect 200 OK or 503 (if docker missing) or empty lists, but Content-Type should be JSON
            # Even error responses (JSON) should not be cached if they contain sensitive info path

            # Check if JSON
            if response.mimetype == 'application/json':
                assert response.headers['Cache-Control'] == 'no-store, max-age=0', f"Endpoint {endpoint} missing no-store"

def test_data_endpoints_revalidate(client):
    """Test that data endpoints with ETag/Last-Modified have no-cache (revalidate)."""
    # We need to mock an endpoint that returns ETag.
    # /api/plot_data does this if parsing succeeds.

    mock_parser = MagicMock()
    # Return valid data so it generates ETag
    mock_parser.get_time_directories.return_value = ["0", "0.1"]
    mock_parser.get_all_time_series_data.return_value = {"time": [0, 0.1], "p": [1, 2]}

    with patch('app.OpenFOAMFieldParser', return_value=mock_parser), \
         patch('app.CASE_ROOT', '/tmp/test'), \
         patch('pathlib.Path.exists', return_value=True), \
         patch('os.stat') as mock_stat:

        # Mock stats for ETag generation
        mock_stat_result = MagicMock()
        mock_stat_result.st_mtime = 1000.0
        mock_stat.return_value = mock_stat_result

        response = client.get('/api/plot_data?tutorial=test')

        assert response.status_code == 200
        assert 'ETag' in response.headers
        assert response.headers['Cache-Control'] == 'no-cache', "Data endpoint missing no-cache"

def test_static_files_public_cache(client):
    """Test that static files do NOT have no-store (Flask defaults apply)."""
    # We need a static file. favicon.ico is served by a route.
    # But usually static files are served via /static/
    # Let's try favicon.ico since it has a specific route

    with patch('app.send_from_directory') as mock_send:
        # Mock response from send_from_directory
        mock_resp = app.response_class("image", mimetype='image/vnd.microsoft.icon')
        # Flask's send_from_directory sets Cache-Control usually
        mock_resp.headers['Cache-Control'] = 'public, max-age=43200'
        mock_send.return_value = mock_resp

        response = client.get('/favicon.ico')

        # It should NOT be overwritten because mimetype is not application/json
        assert response.headers['Cache-Control'] == 'public, max-age=43200'

def test_html_response_untouched(client):
    """Test that HTML responses are not affected."""
    # / returns HTML
    with patch('app.get_tutorials', return_value=[]):
        response = client.get('/')
        assert response.mimetype == 'text/html'
        # Should not have no-store (unless we added it for HTML too, but code said mimetype==application/json)
        assert 'Cache-Control' not in response.headers or 'no-store' not in response.headers['Cache-Control']
