
import unittest
from unittest.mock import MagicMock
from backend.meshing.runner import MeshingRunner
from pathlib import Path
import logging

logging.disable(logging.CRITICAL)

class TestMeshingRunnerSecurity(unittest.TestCase):
    def test_run_meshing_command_secure_structure(self):
        """
        Verify that MeshingRunner constructs a safe command list using argv passing,
        preventing shell injection.
        """
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Output"

        # Payload that would cause injection if interpolated into string
        payload = "blockMesh; echo INJECTED"

        case_path = Path("/tmp/case")

        MeshingRunner.run_meshing_command(
            case_path,
            payload,
            mock_client,
            "image:tag",
            "v2012"
        )

        # Verify the command structure passed to Docker
        call_args = mock_client.containers.run.call_args
        docker_cmd = call_args[0][1] # second arg is the command

        # Assert it is a list (not a string)
        self.assertIsInstance(docker_cmd, list, "Docker command should be a list for security")

        # Assert structure: bash -c script name arg1 arg2 arg3
        self.assertEqual(docker_cmd[0], "bash")
        self.assertEqual(docker_cmd[1], "-c")

        # Assert the script uses positional parameters
        script = docker_cmd[2]
        self.assertIn("$1", script)
        self.assertIn("$2", script)
        self.assertIn("$3", script)

        # Assert the payload is passed as an argument, NOT part of the script string
        self.assertIn(payload, docker_cmd)
        self.assertNotIn(payload, script)

        # Check specific argument position (last one)
        self.assertEqual(docker_cmd[-1], payload)

if __name__ == '__main__':
    unittest.main()
