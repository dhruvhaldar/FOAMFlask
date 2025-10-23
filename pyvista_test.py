import pyvista as pv

# Create a PyVista Plotter
plotter = pv.Plotter()

# Load your VTK file
vtk_file_path = "bike.vtp"  # Replace with your VTK file path
mesh = pv.read(vtk_file_path)

# Add the mesh to the plotter
plotter.add_mesh(mesh, color="lightblue", show_edges=True)

# Add some axes
plotter.add_axes()

# Show the plotter window
plotter.show()
