import pytest
from unittest.mock import MagicMock, patch
from backend.meshing.runner import MeshingRunner
import docker

class TestMeshingRunner:
    def test_configure_blockmesh(self, tmp_path):
        case_path = tmp_path / "case"
        (case_path / "system").mkdir(parents=True)

        config = {
            "min_point": [0, 0, 0],
            "max_point": [1, 1, 1],
            "cells": [10, 10, 10]
        }

        result = MeshingRunner.configure_blockmesh(case_path, config)
        assert result["success"] is True
        assert (case_path / "system" / "blockMeshDict").exists()

    def test_configure_blockmesh_failure(self, mocker):
        mocker.patch('backend.meshing.runner.BlockMeshGenerator.generate_dict', return_value=False)
        result = MeshingRunner.configure_blockmesh(MagicMock(), {})
        assert result["success"] is False

    def test_configure_snappyhexmesh(self, tmp_path):
        case_path = tmp_path / "case"
        (case_path / "system").mkdir(parents=True)

        config = {"stl_filename": "test.stl"}
        result = MeshingRunner.configure_snappyhexmesh(case_path, config)
        assert result["success"] is True
        assert (case_path / "system" / "snappyHexMeshDict").exists()

    def test_configure_snappyhexmesh_failure(self, mocker):
        mocker.patch('backend.meshing.runner.SnappyHexMeshGenerator.generate_dict', return_value=False)
        result = MeshingRunner.configure_snappyhexmesh(MagicMock(), {})
        assert result["success"] is False

    def test_run_meshing_command_success(self, tmp_path):
        case_path = tmp_path / "case"

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.run.return_value = b"Output"

        result = MeshingRunner.run_meshing_command(
            case_path, "blockMesh", mock_client, "image:tag", "v2012"
        )

        assert result["success"] is True
        assert result["output"] == "Output"
        mock_client.containers.run.assert_called_once()

    def test_run_meshing_command_no_client(self, tmp_path):
        result = MeshingRunner.run_meshing_command(
            tmp_path, "cmd", None, "img", "v"
        )
        assert result["success"] is False
        assert "not available" in result["message"]

    def test_run_meshing_command_unsafe(self, tmp_path):
        mock_client = MagicMock()
        result = MeshingRunner.run_meshing_command(
            tmp_path, "cmd; rm -rf /", mock_client, "img", "v"
        )
        assert result["success"] is False
        assert "Invalid command" in result["message"]

    def test_run_meshing_command_container_error(self, tmp_path):
        case_path = tmp_path / "case"
        mock_client = MagicMock()

        error = docker.errors.ContainerError(
            container=None, exit_status=1, command="cmd", image="img", stderr=b"Error output"
        )
        mock_client.containers.run.side_effect = error

        result = MeshingRunner.run_meshing_command(
            case_path, "blockMesh", mock_client, "img", "v"
        )

        assert result["success"] is False
        assert "Error output" in result["output"]

    def test_run_meshing_command_exception(self, tmp_path):
        case_path = tmp_path / "case"
        mock_client = MagicMock()
        mock_client.containers.run.side_effect = Exception("Unknown")

        result = MeshingRunner.run_meshing_command(
            case_path, "blockMesh", mock_client, "img", "v"
        )

        assert result["success"] is False
        assert "Unknown" in result["message"]
