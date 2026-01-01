
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Mock docker module before importing app
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

# Now import app
from app import app, CASE_ROOT

class TestPathTraversal(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        # Mock get_docker_client to return a mock client
        self.mock_client = MagicMock()
        self.mock_container = MagicMock()
        self.mock_client.containers.run.return_value = self.mock_container
        self.mock_container.logs.return_value = b""

        # Patch the get_docker_client in app
        self.patcher = patch("app.get_docker_client", return_value=self.mock_client)
        self.patcher.start()

        # Set a safe CASE_ROOT for testing
        app.config["TESTING"] = True
        self.original_case_root = CASE_ROOT
        # We need to set the global CASE_ROOT in app module
        import app as app_module
        app_module.CASE_ROOT = "/safe/root"

    def tearDown(self):
        self.patcher.stop()
        import app as app_module
        app_module.CASE_ROOT = self.original_case_root

    def test_run_foamtovtk_traversal(self):
        # malicious path
        malicious_path = "/etc"

        response = self.app.post("/run_foamtovtk", json={
            "tutorial": "cavity",
            "caseDir": malicious_path
        })

        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")

        # Expecting 400 Bad Request
        if response.status_code == 400:
             print("SUCCESS: Path traversal blocked with 400 Bad Request")
        else:
             print(f"FAILURE: Unexpected status code {response.status_code}")

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Access denied", response.data)

        # Ensure docker was NOT called
        self.mock_client.containers.run.assert_not_called()

    def test_run_case_traversal(self):
        # malicious path
        malicious_path = "/etc"

        response = self.app.post("/run", json={
            "tutorial": "cavity",
            "command": "blockMesh",
            "caseDir": malicious_path
        })

        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")

        # Expecting 400 Bad Request
        if response.status_code == 400:
             print("SUCCESS: Path traversal blocked with 400 Bad Request")
        else:
             print(f"FAILURE: Unexpected status code {response.status_code}")

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Access denied", response.data)

        # Ensure docker was NOT called
        self.mock_client.containers.run.assert_not_called()

if __name__ == "__main__":
    unittest.main()
