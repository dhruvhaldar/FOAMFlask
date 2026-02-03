import pytest
from unittest.mock import patch
from flask import Response
from app import app
import json

class TestCacheHeaders:

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        app.config["ENABLE_CSRF"] = False
        with app.test_client() as client:
            yield client

    def test_sensitive_json_cache_control(self, client):
        """Test that sensitive JSON endpoints (no validation headers) have Cache-Control: no-store."""
        response = client.get('/get_case_root')
        assert response.status_code == 200
        assert response.mimetype == 'application/json'

        cache_control = response.headers.get("Cache-Control")
        assert cache_control == "no-store, max-age=0"

    def test_static_file_cache_control(self, client):
        """Test that static files are NOT affected by the JSON cache policy."""
        # Static files are not application/json
        response = client.get('/static/js/foamflask_frontend.js')

        if response.status_code == 404:
            pytest.skip("Static file not found")

        cache_control = response.headers.get("Cache-Control")
        # Should be None (default) or at least not our restrictive policies
        # Flask/Werkzeug might add public/max-age depending on config, but definitely not no-store from us.
        # And since we restrict to application/json, it should be skipped.
        assert cache_control is None or "no-store" not in cache_control

    def test_json_with_etag_cache_control(self, client):
        """Test that JSON endpoints with ETag have Cache-Control: no-cache."""
        # Patch fast_jsonify in app.py to return a response with ETag
        # We use a context manager for the patch
        with patch('app.fast_jsonify') as mock_jsonify:
            resp = Response(b"{}", mimetype="application/json")
            resp.headers["ETag"] = '"123"'
            mock_jsonify.return_value = resp

            # Call an endpoint that uses fast_jsonify (api_startup_status is simple)
            response = client.get('/api/startup_status')

            assert response.status_code == 200
            assert response.headers.get("Cache-Control") == "no-cache"

    def test_json_with_last_modified_cache_control(self, client):
        """Test that JSON endpoints with Last-Modified have Cache-Control: no-cache."""
        with patch('app.fast_jsonify') as mock_jsonify:
            resp = Response(b"{}", mimetype="application/json")
            resp.headers["Last-Modified"] = 'Wed, 21 Oct 2015 07:28:00 GMT'
            mock_jsonify.return_value = resp

            response = client.get('/api/startup_status')

            assert response.status_code == 200
            assert response.headers.get("Cache-Control") == "no-cache"
