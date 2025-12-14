
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app import get_tutorials

def test_get_tutorials_is_cached():
    """
    Verify that get_tutorials caches results and does not call docker on subsequent calls
    with same configuration.
    """
    # We need to clear the cache before running the test, as it is global
    import app
    app._TUTORIALS_CACHE = {}

    with patch('app.get_docker_client') as mock_get_client:
        # Setup mock client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Setup mock container run return values
        mock_container_run = mock_client.containers.run
        mock_container_run.side_effect = [
            b"/opt/openfoam/tutorials\n", # 1st call: echo $FOAM_TUTORIALS
            b"/opt/openfoam/tutorials/incompressible/pimpleFoam/ras/pitzDaily\n/opt/openfoam/tutorials/basic/laplacianFoam/flange\n", # 2nd call: find ...
            # Subsequent calls should not happen due to caching
        ]

        # First call
        tutorials1 = get_tutorials()
        assert len(tutorials1) == 2

        # Second call
        tutorials2 = get_tutorials()
        assert len(tutorials2) == 2

        # Verification
        # We expect 2 calls to containers.run (only for the first call)
        assert mock_container_run.call_count == 2
