import pyvista as pv
import numpy as np

"""
Run using .\my-python313-venv-win\Scripts\python.exe -m pyvista_test
"""
# ---------------------------------------------------
# # Pyvista plotter
# # Create a PyVista Plotter
# plotter = pv.Plotter()

# # Load your VTK file
# vtk_file_path = "bike.vtp"  # Replace with your VTK file path
# mesh = pv.read(vtk_file_path)

# # Add the mesh to the plotter
# plotter.add_mesh(mesh, color="lightblue", show_edges=True)

# # Add some axes
# plotter.add_axes()

# # Show the plotter window
# plotter.show()

# ---------------------------------------------------
# Pyvista Isosurface
# Read the mesh
mesh = pv.read("run_folder/fluid/aerofoilNACA0012Steady/VTK/case_100.vtk", progress_bar=True)
print(mesh)
# UnstructuredGrid (0x2a47ca16e00)
#   N Cells:    16200
#   N Points:   32960
#   X Bounds:   -4.970e+01, 1.000e+02
#   Y Bounds:   -1.000e+00, 0.000e+00
#   Z Bounds:   -5.000e+01, 5.000e+01
#   N Arrays:   19

print("Original mesh arrays:", mesh.array_names)
# Original mesh arrays: ['alphat', 'Ma', 'nut', 'rho', 'p', 'T', 'k', 'omega', 'U', 'cellID', 'alphat', 'Ma', 'nut', 'rho', 'p', 'T', 'k', 'omega', 'U']

# Check if we have point data or cell data
print("\nPoint data arrays:", mesh.point_data.keys())
# Point data arrays: ['alphat', 'Ma', 'nut', 'rho', 'p', 'T', 'k', 'omega', 'U']
print("Cell data arrays:", mesh.cell_data.keys())
# Cell data arrays: ['cellID', 'alphat', 'Ma', 'nut', 'rho', 'p', 'T', 'k', 'omega', 'U']

# Compute velocity magnitude on point data
mesh.point_data["U_Magnitude"] = np.linalg.norm(mesh.point_data["U"], axis=1)
print("\nU_Magnitude range:",
      mesh.point_data["U_Magnitude"].min(),
      mesh.point_data["U_Magnitude"].max())
# U_Magnitude range: 0.0 305.8504

# Also print some statistics
print("U_Magnitude mean:", np.mean(mesh.point_data["U_Magnitude"]))
# U_Magnitude mean: 236.53644
print("U_Magnitude percentiles (0, 25, 50, 75, 100):",
      np.percentile(mesh.point_data["U_Magnitude"], [0, 25, 50, 75, 100]))
# U_Magnitude percentiles (0, 25, 50, 75, 100): [  0.         242.70234299 249.9232254  250.1421814  305.85040283]

# Create isosurfaces using the mesh
contours = mesh.contour(rng=[122.34, 168.2177], scalars="U_Magnitude")

print("\nContour info:")
print(contours)
# PolyData (0x2a47ca167a0)
#   N Cells:    4900
#   N Points:   4900
#   N Strips:   0
#   X Bounds:   -3.629e-02, 1.154e+00
#   Y Bounds:   -1.000e+00, 0.000e+00
#   Z Bounds:   -6.025e-02, 6.025e-02
#   N Arrays:   20

# Create plot
pl = pv.Plotter()
pl.add_mesh(mesh, opacity=0.25, scalars="U_Magnitude", show_scalar_bar=True, cmap='viridis')
pl.add_mesh(contours, opacity=0.8, show_scalar_bar=False, color='red')
pl.show()
