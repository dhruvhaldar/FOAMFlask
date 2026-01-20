
import unittest
from unittest.mock import MagicMock
from backend.meshing.runner import MeshingRunner
from pathlib import Path
import logging

logging.disable(logging.CRITICAL)

class TestMeshingRunnerSecurity(unittest.TestCase):
    def test_run_meshing_command_secure_structure(self):
        """
        Verify that MeshingRunner REJECTS unsafe commands instead of passing them.
        """
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Output"

        # Payload that would cause injection if interpolated into string
        payload = "blockMesh; echo INJECTED"

        case_path = Path("/tmp/case")

        result = MeshingRunner.run_meshing_command(
            case_path,
            payload,
            mock_client,
            "image:tag",
            "v2012"
        )

        # Verify that docker run was NOT called
        mock_client.containers.run.assert_not_called()

        # Verify result indicates failure due to security
        self.assertFalse(result["success"])
        self.assertIn("security risk", result["message"])

if __name__ == '__main__':
    unittest.main()
