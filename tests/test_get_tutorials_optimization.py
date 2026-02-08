from unittest.mock import patch, MagicMock
import pytest
import os
import app

def test_get_tutorials_optimization(mocker):
    """
    Verify that get_tutorials uses the optimized find command instead of -exec test.
    """
    # Clear cache
    app._TUTORIALS_CACHE = {}

    # Unset FOAMFLASK_MOCK_DOCKER
    mocker.patch.dict(os.environ, {}, clear=True)
    if "FOAMFLASK_MOCK_DOCKER" in os.environ:
            mocker.patch.dict(os.environ, {"FOAMFLASK_MOCK_DOCKER": ""})

    with patch('app.get_docker_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_container_run = mock_client.containers.run

        # Mock return value to be valid output
        mock_container_run.return_value = b"/opt/openfoam/tutorials\n/opt/openfoam/tutorials/basic/pitzDaily\n"

        app.get_tutorials()

        assert mock_container_run.called
        args, kwargs = mock_container_run.call_args
        cmd = args[1]

        # Assert optimization is present
        assert "find $FOAM_TUTORIALS -mindepth 3 -maxdepth 3" in cmd
        assert "sed 's|/[^/]*$||'" in cmd
        assert "uniq -d" in cmd

        # Assert slow path is removed
        assert "-exec test -d" not in cmd
