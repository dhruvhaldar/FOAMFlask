#!/usr/bin/env python3
"""
Basic tests to demonstrate code coverage.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app module
import app


def test_app_imports():
    """Test that the app module can be imported."""
    assert app is not None
    assert hasattr(app, 'app')


def test_flask_app_exists():
    """Test that Flask app exists."""
    assert hasattr(app, 'app')
    flask_app = app.app
    assert flask_app is not None


def test_endpoints_exist():
    """Test that main endpoints are defined."""
    flask_app = app.app
    
    # Get all routes
    routes = []
    for rule in flask_app.url_map.iter_rules():
        routes.append(rule.rule)
    
    # Check key endpoints exist
    expected_endpoints = [
        '/',
        '/get_case_root',
        '/get_docker_config',
        '/run',
        '/api/plot_data',
        '/api/residuals'
    ]
    
    for endpoint in expected_endpoints:
        assert endpoint in routes, f"Endpoint {endpoint} not found"


def test_config_values():
    """Test that configuration values exist."""
    assert hasattr(app, 'CASE_ROOT')
    assert hasattr(app, 'DOCKER_IMAGE')
    assert hasattr(app, 'OPENFOAM_VERSION')


if __name__ == "__main__":
    # Run tests
    test_app_imports()
    test_flask_app_exists()
    test_endpoints_exist()
    test_config_values()
    
    print("✅ All basic tests passed!")
