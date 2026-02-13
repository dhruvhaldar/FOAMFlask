# PyVista Integration Guide

## Overview

This document provides comprehensive documentation for the PyVista integration in the FOAMPilot application, which enables powerful 3D mesh visualization capabilities for OpenFOAM simulations.

## Table of Contents

- [Introduction](#introduction)
- [Architecture](#architecture)
- [Installation](#installation)
- [API Reference](#api-reference)
  - [MeshVisualizer Class](#meshvisualizer-class)
  - [Flask Endpoints](#flask-endpoints)
- [Usage Examples](#usage-examples)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)
- [Contributing](#contributing)

## Introduction

PyVista integration brings robust 3D visualization capabilities to FOAMPilot, allowing users to:

- Visualize complex OpenFOAM meshes interactively
- Generate high-quality static images for reports
- Access mesh statistics and properties
- Integrate with the existing FOAMPilot workflow

## Architecture

The PyVista integration consists of several key components:

1. **Backend Processing**
   - `pyvista_handler.py`: Core mesh processing and visualization
   - Flask API endpoints for web interface communication
   - Asynchronous task handling for large meshes

2. **Frontend Interface**
   - Interactive 3D viewer using PyVista's pythreejs backend
   - Responsive controls for mesh manipulation
   - Real-time feedback and error handling

3. **Data Flow**
   ```mermaid
   graph LR
     A[OpenFOAM Case] --> B[PyVista Handler]
     B --> C[3D Mesh Processing]
     C --> D[Web Interface]
     D --> E[User Interaction]
   ```

## Installation

### Prerequisites

- Python 3.8+
- OpenFOAM installation (for mesh generation)
- Modern web browser with WebGL support

### Dependencies

Core dependencies (automatically installed with `pyproject.toml`):

```bash
# Core
pyvista>=0.44.1
numpy>=1.20.0
flask>=2.0.0

# Optional (for additional features)
pythreejs>=2.4.2  # Interactive 3D visualization
panel>=1.5.4       # Interactive widgets
```

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/foampilot.git
   cd foampilot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

## API Reference

### MeshVisualizer Class

The `MeshVisualizer` class handles all mesh-related operations.

#### `__init__(self, case_dir=None)`
Initialize the mesh visualizer with an optional case directory.

**Parameters**:
- `case_dir` (str, optional): Path to the OpenFOAM case directory

#### `load_mesh(self, file_path)`
Load a mesh file and return its properties.

**Parameters**:
- `file_path` (str): Path to the mesh file (VTK/VTP/VTU)

**Returns**:
```python
{
    'points': int,          # Number of points
    'cells': int,           # Number of cells
    'bounds': [float, ...], # Mesh bounding box [xmin, xmax, ymin, ymax, zmin, zmax]
    'volume': float,        # Total mesh volume
    'center': [float, float, float],  # Mesh center coordinates
    'type': str,            # Mesh type (e.g., 'unstructured', 'polydata')
    'arrays': list          # Available data arrays
}
```

#### `get_mesh_screenshot(self, file_path, width=1200, height=800, show_edges=True, color='lightblue', camera_position='iso')`
Generate a static image of the mesh.

**Parameters**:
- `file_path` (str): Path to the mesh file
- `width` (int): Image width in pixels
- `height` (int): Image height in pixels
- `show_edges` (bool): Whether to show mesh edges
- `color` (str): Mesh color (name or hex code)
- `camera_position` (str): View direction ('xy', 'xz', 'yz', 'iso')

**Returns**: Base64-encoded PNG image

#### `get_available_meshes(self, tutorial=None, case_dir=None)`
Scan for available mesh files in the case directory.

**Parameters**:
- `tutorial` (str, optional): Tutorial name
- `case_dir` (str, optional): Custom case directory

**Returns**: List of found mesh file paths

### Flask Endpoints

#### `GET /api/available_meshes`
List available mesh files.

**Query Parameters**:
- `tutorial` (str, optional): Tutorial name
- `caseDir` (str, optional): Custom case directory

**Response**:
```json
{
  "status": "success",
  "meshes": [
    "/path/to/mesh1.vtk",
    "/path/to/mesh2.vtk"
  ]
}
```

#### `POST /api/load_mesh`
Load and return mesh information.

**Request Body**:
```json
{
  "file_path": "/path/to/mesh.vtk"
}
```

**Response**:
```json
{
  "status": "success",
  "mesh_info": {
    "points": 1000,
    "cells": 2000,
    "bounds": [0, 10, 0, 10, 0, 5],
    "volume": 500.0,
    "center": [5.0, 5.0, 2.5],
    "type": "unstructured",
    "arrays": ["pressure", "velocity"]
  }
}
```

## Usage Examples

### Basic Mesh Loading

```python
from pyvista_handler import MeshVisualizer

# Initialize with case directory
visualizer = MeshVisualizer("/path/to/openfoam/case")

# Get available meshes
meshes = visualizer.get_available_meshes()
print(f"Found meshes: {meshes}")

# Load a specific mesh
mesh_info = visualizer.load_mesh("path/to/mesh.vtk")
print(f"Mesh has {mesh_info['points']} points and {mesh_info['cells']} cells")
```

### Generating a Screenshot

```python
# Generate a screenshot
image_data = visualizer.get_mesh_screenshot(
    "path/to/mesh.vtk",
    width=1600,
    height=900,
    show_edges=True,
    color="#3498db",
    camera_position="xy"
)

# Save to file
with open("screenshot.png", "wb") as f:
    f.write(base64.b64decode(image_data))
```

## Performance Considerations

### Memory Management

- **Large Meshes**: For meshes >1M cells, enable progressive loading
- **Caching**: Enable mesh caching for repeated access
- **Garbage Collection**: Manually trigger garbage collection after processing large meshes

### Optimization Tips

1. **Pre-processing**:
   ```python
   # Reduce mesh resolution if possible
   mesh = pv.read("large_mesh.vtk")
   simplified = mesh.decimate(0.9)  # Reduce by 90%
   ```

2. **Parallel Processing**:
   ```python
   from joblib import Parallel, delayed
   
   def process_mesh(mesh_path):
       # Process individual mesh
       pass
   
   # Process multiple meshes in parallel
   results = Parallel(n_jobs=4)(
       delayed(process_mesh)(path) for path in mesh_paths
   )
   ```

## Troubleshooting

### Common Issues

#### Mesh Loading Failures
- **Symptom**: `vtkCommonDataModelPython.vtkUnstructuredGrid` errors
- **Solution**:
  ```python
  # Try reading with specific file type
  mesh = pv.read("mesh.vtk", file_format="vtk")
  ```

#### Rendering Artifacts
- **Symptom**: Missing faces or incorrect rendering
- **Solution**:
  ```python
  # Rebuild face connectivity
  mesh = mesh.extract_surface().triangulate()
  ```

## Advanced Configuration

### Custom Shaders

```python
import pyvista as pv

# Define custom shader
shader = """
//VTK::Color::Impl
  vec3 lx = normalize(lightPosition0 - vertexMC.xyz);
  vec3 n = normalize(normalMC);
  float df = max(0.0, dot(n, lx));
  diffuseColor = vec4(diffuseColor.rgb * df, 1.0);
"""

# Apply to plotter
pl = pv.Plotter()
pl.add_mesh(mesh, color='white')
pl.renderer.shader = shader
```

### Custom Color Maps

```python
import pyvista as pv
import numpy as np

# Create custom color map
values = np.linspace(0, 1, 256)
colors = pv.themes.DocumentTheme().cmap(values)  # Use theme colors
custom_cmap = pv.LookupTable()
custom_cmap.apply_opacity = True
custom_cmap.scalar_range = (0, 1)
custom_cmap.n_values = 256
custom_cmap.table = colors

# Apply to mesh
plotter = pv.Plotter()
plotter.add_mesh(mesh, cmap=custom_cmap, show_edges=True)
```

## Contributing

We welcome contributions to improve the PyVista integration:

1. **Reporting Issues**
   - Check existing issues before creating new ones
   - Include steps to reproduce and system information

2. **Code Contributions**
   - Follow PEP 8 style guide
   - Write unit tests for new features
   - Update documentation

3. **Testing**
   - Run tests: `pytest tests/`
   - Test with different mesh types and sizes

4. **Documentation**
   - Update docstrings
   - Add usage examples
   - Keep README up to date

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PyVista development team
- OpenFOAM community
- VTK developers

#### Features
- Supports VTK, VTP, and VTU file formats
- Provides mesh statistics (points, cells, bounds, volume, etc.)
- Generates high-quality screenshots with customizable:
  - Colors
  - Edge visibility
  - Camera positions (XY, XZ, YZ, Isometric, Auto)
- Base64 image encoding for easy web display

### 2. **app.py** (MODIFIED)
Added three new Flask API endpoints:

#### `/api/available_meshes` (GET)
- Returns list of available mesh files in the current tutorial
- Searches in common OpenFOAM locations (VTK/, postProcessing/, etc.)

#### `/api/load_mesh` (POST)
- Loads a mesh file and returns detailed information
- Parameters: `file_path`

#### `/api/mesh_screenshot` (POST)
- Generates a mesh screenshot with custom settings
- Parameters: `file_path`, `width`, `height`, `show_edges`, `color`, `camera_position`

### 3. **static/foamflask_frontend.html** (MODIFIED)
Enhanced the Mesh page with:

#### UI Components
- **Mesh Selection Dropdown**: Lists available mesh files
- **Refresh Button**: Reloads the mesh file list
- **Load Mesh Button**: Loads and displays the selected mesh
- **Mesh Controls Panel**:
  - Show/Hide edges checkbox
  - Color selector (Light Blue, White, Gray, Red, Green, Blue)
  - Camera position selector (Auto, XY, XZ, YZ, Isometric)
  - Update View button
- **Mesh Info Panel**: Displays mesh statistics
- **Mesh Viewer**: Shows the rendered mesh image

### 4. **static/js/foamflask_frontend.js** (MODIFIED)
Added JavaScript functions for mesh visualization:

#### Functions
- **`refreshMeshList()`**: Fetches and populates available mesh files
- **`loadMeshVisualization()`**: Loads mesh info and generates initial view
- **`updateMeshView()`**: Re-renders mesh with updated settings
- **`displayMeshInfo(meshInfo)`**: Formats and displays mesh statistics

#### State Management
- `currentMeshPath`: Tracks the currently loaded mesh
- `availableMeshes`: Stores list of available meshes

### 5. **requirements.txt** (MODIFIED)
Added `pyvista==0.46.4` dependency to `pyproject.toml`

## Usage Instructions

### 1. Install Dependencies
```bash
uv sync
```

### 2. Start the Flask Application
```bash
python app.py
```

### 3. Using the Mesh Viewer

1. **Setup Phase**:
   - Navigate to the "Setup" page
   - Set your case directory
   - Load a tutorial case

2. **Mesh Visualization**:
   - Navigate to the "Mesh" page
   - Click "Refresh List" to scan for mesh files
   - Select a mesh file from the dropdown
   - Click "Load Mesh" to visualize

3. **Customize View**:
   - Toggle edge visibility
   - Change mesh color
   - Select different camera angles
   - Click "Update View" to apply changes

## Technical Details

### Mesh File Discovery
The system searches for mesh files in:
- Tutorial root directory
- `VTK/` subdirectory
- `postProcessing/` subdirectory

### Supported File Formats
- `.vtk` - Legacy VTK format
- `.vtp` - VTK PolyData format
- `.vtu` - VTK Unstructured Grid format

### Image Rendering
- Screenshots are rendered server-side using PyVista's off-screen rendering
- Images are converted to PNG and base64-encoded
- Default resolution: 1200x800 pixels
- Transparent backgrounds are disabled for better visibility

### Performance Considerations
- Mesh loading is asynchronous to prevent UI blocking
- Screenshots are generated on-demand
- Large meshes may take longer to render

## Example Workflow

```javascript
// 1. User selects tutorial
// 2. System scans for mesh files
GET /api/available_meshes?tutorial=incompressible/simpleFoam/pitzDaily

// 3. User selects and loads mesh
POST /api/load_mesh
{
  "file_path": "/path/to/case/bike.vtp"
}

// 4. System generates screenshot
POST /api/mesh_screenshot
{
  "file_path": "/path/to/case/bike.vtp",
  "width": 1200,
  "height": 800,
  "show_edges": true,
  "color": "lightblue",
  "camera_position": "iso"
}
```

## Future Enhancements

Potential improvements:
- Interactive 3D viewer using PyVista's HTML export
- Mesh quality analysis
- Field data visualization on mesh
- Animation support for time-series data
- Mesh comparison tools
- Export capabilities (STL, OBJ, etc.)

## Troubleshooting

### Common Issues

1. **"No mesh files found"**
   - Ensure the tutorial has been run and mesh files exist
   - Check VTK/ or postProcessing/ directories

2. **"Failed to render mesh"**
   - Verify PyVista is installed correctly
   - Check file permissions
   - Ensure sufficient memory for large meshes

3. **Slow rendering**
   - Large meshes (>1M cells) may take time
   - Consider reducing screenshot resolution
   - Use edge visibility toggle to improve performance

## Dependencies

- **pyvista**: 3D mesh visualization
- **vtk**: VTK library (installed with PyVista)
- **pillow**: Image processing
- **numpy**: Numerical operations
- **flask**: Web framework

## Integration with Existing Code

The PyVista integration is designed to work seamlessly with:
- Existing tutorial loading system
- Case directory management
- Notification system
- Page navigation
- Responsive UI design
