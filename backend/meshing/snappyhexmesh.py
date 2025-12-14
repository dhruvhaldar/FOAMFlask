import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List, Union

logger = logging.getLogger("FOAMFlask")

class SnappyHexMeshGenerator:
    """Generates system/snappyHexMeshDict based on configuration."""

    @staticmethod
    def generate_dict(
        case_path: Path,
        config: Dict[str, Any]
    ) -> bool:
        """
        Generates the snappyHexMeshDict file.
        """
        try:
            # Check if case_path exists
            if not case_path.exists():
                return False

            system_dir = case_path / "system"
            if not system_dir.exists():
                logger.error(f"System directory not found: {system_dir}")
                return False

            # Ensure system_dir is inside case_path
            try:
                system_dir.resolve().relative_to(case_path.resolve())
            except ValueError:
                return False

            dict_path = system_dir / "snappyHexMeshDict"

            # Parse Configuration

            global_settings = config.get("global_settings", {})
            objects = config.get("objects", [])
            location_in_mesh = config.get("location_in_mesh", [0, 0, 0])

            # If objects is empty but 'stl_filename' exists (legacy), construct objects
            if not objects and "stl_filename" in config:
                objects = [{
                    "name": config["stl_filename"],
                    "refinement_level_min": int(config.get("refinement_level", 2)),
                    "refinement_level_max": int(config.get("refinement_level", 2)),
                    "layers": 0
                }]
                # Assume basic global settings
                global_settings = {
                    "castellated_mesh": True,
                    "snap": True,
                    "add_layers": False
                }

            # Extract Global Settings with Defaults
            castellated = "true" if global_settings.get("castellated_mesh", True) else "false"
            snap = "true" if global_settings.get("snap", True) else "false"
            add_layers = "true" if global_settings.get("add_layers", False) else "false"

            # Castellated Controls
            max_global_cells = global_settings.get("max_global_cells", 2000000)
            resolve_feature_angle = global_settings.get("resolve_feature_angle", 30)

            # Snap Controls
            n_smooth_patch = global_settings.get("n_smooth_patch", 3)
            snap_tolerance = global_settings.get("tolerance", 2.0)
            n_solve_iter = global_settings.get("n_solve_iter", 30)
            n_relax_iter = global_settings.get("n_relax_iter", 5)
            # Default to implicit feature snap
            implicit_feature_snap = "true"
            explicit_feature_snap = "false"
            multi_region_feature_snap = "false"

            # Add Layers Controls
            expansion_ratio = global_settings.get("expansion_ratio", 1.0)
            final_layer_thickness = global_settings.get("final_thickness", 0.3)
            min_thickness = global_settings.get("min_thickness", 0.1)
            layer_feature_angle = global_settings.get("feature_angle", 60)

            # Mesh Quality Controls
            max_non_ortho = global_settings.get("max_non_ortho", 65)
            max_boundary_skewness = global_settings.get("max_boundary_skewness", 20)
            max_internal_skewness = global_settings.get("max_internal_skewness", 4)
            min_triangle_twist = global_settings.get("min_triangle_twist", -1)
            relaxed_max_non_ortho = global_settings.get("relaxed_max_non_ortho", 75)

            # Construct Geometry Section
            geometry_str = ""
            for obj in objects:
                name = obj["name"]
                # Sanitize name to be safe
                if ".." in name or "/" in name or "\\" in name:
                     continue # Skip unsafe names

                if name.lower().endswith(".stl"):
                    region_name = name
                    geometry_str += f"""
    {name}
    {{
        type triSurfaceMesh;
        name {region_name};
    }}
"""

            # Construct Features Section
            features_str = ""
            for obj in objects:
                name = obj["name"]
                if ".." in name or "/" in name or "\\" in name: continue

                level = obj.get("refinement_level_min", 1)
                features_str += f"""
        {{
            file "{name}";
            level {level};
        }}
"""

            # Construct Refinement Surfaces
            refinement_surfaces_str = ""
            layers_str = ""

            for obj in objects:
                name = obj["name"]
                if ".." in name or "/" in name or "\\" in name: continue

                min_lvl = obj.get("refinement_level_min", 2)
                max_lvl = obj.get("refinement_level_max", 2)
                num_layers = int(obj.get("layers", 0))

                region_name = name

                refinement_surfaces_str += f"""
        {region_name}
        {{
            level ({min_lvl} {max_lvl});
        }}
"""
                if num_layers > 0:
                    layers_str += f"""
        {region_name}
        {{
            nSurfaceLayers {num_layers};
        }}
"""

            # Build the file content
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

castellatedMesh {castellated};
snap            {snap};
addLayers       {add_layers};

geometry
{{
{geometry_str}
}};

castellatedMeshControls
{{
    maxGlobalCells {max_global_cells};
    minRefinementCells 0;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;

    features
    (
{features_str}
    );

    refinementSurfaces
    {{
{refinement_surfaces_str}
    }}

    resolveFeatureAngle {resolve_feature_angle};

    refinementRegions
    {{
    }}

    locationInMesh ({location_in_mesh[0]} {location_in_mesh[1]} {location_in_mesh[2]});

    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch {n_smooth_patch};
    tolerance {snap_tolerance};
    nSolveIter {n_solve_iter};
    nRelaxIter {n_relax_iter};
    nFeatureSnapIter 10;
    implicitFeatureSnap {implicit_feature_snap};
    explicitFeatureSnap {explicit_feature_snap};
    multiRegionFeatureSnap {multi_region_feature_snap};
}}

addLayersControls
{{
    relativeSizes true;
    layers
    {{
{layers_str}
    }}
    expansionRatio {expansion_ratio};
    finalLayerThickness {final_layer_thickness};
    minThickness {min_thickness};
    nGrow 0;
    featureAngle {layer_feature_angle};
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
    maxNonOrtho {max_non_ortho};
    maxBoundarySkewness {max_boundary_skewness};
    maxInternalSkewness {max_internal_skewness};
    maxConcave 80;
    minVol 1e-13;
    minTetQuality 1e-30;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist {min_triangle_twist};

    nSmoothScale 4;
    errorReduction 0.75;

    relaxed
    {{
        maxNonOrtho {relaxed_max_non_ortho};
    }}
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
