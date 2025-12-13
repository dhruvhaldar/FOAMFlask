import logging
import platform
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import docker
import posixpath

from .blockmesh import BlockMeshGenerator
from .snappyhexmesh import SnappyHexMeshGenerator

logger = logging.getLogger("FOAMFlask")

class MeshingRunner:
    """
    Handles configuration and execution of meshing tools.
    """

    @staticmethod
    def configure_blockmesh(case_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configures blockMeshDict.

        Args:
            case_path: Path to the case directory.
            config: Dictionary containing 'min_point', 'max_point', 'cells', 'grading'.

        Returns:
            Dict with success status and message.
        """
        try:
            min_point = tuple(config.get("min_point", [-1, -1, -1]))
            max_point = tuple(config.get("max_point", [1, 1, 1]))
            cells = tuple(config.get("cells", [10, 10, 10]))
            grading = tuple(config.get("grading", [1, 1, 1]))

            success = BlockMeshGenerator.generate_dict(case_path, min_point, max_point, cells, grading)

            if success:
                return {"success": True, "message": "blockMeshDict generated successfully"}
            else:
                return {"success": False, "message": "Failed to generate blockMeshDict"}
        except Exception as e:
            logger.error(f"Error configuring blockMesh: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def configure_snappyhexmesh(case_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configures snappyHexMeshDict.

        Args:
            case_path: Path to the case directory.
            config: Configuration dictionary (new complex structure or legacy).

        Returns:
            Dict with success status and message.
        """
        try:
            # Pass the full config to the generator
            success = SnappyHexMeshGenerator.generate_dict(case_path, config)

            if success:
                return {"success": True, "message": "snappyHexMeshDict generated successfully"}
            else:
                return {"success": False, "message": "Failed to generate snappyHexMeshDict"}
        except Exception as e:
            logger.error(f"Error configuring snappyHexMesh: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def run_meshing_command(
        case_path: Path,
        command: str,
        docker_client: docker.DockerClient,
        docker_image: str,
        openfoam_version: str,
        user_config: Dict[str, str] = {}
    ) -> Dict[str, Any]:
        """
        Runs a meshing command (blockMesh, snappyHexMesh) in the Docker container.
        """
        try:
            if not docker_client:
                 return {"success": False, "message": "Docker client not available"}

            # Setup paths
            container_run_path = "/tmp/FOAM_Run"

            case_name = case_path.name
            container_case_path = posixpath.join(container_run_path, case_name)

            bashrc = f"/opt/openfoam{openfoam_version}/etc/bashrc"

            # Host path (parent of case_path)
            host_path = case_path.parent.resolve()

            # Windows/POSIX handling
            is_windows = platform.system() == "Windows"
            host_path_str = host_path.as_posix() if is_windows else str(host_path)

            volumes = {
                host_path_str: {
                    "bind": container_run_path,
                    "mode": "rw",
                }
            }

            # Create command
            # Source bashrc, cd to case, run command
            docker_cmd = (
                f"bash -c 'source {bashrc} && "
                f"cd {container_case_path} && "
                f"{command}'"
            )

            logger.info(f"Running meshing command: {command} in {container_case_path}")

            run_kwargs = {
                "detach": False, # Wait for it
                "tty": False,
                "stdout": True,
                "stderr": True,
                "volumes": volumes,
                "remove": True,
            }
            run_kwargs.update(user_config)

            # Run
            result = docker_client.containers.run(
                docker_image,
                docker_cmd,
                **run_kwargs
            )

            output = result.decode("utf-8")
            logger.info(f"Meshing output: {output[:200]}...") # Log first 200 chars

            return {"success": True, "output": output}

        except docker.errors.ContainerError as e:
            # Container exited with non-zero code
            return {"success": False, "message": f"Command failed", "output": e.stderr.decode('utf-8') if e.stderr else str(e)}
        except Exception as e:
            logger.error(f"Error running meshing command: {e}")
            return {"success": False, "message": str(e)}
