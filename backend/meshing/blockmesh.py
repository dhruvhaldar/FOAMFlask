import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple

logger = logging.getLogger("FOAMFlask")

class BlockMeshGenerator:
    """Generates system/blockMeshDict based on configuration."""

    @staticmethod
    def generate_dict(
        case_path: Path,
        min_point: Tuple[float, float, float],
        max_point: Tuple[float, float, float],
        cells: Tuple[int, int, int],
        grading: Tuple[float, float, float] = (1, 1, 1)
    ) -> bool:
        """
        Generates the blockMeshDict file.
        """
        try:
            # Check if case_path is valid/exists
            if not case_path.exists():
                 logger.error(f"Case path not found: {case_path}")
                 return False

            system_dir = case_path / "system"
            if not system_dir.exists():
                logger.error(f"System directory not found: {system_dir}")
                return False

            # Ensure system_dir is inside case_path
            try:
                system_dir.resolve().relative_to(case_path.resolve())
            except ValueError:
                logger.error("Invalid system directory")
                return False

            dict_path = system_dir / "blockMeshDict"

            # Unpack values
            min_x, min_y, min_z = min_point
            max_x, max_y, max_z = max_point
            nx, ny, nz = cells
            gx, gy, gz = grading

            content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2012                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({min_x} {min_y} {min_z})
    ({max_x} {min_y} {min_z})
    ({max_x} {max_y} {min_z})
    ({min_x} {max_y} {min_z})
    ({min_x} {min_y} {max_z})
    ({max_x} {min_y} {max_z})
    ({max_x} {max_y} {max_z})
    ({min_x} {max_y} {max_z})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading ({gx} {gy} {gz})
);

edges
(
);

boundary
(
    allBoundary
    {{
        type patch;
        faces
        (
            (3 7 6 2)
            (0 4 7 3)
            (2 6 5 1)
            (1 5 4 0)
            (0 3 2 1)
            (4 5 6 7)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""
            with open(dict_path, "w") as f:
                f.write(content)

            logger.info(f"Generated blockMeshDict at {dict_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating blockMeshDict: {e}")
            return False
