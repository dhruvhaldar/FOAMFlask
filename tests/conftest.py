"""
Pytest configuration and fixtures for FOAMFlask tests.
"""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from flask import Flask

# Add the project root to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

# Import the app after adding the project root to the path
import app as flask_app


@pytest.fixture(scope="module")
def app() -> Flask:
    """Create and configure a new app instance for each test module."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure the app for testing
        test_config = {
            'TESTING': True,
            'SECRET_KEY': 'test',
            'CASE_ROOT': temp_dir,
            'DOCKER_IMAGE': 'test-image',
            'OPENFOAM_VERSION': 'test-version'
        }
        
        # Create a test client using the Flask application configured for testing
        with flask_app.app.test_client() as testing_client:
            # Establish an application context before running the tests
            with flask_app.app.app_context():
                yield testing_client


@pytest.fixture
def client(app) -> Flask:
    """A test client for the app."""
    return app


@pytest.fixture
def runner(app) -> Flask.test_cli_runner:
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def test_case_dir(tmp_path):
    """Create a test case directory structure."""
    case_dir = tmp_path / "test_case"
    case_dir.mkdir()
    
    # Create a simple controlDict file
    (case_dir / "system").mkdir()
    (case_dir / "system" / "controlDict").write_text("""
    application     simpleFoam;
    startFrom       startTime;
    startTime       0;
    stopAt          endTime;
    endTime         0.1;
    deltaT          0.005;
    writeControl    timeStep;
    writeInterval   1;
    purgeWrite      0;
    writeFormat     ascii;
    writePrecision  6;
    writeCompression off;
    timeFormat      general;
    timePrecision   6;
    runTimeModifiable true;
    """)
    
    # Create a simple log file
    (case_dir / "log").mkdir()
    (case_dir / "log" / "simpleFoam").write_text("""
    Time = 0.1
    
    smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 1e-6, No Iterations 3
    smoothSolver:  Solving for Uy, Initial residual = 0.2, Final residual = 1e-6, No Iterations 3
    smoothSolver:  Solving for Uz, Initial residual = 0.3, Final residual = 1e-6, No Iterations 3
    """)
    
    return case_dir
