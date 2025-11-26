"""
Tests for the main FOAMFlask application endpoints.
"""
import json
import os
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock, mock_open
from docker.errors import DockerException

# Import the app module
import app as flask_app

def test_index_route(client):
    """Test the index route returns a successful response."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'FOAMFlask' in response.data

def test_is_safe_command():
    """Test the is_safe_command function with various inputs."""
    # Test valid commands
    assert flask_app.is_safe_command("simple-command") is True
    assert flask_app.is_safe_command("command-with-dashes") is True
    assert flask_app.is_safe_command("command_with_underscores") is True
    assert flask_app.is_safe_command("command with spaces") is True
    assert flask_app.is_safe_command("command123") is True

    # Test invalid commands
    # Empty or None
    assert flask_app.is_safe_command("") is False
    assert flask_app.is_safe_command(None) is False
    assert flask_app.is_safe_command(123) is False  # Not a string

    # Test dangerous characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'", '%']
    for char in dangerous_chars:
        assert flask_app.is_safe_command(f"command{char}") is False, f"Failed for character: {char}"

    # Test command combinations
    assert flask_app.is_safe_command("command; rm -rf /") is False  # Command separator
    assert flask_app.is_safe_command("command && rm -rf /") is False  # Logical AND
    assert flask_app.is_safe_command("command || rm -rf /") is False  # Logical OR
    assert flask_app.is_safe_command("command | rm -rf /") is False  # Pipe
    assert flask_app.is_safe_command("command `rm -rf /`") is False  # Backticks
    assert flask_app.is_safe_command("command $(rm -rf /)") is False  # Command substitution
    assert flask_app.is_safe_command('command "dangerous"') is False  # Double quotes
    assert flask_app.is_safe_command("command 'dangerous'") is False  # Single quotes
    assert flask_app.is_safe_command("command<dangerous") is False  # Input redirection
    assert flask_app.is_safe_command("command>dangerous") is False  # Output redirection
    assert flask_app.is_safe_command("command(dangerous)") is False  # Parentheses

    # Test path traversal
    assert flask_app.is_safe_command("command ../../dangerous") is False
    assert flask_app.is_safe_command("command /etc/passwd") is True  # Allowed, handled by command validation
    assert flask_app.is_safe_command("command /etc/../etc/passwd") is False
    assert flask_app.is_safe_command("command ./../dangerous") is False
    assert flask_app.is_safe_command("command ~/dangerous") is True  # Tilde expansion is allowed

    # Test file descriptor redirection
    assert flask_app.is_safe_command("command 2>error.log") is False
    assert flask_app.is_safe_command("command 1>output.log") is False
    assert flask_app.is_safe_command("command 0<input.txt") is False
    assert flask_app.is_safe_command("command 10>file") is False  # Multi-digit file descriptor
    assert flask_app.is_safe_command("command 2>&1") is False  # Redirect stderr to stdout
    assert flask_app.is_safe_command("command 3>file 4<input") is False  # Multiple redirections
    assert flask_app.is_safe_command("command >file") is False  # Default stdout redirection
    assert flask_app.is_safe_command("command <input") is False  # Default stdin redirection

    # Test command substitution variations
    assert flask_app.is_safe_command("command_`inside`backticks") is False
    assert flask_app.is_safe_command("command_$(inside)parentheses") is False
    assert flask_app.is_safe_command("`only_backticks`") is False
    assert flask_app.is_safe_command("$(only_command_sub)") is False
    assert flask_app.is_safe_command("command_`echo test`_end") is False

    # Test background/foreground
    assert flask_app.is_safe_command("command &") is False
    assert flask_app.is_safe_command("command %") is False
    assert flask_app.is_safe_command("command &> /dev/null &") is False  # Common background pattern

    # Test length check
    long_command = "a" * 100
    assert flask_app.is_safe_command(long_command) is True
    assert flask_app.is_safe_command(long_command + "a") is False  # 101 characters
    assert flask_app.is_safe_command("x" * 1000) is False  # Very long command

    # Test mixed cases
    assert flask_app.is_safe_command("command; $(rm -rf /) && echo 'hacked'") is False
    assert flask_app.is_safe_command("command `echo test` > file") is False
    assert flask_app.is_safe_command("command $(cat /etc/passwd) | grep root") is False

def test_is_safe_script_name():
    """Test the is_safe_script_name function with various inputs."""
    # Test valid script names
    assert flask_app.is_safe_script_name("script.sh") is True
    assert flask_app.is_safe_script_name("test_script-1.2.3.py") is True
    assert flask_app.is_safe_script_name("UPPERCASE_SCRIPT") is True
    assert flask_app.is_safe_script_name("123_script.456") is True
    assert flask_app.is_safe_script_name("a" * 50) is True  # Max length

    # Test invalid script names
    # Empty or None
    assert flask_app.is_safe_script_name("") is False
    assert flask_app.is_safe_script_name(None) is False
    assert flask_app.is_safe_script_name(123) is False  # Not a string

    # Test invalid characters
    invalid_chars = ['!', '@', '#', '$', '$(','%', '`','^', '&', '*', '(', ')', '=', '+', 
                    '{', '}', '[', ']', ':', ';', "'", '"', ',', '<', '>', '?', '/', '\\']
    for char in invalid_chars:
        assert flask_app.is_safe_script_name(f"script{char}") is False, f"Failed for character: {char}"

    # Test path traversal attempts
    assert flask_app.is_safe_script_name("../malicious.sh") is False
    assert flask_app.is_safe_script_name("/etc/passwd") is False
    assert flask_app.is_safe_script_name("folder/script.sh") is False
    assert flask_app.is_safe_script_name("folder\\script.sh") is False
    assert flask_app.is_safe_script_name("..\\..\\malicious.sh") is False

    # Test hidden files
    assert flask_app.is_safe_script_name(".hidden") is False
    assert flask_app.is_safe_script_name("..hidden") is False  # Not actually hidden, just starts with dots
    assert flask_app.is_safe_script_name("file.") is True  # Ends with dot is allowed

    # Test length limits
    assert flask_app.is_safe_script_name("a" * 50) is True  # Max length
    assert flask_app.is_safe_script_name("a" * 51) is False  # Too long

    # Test edge cases
    assert flask_app.is_safe_script_name(" ") is False  # Whitespace only
    assert flask_app.is_safe_script_name("script with spaces.sh") is False  # Spaces not allowed
    assert flask_app.is_safe_script_name("script\twith\ttabs.sh") is False  # Tabs not allowed
    assert flask_app.is_safe_script_name("script\nwith\nnewlines.sh") is False  # Newlines not allowed

def test_is_safe_command_with_substitution_and_redirection():
    # Command substitution
    assert flask_app.is_safe_command("command_$(rm -rf /)") is False
    assert flask_app.is_safe_command("command `rm -rf /`") is False
    assert flask_app.is_safe_command("`only_backticks`") is False
    assert flask_app.is_safe_command("$(only_command_sub)") is False
    assert flask_app.is_safe_command("command normal") is True  # Control positive

    # File descriptor redirection
    assert flask_app.is_safe_command("command 2> error.log") is False
    assert flask_app.is_safe_command("command 1> output.log") is False
    assert flask_app.is_safe_command("command 0<input.txt") is False
    assert flask_app.is_safe_command("command 10> file") is False  # multi-digit fd
    assert flask_app.is_safe_command("command without redirection") is True  # Control positive

def test_load_config_no_file(tmp_path):
    # Patch CONFIG_FILE to a non-existent file path
    with patch('app.CONFIG_FILE', tmp_path / "nonexistent.json"):
        # Ensure file does not exist
        assert not os.path.exists(flask_app.CONFIG_FILE)
        config = flask_app.load_config()
        assert config["CASE_ROOT"] == os.path.abspath("tutorial_cases")
        assert config["DOCKER_IMAGE"] == "haldardhruv/ubuntu_noble_openfoam:v12"
        assert config["OPENFOAM_VERSION"] == "12"

def test_load_config_with_valid_file(tmp_path):
    config_file = tmp_path / "case_config.json"
    data = {
        "CASE_ROOT": "/custom/path",
        "DOCKER_IMAGE": "custom/image:latest",
        "OPENFOAM_VERSION": "13"
    }
    config_file.write_text(json.dumps(data), encoding="utf-8")

    with patch('app.CONFIG_FILE', str(config_file)):
        config = flask_app.load_config()
        # Should merge defaults and file content, but file data overrides defaults
        assert config["CASE_ROOT"] == "/custom/path"
        assert config["DOCKER_IMAGE"] == "custom/image:latest"
        assert config["OPENFOAM_VERSION"] == "13"

def test_load_config_with_invalid_json(tmp_path, caplog):
    config_file = tmp_path / "case_config.json"
    # Write invalid JSON content
    config_file.write_text("{invalid json}", encoding="utf-8")

    with patch('app.CONFIG_FILE', str(config_file)):
        with caplog.at_level("WARNING"):
            config = flask_app.load_config()
            # Should return defaults on JSONDecodeError
            assert config["CASE_ROOT"] == os.path.abspath("tutorial_cases")
            assert any("Could not load config file" in record.message for record in caplog.records)

def test_load_config_with_os_error(monkeypatch):
    # Patch open() to raise OSError
    mocked_open = mock_open()
    def raise_os_error(*args, **kwargs):
        raise OSError("Permission denied")

    with patch('app.CONFIG_FILE', 'dummy_path.json'):
        with patch('builtins.open', raise_os_error):
            result = flask_app.load_config()
            # Should return defaults on OSError
            assert result["CASE_ROOT"] == os.path.abspath("tutorial_cases")

def test_save_config_success(tmp_path):
    # Use a real temporary file for the config file
    config_file = tmp_path / "case_config.json"

    with patch('app.CONFIG_FILE', str(config_file)), \
         patch('app.load_config', return_value={"CASE_ROOT": "/default/path"}):
        
        updates = {"DOCKER_IMAGE": "new-image:latest", "OPENFOAM_VERSION": "13"}
        
        result = flask_app.save_config(updates)
        assert result is True

        # Check file exists and contents include updates merged with loaded config
        with open(config_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["CASE_ROOT"] == "/default/path"
            assert saved_data["DOCKER_IMAGE"] == "new-image:latest"
            assert saved_data["OPENFOAM_VERSION"] == "13"

def test_save_config_oserror(monkeypatch):
    # Simulate OSError on file open
    def mock_open_fail(*args, **kwargs):
        raise OSError("Disk full")

    with patch('app.CONFIG_FILE', 'dummy_path.json'), \
         patch('app.load_config', return_value={"CASE_ROOT": "/default"}), \
         patch('builtins.open', mock_open_fail), \
         patch('app.logger') as mock_logger:
        
        updates = {"DOCKER_IMAGE": "fail-image"}
        result = flask_app.save_config(updates)
        assert result is False
        # Verify error logged
        mock_logger.error.assert_called()

def test_save_config_typeerror(monkeypatch):
    # Simulate TypeError on json.dump (e.g., unserializable type)
    class DummyFile:
        def write(self, _):
            raise TypeError("Cannot serialize")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_open(*args, **kwargs):
        return DummyFile()

    with patch('app.CONFIG_FILE', 'dummy_path.json'), \
         patch('app.load_config', return_value={"CASE_ROOT": "/default"}), \
         patch('builtins.open', mock_open), \
         patch('app.logger') as mock_logger:

        updates = {"DOCKER_IMAGE": object()}  # object() is unserializable
        result = flask_app.save_config(updates)
        assert result is False
        mock_logger.error.assert_called()

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

    def test_get_docker_client_success(monkeypatch):
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        with patch('app.docker.from_env', return_value=mock_client):
            # Reset cached client
            flask_app.docker_client = None

            client = flask_app.get_docker_client()
            # Should return the client instance
            assert client == mock_client
            mock_client.ping.assert_called_once()

    def test_get_docker_client_cached(monkeypatch):
        # Setup a cached client in global variable
        mock_client = MagicMock()
        flask_app.docker_client = mock_client

        client = flask_app.get_docker_client()
        # Should return the cached client directly without calling docker.from_env
        assert client == mock_client

    def test_get_docker_client_docker_exception(monkeypatch):
        # Mock docker.from_env to raise DockerException (simulate Docker not running)
        with patch('app.docker.from_env', side_effect=DockerException("Connection error")), \
            patch('app.logger') as mock_logger:
            
            # Reset cached client
            flask_app.docker_client = None
            
            client = flask_app.get_docker_client()
            assert client is None
            # Confirm error was logged mentioning Docker daemon not available
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args[0][0]
            assert "Docker daemon not available" in call_args

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


def test_api_residuals(client, test_case_dir):
    """Test the api_residuals endpoint."""
    # Create tutorial dir expected by the endpoint
    tutorial_dir = test_case_dir / "test_tutorial"
    tutorial_dir.mkdir(parents=True, exist_ok=True)

    # Set up a test log file under CASE_ROOT/test_tutorial/log/simpleFoam
    log_file = tutorial_dir / "log" / "simpleFoam"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("""
    Time = 0.1

    smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 1e-6, No Iterations 3
    smoothSolver:  Solving for Uy, Initial residual = 0.2, Final residual = 1e-6, No Iterations 3
    smoothSolver:  Solving for Uz, Initial residual = 0.3, Final residual = 1e-6, No Iterations 3
    """)

    # Mock the CASE_ROOT in the app
    flask_app.CASE_ROOT = str(test_case_dir)

    # Test with mock
    with patch('app.OpenFOAMFieldParser') as mock_parser_cls:
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.get_residuals_from_log.return_value = {
            'time': [0.1],
            'residuals': {
                'Ux': [0.1],
                'Uy': [0.2],
                'Uz': [0.3]
            }
        }
        mock_parser_cls.return_value = mock_parser

        # Make the request
        response = client.get('/api/residuals?tutorial=test_tutorial')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response structure
        assert 'time' in data
        assert 'residuals' in data
        assert 'Ux' in data['residuals']
        assert 'Uy' in data['residuals']
        assert 'Uz' in data['residuals']

        # Verify the mock was called with correct path
        expected_case_dir = str(test_case_dir / "test_tutorial")
        mock_parser_cls.assert_called_once_with(expected_case_dir)
        mock_parser.get_residuals_from_log.assert_called_once()

         # Test 2: No tutorial specified
        response = client.get('/api/residuals')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == "No tutorial specified"

        # Test 3: Case directory not found
        response = client.get('/api/residuals?tutorial=non_existent_tutorial')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == "Case directory not found"

        # Test 4: Parser raises an exception
        with patch('app.OpenFOAMFieldParser') as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.get_residuals_from_log.side_effect = Exception("Test error")
            mock_parser_cls.return_value = mock_parser

            # Create the tutorial directory for this test
            tutorial_dir.mkdir(parents=True, exist_ok=True)

            response = client.get('/api/residuals?tutorial=test_tutorial')
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert data['error'] == "Test error"

def test_api_latest_data(client, test_case_dir):
    """Test the api_latest_data endpoint with various scenarios."""
    # Setup common test data
    tutorial_dir = test_case_dir / "test_tutorial"
    tutorial_dir.mkdir(parents=True, exist_ok=True)  # Create the folder expected by the API
    flask_app.CASE_ROOT = str(test_case_dir)

    # Test 1: Test successful response
    with patch('app.OpenFOAMFieldParser') as mock_parser_cls:
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.get_latest_time_data.return_value = {
            'time': 1.0,
            'fields': ['U', 'p'],
            'boundaryField': {'inlet': {'type': 'patch'}}
        }
        mock_parser_cls.return_value = mock_parser

        # Make the request
        response = client.get('/api/latest_data?tutorial=test_tutorial')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response structure
        assert 'time' in data
        assert 'fields' in data
        assert 'boundaryField' in data
        assert 'inlet' in data['boundaryField']

        # Verify the mock was called with correct path
        expected_case_dir = str(test_case_dir / "test_tutorial")
        mock_parser_cls.assert_called_once_with(expected_case_dir)
        mock_parser.get_latest_time_data.assert_called_once()

    # Test 2: No tutorial specified
    response = client.get('/api/latest_data')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == "No tutorial specified"

    # Test 3: Case directory not found
    response = client.get('/api/latest_data?tutorial=non_existent_tutorial')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == "Case directory not found"

    # Test 4: Parser raises an exception
    with patch('app.OpenFOAMFieldParser') as mock_parser_cls:
        mock_parser = MagicMock()
        mock_parser.get_latest_time_data.side_effect = Exception("Test error")
        mock_parser_cls.return_value = mock_parser

        # Create the tutorial directory for this test
        tutorial_dir.mkdir(parents=True, exist_ok=True)

        response = client.get('/api/latest_data?tutorial=test_tutorial')
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == "Test error"

    # Test 5: Empty data returned from parser
    with patch('app.OpenFOAMFieldParser') as mock_parser_cls:
        mock_parser = MagicMock()
        mock_parser.get_latest_time_data.return_value = None
        mock_parser_cls.return_value = mock_parser

        response = client.get('/api/latest_data?tutorial=test_tutorial')
        assert response.status_code == 200
        data = response.get_json()
        assert data == {}  # Should return empty dict when no data   

