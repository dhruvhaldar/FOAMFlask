import vtk
import os
import tempfile
import base64
from pathlib import Path

from trame.app import TrameApp, get_server
from trame.ui.vuetify3 import SinglePageWithDrawerLayout
from trame.widgets import vtklocal, trame as tw, vuetify3 as v3
from trame.decorators import change
from trame.assets.remote import HttpFile
from trame.assets.local import to_url

# -----------------------------------------------------------------------------
# Fetch default data / files
# -----------------------------------------------------------------------------
BIKE = HttpFile(
    "bike.vtp",
    "https://github.com/Kitware/trame-app-bike/raw/master/data/bike.vtp",
)
# TUNNEL = HttpFile(
#     "tunnel.vtu",
#     "https://github.com/Kitware/trame-app-bike/raw/master/data/tunnel.vtu",
# )
IMAGE = HttpFile(
    "seeds.jpg",
    "https://github.com/Kitware/trame-app-bike/raw/master/data/seeds.jpg",
)

if not BIKE.local:
    BIKE.fetch()

# if not TUNNEL.local:
#     TUNNEL.fetch()

if not IMAGE.local:
    IMAGE.fetch()

# -----------------------------------------------------------------------------
# Constants setup
# -----------------------------------------------------------------------------
# P1 = [-0.4, 0, 0.05]
# P2 = [-0.4, 0, 1.5]

INITIAL_STATE = {
    # "line_widget": {
    #     "p1": P1,
    #     "p2": P2,
    # },
    "trame__title": "VTK Dataset Viewer",
    "trame__favicon": to_url(IMAGE.path),
    "geometry_file": None,
    # "flow_file": None,
    "bike_opacity": 1,
    "status_message": "Ready",
}


# -----------------------------------------------------------------------------
# VTK Reader Factory
# -----------------------------------------------------------------------------
def create_reader(filename):
    """Create appropriate VTK reader based on file extension"""
    ext = Path(filename).suffix.lower()
    
    readers = {
        '.vtp': vtk.vtkXMLPolyDataReader,
        '.vtu': vtk.vtkXMLUnstructuredGridReader,
        '.vti': vtk.vtkXMLImageDataReader,
        '.vtr': vtk.vtkXMLRectilinearGridReader,
        '.vts': vtk.vtkXMLStructuredGridReader,
        '.vtk': vtk.vtkDataSetReader,
        '.ply': vtk.vtkPLYReader,
        '.stl': vtk.vtkSTLReader,
        '.obj': vtk.vtkOBJReader,
        '.vtm': vtk.vtkXMLMultiBlockDataReader,
    }
    
    reader_class = readers.get(ext)
    if reader_class is None:
        raise ValueError(f"Unsupported file type: {ext}")
    
    reader = reader_class()
    reader.SetFileName(filename)
    return reader


# -----------------------------------------------------------------------------
# File handling utilities
# -----------------------------------------------------------------------------
def save_uploaded_file(file_dict, temp_dir):
    """Save uploaded file data to temporary file and return path"""
    if not file_dict:
        return None
    
    # Extract file info from the dictionary
    name = file_dict.get('name', 'uploaded_file')
    content = file_dict.get('content')
    
    if not content:
        return None
    
    # Create temporary file with original extension
    ext = Path(name).suffix
    temp_file = tempfile.NamedTemporaryFile(
        mode='wb', 
        suffix=ext, 
        dir=temp_dir, 
        delete=False
    )
    
    # Decode base64 content and write
    if isinstance(content, str):
        # Remove data URL prefix if present
        if ',' in content:
            content = content.split(',', 1)[1]
        file_bytes = base64.b64decode(content)
    else:
        file_bytes = content
    
    temp_file.write(file_bytes)
    temp_file.close()
    
    return temp_file.name


# -----------------------------------------------------------------------------
# VTK pipeline
# -----------------------------------------------------------------------------
def create_vtk_pipeline(geometry_file=None):
    # K_RANGE = [0.0, 15.6]
    # resolution = 50

    renderer = vtk.vtkRenderer()
    renderWindow = vtk.vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindow.OffScreenRenderingOn()

    renderWindowInteractor = vtk.vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)
    renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

    # Use custom files or defaults
    geom_file = geometry_file if geometry_file and os.path.exists(geometry_file) else BIKE.path
    # flow_file_path = flow_file if flow_file and os.path.exists(flow_file) else TUNNEL.path

    # Create readers
    bikeReader = create_reader(geom_file)
    # tunnelReader = create_reader(flow_file_path)
    # tunnelReader.Update()

    # lineSeed = vtk.vtkLineSource()
    # lineSeed.SetPoint1(*P1)
    # lineSeed.SetPoint2(*P2)
    # lineSeed.SetResolution(resolution)
    # lineSeed.Update()

    # lineWidget = vtk.vtkLineWidget2()
    # lineWidgetRep = lineWidget.GetRepresentation()
    # lineWidgetRep.SetPoint1WorldPosition(P1)
    # lineWidgetRep.SetPoint2WorldPosition(P2)
    # lineWidget.SetInteractor(renderWindowInteractor)

    # streamTracer = vtk.vtkStreamTracer()
    # streamTracer.SetInputConnection(tunnelReader.GetOutputPort())
    # streamTracer.SetSourceConnection(lineSeed.GetOutputPort())
    # streamTracer.SetIntegrationDirectionToForward()
    # streamTracer.SetIntegratorTypeToRungeKutta45()
    # streamTracer.SetMaximumPropagation(3)
    # streamTracer.SetIntegrationStepUnit(2)
    # streamTracer.SetInitialIntegrationStep(0.2)
    # streamTracer.SetMinimumIntegrationStep(0.01)
    # streamTracer.SetMaximumIntegrationStep(0.5)
    # streamTracer.SetMaximumError(0.000001)
    # streamTracer.SetMaximumNumberOfSteps(2000)
    # streamTracer.SetTerminalSpeed(0.00000000001)

    # tubeFilter = vtk.vtkTubeFilter()
    # tubeFilter.SetInputConnection(streamTracer.GetOutputPort())
    # tubeFilter.SetRadius(0.01)
    # tubeFilter.SetNumberOfSides(6)
    # tubeFilter.CappingOn()
    # tubeFilter.Update()

    bike_mapper = vtk.vtkPolyDataMapper()
    bike_actor = vtk.vtkActor()
    bike_mapper.SetInputConnection(bikeReader.GetOutputPort())
    bike_actor.SetMapper(bike_mapper)
    renderer.AddActor(bike_actor)

    # stream_mapper = vtk.vtkPolyDataMapper()
    # stream_actor = vtk.vtkActor()
    # stream_mapper.SetInputConnection(tubeFilter.GetOutputPort())
    # stream_actor.SetMapper(stream_mapper)
    # renderer.AddActor(stream_actor)

    # lut = vtk.vtkLookupTable()
    # lut.SetHueRange(0.7, 0)
    # lut.SetSaturationRange(1.0, 0)
    # lut.SetValueRange(0.5, 1.0)

    # stream_mapper.SetLookupTable(lut)
    # stream_mapper.SetColorModeToMapScalars()
    # stream_mapper.SetScalarModeToUsePointData()
    # stream_mapper.SetArrayName("k")
    # stream_mapper.SetScalarRange(K_RANGE)

    renderWindow.Render()
    renderer.ResetCamera()
    renderer.SetBackground(0.4, 0.4, 0.4)

    # lineWidget.On()

    return renderWindow, bike_actor, renderer  # , lineSeed, lineWidget, bike_actor, renderer


# -----------------------------------------------------------------------------
# Trame app
# -----------------------------------------------------------------------------
class App(TrameApp):
    def __init__(self, server=None):
        super().__init__(server)

        # Create temp directory for this session
        self.temp_dir = tempfile.mkdtemp(prefix="vtk_viewer_")
        self.geometry_path = None
        # self.flow_path = None

        # VTK setup
        self.rw, self.bike_actor, self.renderer = create_vtk_pipeline()  # self.seed, self.widget, 
        
        # Store pipeline components for updates
        # self.streamTracer = None
        self.bike_mapper = None
        # self.stream_actor = None
        self._extract_pipeline_components()

        # GUI setup
        self._build_ui()

        # Initial state
        self.state.update(INITIAL_STATE)

    def _extract_pipeline_components(self):
        """Extract pipeline components for later updates"""
        # Find the stream tracer and mappers in the pipeline
        self.bike_mapper = self.bike_actor.GetMapper()
        
        # Get stream actor (second actor added to renderer)
        # actors = self.renderer.GetActors()
        # actors.InitTraversal()
        # actors.GetNextActor()  # Skip bike actor
        # self.stream_actor = actors.GetNextActor()
        
        # Trace back from stream actor to find streamTracer
        # stream_mapper = self.stream_actor.GetMapper()
        # tube_filter = stream_mapper.GetInputConnection(0, 0).GetProducer()
        # self.streamTracer = tube_filter.GetInputConnection(0, 0).GetProducer()

    @change("bike_opacity")
    def _on_opacity(self, bike_opacity, **_):
        self.bike_actor.property.opacity = bike_opacity
        self.ctrl.view_update()

    # @change("line_widget")
    # def _on_widget_update(self, line_widget, **_):
    #     if line_widget is None:
    #         return

    #     p1 = line_widget.get("p1")
    #     p2 = line_widget.get("p2")

    #     self.seed.SetPoint1(p1)
    #     self.seed.SetPoint2(p2)

    #     if line_widget.get("widget_update", False):
    #         self.widget.representation.point1_world_position = p1
    #         self.widget.representation.point2_world_position = p2

    #     self.ctrl.view_update()

    def reload_pipeline(self, geometry_file=None):
        """Reload VTK pipeline with new files"""
        try:
            # Clean up old pipeline
            # self.widget.Off()
            self.renderer.RemoveAllViewProps()
            
            # Use custom files or defaults
            geom_file = geometry_file if geometry_file and os.path.exists(geometry_file) else BIKE.path
            # flow_file_path = flow_file if flow_file and os.path.exists(flow_file) else TUNNEL.path

            # Create readers
            bikeReader = create_reader(geom_file)
            # tunnelReader = create_reader(flow_file_path)
            # tunnelReader.Update()

            # Update streamtracer input
            # self.streamTracer.SetInputConnection(tunnelReader.GetOutputPort())
            
            # Update geometry mapper
            self.bike_mapper.SetInputConnection(bikeReader.GetOutputPort())
            
            # Re-add actors
            self.renderer.AddActor(self.bike_actor)
            # self.renderer.AddActor(self.stream_actor)
            
            # Reset widget
            # self.widget.On()
            
            # Render and reset camera
            self.rw.Render()
            self.renderer.ResetCamera()
            self.ctrl.view_update()
            
            geom_name = Path(geom_file).name
            # flow_name = Path(flow_file_path).name
            self.state.status_message = f"Loaded: {geom_name}"  # , {flow_name}
            print(f"Loaded: geometry={geom_name}")  # , flow={flow_name}
        except Exception as e:
            error_msg = f"Error loading files: {e}"
            self.state.status_message = error_msg
            print(error_msg)

    @change("geometry_file")
    def _on_geometry_file_change(self, geometry_file, **_):
        """Handle geometry file upload"""
        if geometry_file is None:
            self.geometry_path = None
            self.reload_pipeline(None)  # , self.flow_path
            return
            
        try:
            self.geometry_path = save_uploaded_file(geometry_file, self.temp_dir)
            if self.geometry_path:
                self.reload_pipeline(self.geometry_path)  # , self.flow_path
        except Exception as e:
            error_msg = f"Error loading geometry file: {e}"
            self.state.status_message = error_msg
            print(error_msg)

    # @change("flow_file")
    # def _on_flow_file_change(self, flow_file, **_):
    #     """Handle flow file upload"""
    #     if flow_file is None:
    #         self.flow_path = None
    #         self.reload_pipeline(self.geometry_path, None)
    #         return
            
    #     try:
    #         self.flow_path = save_uploaded_file(flow_file, self.temp_dir)
    #         if self.flow_path:
    #             self.reload_pipeline(self.geometry_path, self.flow_path)
    #     except Exception as e:
    #         error_msg = f"Error loading flow file: {e}"
    #         self.state.status_message = error_msg
    #         print(error_msg)

    def _build_ui(self):
        with SinglePageWithDrawerLayout(self.server, full_height=True) as layout:
            self.ui = layout  # for jupyter integration

            # Toolbar
            with layout.toolbar as toolbar:
                toolbar.density = "compact"
                layout.title.set_text("VTK Dataset Viewer")
                v3.VSpacer()
                v3.VSlider(
                    v_model=("bike_opacity", 1),
                    min=0,
                    max=1,
                    step=0.05,
                    density="compact",
                    hide_details=True,
                    style="max-width: 200px;",
                )
                v3.VBtn(icon="mdi-crop-free", click=self.ctrl.view_reset_camera)

            # Drawer
            with layout.drawer:
                v3.VCardTitle("File Upload")
                v3.VDivider()
                
                with v3.VContainer(fluid=True):
                    v3.VFileInput(
                        label="Geometry File (.vtp, .vtu, .stl, .obj, etc.)",
                        accept=".vtp,.vtu,.vti,.vtr,.vts,.vtk,.ply,.stl,.obj,.vtm",
                        v_model=("geometry_file",),
                        density="compact",
                        show_size=True,
                    )
                    
                    # v3.VFileInput(
                    #     label="Flow Field File (.vtu, .vti, etc.)",
                    #     accept=".vtp,.vtu,.vti,.vtr,.vts,.vtk,.vtm",
                    #     v_model=("flow_file",),
                    #     density="compact",
                    #     show_size=True,
                    # )
                    
                    v3.VBtn(
                        "Reset to Default",
                        click="geometry_file = null",  # ; flow_file = null
                        block=True,
                        color="primary",
                        variant="outlined",
                        classes="mb-2",
                    )
                    
                    v3.VAlert(
                        text=("status_message",),
                        type="info",
                        density="compact",
                        variant="tonal",
                    )
                
                # v3.VDivider(classes="my-4")
                # v3.VCardTitle("Line Seed")
                
                # tw.LineSeed(
                #     image=to_url(IMAGE.path),
                #     point_1=("line_widget.p1",),
                #     point_2=("line_widget.p2",),
                #     bounds=("[-0.399, 1.80, -1.12, 1.11, -0.43, 1.79]",),
                #     update_seed="line_widget = { ...$event, widget_update: 1 }",
                #     n_sliders=2,
                # )

            # Content
            with layout.content:
                with vtklocal.LocalView(self.rw, throttle_rate=20) as view:
                    self.ctrl.view_update = view.update_throttle
                    self.ctrl.view_reset_camera = view.reset_camera

                    # Bind state to 3D widget interaction event
                    # widget_id = view.register_vtk_object(self.widget)
                    # view.listeners = (
                    #     "wasm_listeners",
                    #     {
                    #         widget_id: {
                    #             "InteractionEvent": {
                    #                 "line_widget": {
                    #                     "p1": (
                    #                         widget_id,
                    #                         "WidgetRepresentation",
                    #                         "Point1WorldPosition",
                    #                     ),
                    #                     "p2": (
                    #                         widget_id,
                    #                         "WidgetRepresentation",
                    #                         "Point2WorldPosition",
                    #                     ),
                    #                 }
                    #             },
                    #         },
                    #     },
                    # )


# -----------------------------------------------------------------------------
# Server factory for multi-user support
# -----------------------------------------------------------------------------
def create_app(server=None):
    """Factory function for launcher"""
    return App(server)


def main():
    # For single-user mode
    app = App()
    app.server.start(port=5001, debug=True, verbose=True, open_browser=False)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Multi-user launcher configuration
# -----------------------------------------------------------------------------
"""
To run with multi-user support, create a launcher.yaml file:

```yaml
version: 1
timeout: -1
resources:
  - port: 9000
    host: localhost
application:
  apps:
    vtk_viewer:
      cmd:
        - python
        - vtk_viewer.py
        - --port
        - "{port}"
        - --authKey
        - "{secret}"
      ready_line: "App running"
```

Then run with:
```bash
trame-launcher launcher.yaml
```

Or configure programmatically:
```python
from trame_launcher import Launcher

launcher = Launcher({
    "application": {
        "apps": {
            "vtk_viewer": {
                "cmd": ["python", "vtk_viewer.py", "--port", "{port}"],
            }
        }
    }
})
launcher.start()
```
"""