import logging
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger("FOAMFlask")

class SnappyHexMeshGenerator:
    """Generates system/snappyHexMeshDict based on configuration."""

    @staticmethod
    def generate_dict(
        case_path: Path,
        stl_filename: str,
        refinement_level: int = 2,
        location_in_mesh: Tuple[float, float, float] = (0, 0, 0)
    ) -> bool:
        """
        Generates the snappyHexMeshDict file.

        Args:
            case_path: Path to the case directory.
            stl_filename: Name of the STL file in constant/triSurface.
            refinement_level: Surface refinement level (min and max set to this).
            location_in_mesh: A point inside the mesh but outside the STL (usually).
                              Wait, snappyHexMesh usually meshes the fluid region.
                              We need a point inside the region we want to keep.
                              For external flow (like a wind tunnel around a car), the point is outside the car.
                              For internal flow, it's inside.

                              We will assume external flow for now or take it as input.
                              Defaults to (0,0,0) but the user should probably provide it or we compute it.

        Returns:
            True if successful, False otherwise.
        """
        try:
            system_dir = case_path / "system"
            if not system_dir.exists():
                logger.error(f"System directory not found: {system_dir}")
                return False

            dict_path = system_dir / "snappyHexMeshDict"

            # Basic simple template
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
    object      snappyHexMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

castellatedMesh true;
snap            true;
addLayers       false;

geometry
{{
    {stl_filename}
    {{
        type triSurfaceMesh;
        name objectSurface;
    }}
}};

castellatedMeshControls
{{
    maxGlobalCells 2000000;
    minRefinementCells 0;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;

    features
    (
        {{
            file "{stl_filename}";
            level {refinement_level};
        }}
    );

    refinementSurfaces
    {{
        objectSurface
        {{
            level ({refinement_level} {refinement_level});
        }}
    }}

    resolveFeatureAngle 30;

    refinementRegions
    {{
    }}

    locationInMesh ({location_in_mesh[0]} {location_in_mesh[1]} {location_in_mesh[2]});

    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}

addLayersControls
{{
    relativeSizes true;
    layers
    {{
    }}
    expansionRatio 1.0;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    #include "meshQualityDict"
}}

mergeTolerance 1e-6;

// ************************************************************************* //
"""
            with open(dict_path, "w") as f:
                f.write(content)

            logger.info(f"Generated snappyHexMeshDict at {dict_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating snappyHexMeshDict: {e}")
            return False
