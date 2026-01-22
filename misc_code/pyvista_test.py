"""PyVista test script for FOAMFlask.

This script demonstrates PyVista's capabilities for 3D visualization and isosurface
extraction from VTK files. It's used for testing and development purposes.

Example:
    .\my-python313-venv-win\Scripts\python.exe -m pyvista_test
"""
# Standard library imports
import os
from typing import List, Tuple, Dict, Any, Optional, Union

# Third-party imports
import numpy as np
import pyvista as pv
def main() -> None:
    """Main function to demonstrate PyVista visualization.
    
    This function loads a VTK file, processes the mesh data, creates isosurfaces,
    and displays the results in an interactive 3D plot.
    """
    # Example code for basic PyVista plotter (commented out)
    # plotter = pv.Plotter()
    # vtk_file_path = "bike.vtp"  # Replace with your VTK file path
    # mesh = pv.read(vtk_file_path)
    # plotter.add_mesh(mesh, color="lightblue", show_edges=True)
    # plotter.add_axes()
    # plotter.show()

    # Read the mesh
    mesh_path = "run_folder/aerofoilNACA0012Steady/VTK/aerofoilNACA0012Steady_1100.vtk"
    mesh = pv.read(mesh_path, progress_bar=True)
    print(mesh)
    # Expected output:
    # UnstructuredGrid (0x2a47ca16e00)
    #   N Cells:    16200
    #   N Points:   32960
    #   X Bounds:   -4.970e+01, 1.000e+02
    #   Y Bounds:   -1.000e+00, 0.000e+00
    #   Z Bounds:   -5.000e+01, 5.000e+01
    #   N Arrays:   19

    print("Original mesh arrays:", mesh.array_names)
    # Expected output:
    # Original mesh arrays: ['alphat', 'Ma', 'nut', 'rho', 'p', 'T', 'k', 'omega', 'U', 'cellID', ...]

    # Check if we have point data or cell data
    print("\nPoint data arrays:", list(mesh.point_data.keys()))
    # Expected output:
    # Point data arrays: ['alphat', 'Ma', 'nut', 'rho', 'p', 'T', 'k', 'omega', 'U']
    
    print("Cell data arrays:", list(mesh.cell_data.keys()))
    # Expected output:
    # Cell data arrays: ['cellID', 'alphat', 'Ma', 'nut', 'rho', 'p', 'T', 'k', 'omega', 'U']

    # Compute velocity magnitude on point data
    mesh.point_data["U_Magnitude"] = np.linalg.norm(mesh.point_data["U"], axis=1)
    
    # Print velocity magnitude statistics
    u_mag = mesh.point_data["U_Magnitude"]
    print("\nU_Magnitude range:", u_mag.min(), u_mag.max())
    # Expected output:
    # U_Magnitude range: 0.0 305.8504

    print("U_Magnitude mean:", np.mean(u_mag))
    # Expected output:
    # U_Magnitude mean: 236.53644
    
    percentiles = [0, 25, 50, 75, 100]
    percentile_values = np.percentile(u_mag, percentiles)
    print("U_Magnitude percentiles (0, 25, 50, 75, 100):", percentile_values)
    # Expected output:
    # U_Magnitude percentiles: [0.0, 242.702, 249.923, 250.142, 305.850]

    # Create isosurfaces using the mesh
    contour_range = [122.34, 168.2177]
    contours = mesh.contour(rng=contour_range, scalars="U_Magnitude")

    print("\nContour info:")
    print(contours)
    # Expected output:
    # PolyData (0x2a47ca167a0)
    #   N Cells:    4900
    #   N Points:   4900
    #   N Strips:   0
    #   X Bounds:   -3.629e-02, 1.154e+00
    #   Y Bounds:   -1.000e+00, 0.000e+00
    #   Z Bounds:   -6.025e-02, 6.025e-02
    #   N Arrays:   20

    # Create and configure the plot
    plotter = pv.Plotter()
    
    # Add the main mesh with semi-transparent surface
    plotter.add_mesh(
        mesh,
        opacity=0.25,
        scalars="U_Magnitude",
        show_scalar_bar=True,
        cmap='viridis',
        scalar_bar_args={'title': 'Velocity Magnitude'}
    )
    
    # Add the contour lines
    plotter.add_mesh(
        contours,
        opacity=0.8,
        show_scalar_bar=False,
        color='red',
        line_width=3
    )
    
    # Add isovalue widget for interactive exploration
    plotter.add_mesh_isovalue(
        mesh,
        scalars="U_Magnitude",
        opacity=0.5
    )
    
    # Add axes and title
    plotter.add_axes()
    plotter.add_title("Aerofoil NACA0012 - Velocity Magnitude")
    
    # Display the plot
    plotter.show()


if __name__ == "__main__":
    main()
