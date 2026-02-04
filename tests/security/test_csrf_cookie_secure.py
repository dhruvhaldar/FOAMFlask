import pytest
from app import app

class TestCsrfCookieSecure:
    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        app.config["ENABLE_CSRF"] = True
        with app.test_client() as client:
            yield client

    def test_https_request_sets_secure_cookie(self, client):
        """Test that HTTPS requests get a Secure cookie."""
        # Simulate HTTPS request by setting base_url or environ_overrides
        response = client.get('/', base_url='https://localhost')

        # Check for Set-Cookie header
        cookie = None
        for header in response.headers.getlist('Set-Cookie'):
            if 'csrf_token' in header:
                cookie = header
                break

        assert cookie is not None
        # It MUST have Secure now
        assert 'Secure' in cookie

    def test_http_request_sets_non_secure_cookie(self, client):
        """Test that HTTP requests get a non-Secure cookie."""
        response = client.get('/', base_url='http://localhost')

        cookie = None
        for header in response.headers.getlist('Set-Cookie'):
            if 'csrf_token' in header:
                cookie = header
                break

        assert cookie is not None
        assert 'Secure' not in cookie
