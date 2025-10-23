# PyVista Integration Documentation

## Overview
This document describes the PyVista mesh visualization integration into the FOAMFlask application.

## Files Created/Modified

### 1. **pyvista_handler.py** (NEW)
A dedicated module for PyVista-related functionality with the following features:

#### MeshVisualizer Class
- **`load_mesh(file_path)`**: Loads VTK/VTP/VTU mesh files and returns mesh information
- **`get_mesh_screenshot(file_path, ...)`**: Generates a PNG screenshot of the mesh with customizable options
- **`get_mesh_html(file_path, ...)`**: Exports interactive HTML viewer (for future use)
- **`get_available_meshes(case_dir, tutorial)`**: Scans case directory for available mesh files

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
Added `pyvista==0.44.1` dependency

## Usage Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
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
