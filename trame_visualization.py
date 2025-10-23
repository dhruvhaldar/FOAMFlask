"""Trame visualization module for 3D mesh visualization."""
import vtk
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageWithDrawerLayout
from trame.widgets import vtk as vtk_widgets
from trame.decorators import change

def create_trame_app():
    """
    Create and configure the Trame application with a 3D viewer.
    
    Returns:
        tuple: (trame_server, layout) - The Trame server and layout objects
    """
    # Initialize trame server
    trame_server = get_server()
    trame_server.client_type = "vue3"
    trame_server.client_connected = None  # Clear any existing callbacks

    # Create a simple VTK scene
    layout = SinglePageWithDrawerLayout(trame_server, title="Mesh Viewer")
    layout.footer.hide()
    layout.toolbar.hide()

    with layout.content:
        from vtkmodules.vtkFiltersSources import vtkSphereSource

        # Create sample geometry
        sphere = vtkSphereSource()
        sphere.Update()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(sphere.GetOutput())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        renderer = vtk.vtkRenderer()
        renderer.AddActor(actor)
        renderer.ResetCamera()

        render_window = vtk.vtkRenderWindow()
        render_window.AddRenderer(renderer)
        vtk_widgets.VtkLocalView(render_window)
    
    return trame_server, layout
