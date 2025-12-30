"""Trame visualization module for 3D mesh visualization."""
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vtk as vtk_widgets, vuetify3 as v3
from trame.decorators import change
import vtk

class MeshViewer:
    def __init__(self, server=None):
        """
        Initialize the Trame application with a 3D viewer.

        Args:
            server: Trame server instance (will create one if None)
        """
        self.server = get_server(server, client_type="vue3")
        self.state = self.server.state
        self.ctrl = self.server.controller

        # Initialize state variables
        self.state.resolution = 6

        # Build the UI
        self._build_ui()

    def reset_resolution(self):
        """Reset the resolution to default"""
        self.state.resolution = 6

    @change("resolution")
    def _on_resolution_change(self, resolution, **kwargs):
        """Handle resolution change"""
        print(f"Resolution changed to {resolution}")

    def _build_ui(self):
        """Build the user interface"""
        # Create a simple layout without toolbar
        with SinglePageLayout(self.server) as self.ui:
            # Hide toolbar and title
            self.ui.toolbar.hide()
            self.ui.title.set_text("")

            # Create render window and renderer first
            render_window = vtk.vtkRenderWindow()
            renderer = vtk.vtkRenderer()
            render_window.AddRenderer(renderer)

            # Create a simple sphere as a placeholder
            sphere = vtk.vtkSphereSource()
            sphere.SetRadius(1.0)
            sphere.SetPhiResolution(20)
            sphere.SetThetaResolution(20)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(sphere.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)

            renderer.AddActor(actor)
            renderer.ResetCamera()

            # Initialize VtkLocalView with the render window
            with v3.VContainer(fluid=True, classes="pa-0 ma-0 fill-height", style="height: 100vh; width: 100%;"):
                with vtk_widgets.VtkLocalView(render_window) as view:
                    self.ctrl.view_update = view.update
                    self.ctrl.view_reset_camera = view.reset_camera

def create_trame_app():
    """
    Create and configure the Trame application with a 3D viewer.

    Returns:
        tuple: (trame_server, layout) - The Trame server and layout objects
    """
    # Create the Trame application
    app = MeshViewer()

    # Return the server and layout for compatibility with app.py
    return app.server, app.ui
