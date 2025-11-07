# Interactive Mesh Viewer Documentation

## Overview
The mesh viewer now supports both **static** and **interactive** modes for visualizing OpenFOAM mesh files.

## Features

### Static Mode (Default)
- **Fast rendering** using PyVista's screenshot functionality
- **Customizable views**: XY, XZ, YZ planes, or Isometric
- **Adjustable settings**: Edge visibility, mesh color, camera position
- **High-quality PNG output** at 1200x800 resolution
- **Best for**: Quick previews and screenshots

### Interactive Mode (NEW)
- **Full 3D interaction** using PyVista's pythreejs backend
- **Mouse controls**:
  - **Left-click + drag**: Rotate the mesh
  - **Right-click + drag**: Pan the view
  - **Scroll wheel**: Zoom in/out
- **Real-time rendering** in the browser
- **Smooth shading** for better visualization
- **Best for**: Detailed inspection and exploration

## How to Use

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

New dependencies added:
- `pythreejs==2.4.2` - WebGL-based 3D rendering
- `panel==1.5.4` - Alternative backend for interactive viewer

### 2. Load a Mesh
1. Navigate to the **Mesh** page
2. Select a tutorial from the Setup page
3. Click **Refresh List** to find available mesh files
4. Select a mesh file from the dropdown
5. Click **Load Mesh**

### 3. Switch Between Modes

#### Static Mode Controls
- **Show Edges**: Toggle mesh edge visibility
- **Color**: Choose mesh color (Light Blue, White, Gray, Red, Green, Blue)
- **View**: Select camera angle (Auto, XY, XZ, YZ, Isometric)
- **Update View**: Apply changes and re-render

#### Interactive Mode
- Click the **Interactive Mode** button
- Wait for the interactive viewer to load
- Use mouse to interact with the 3D mesh:
  - **Rotate**: Left-click and drag
  - **Pan**: Right-click and drag
  - **Zoom**: Scroll wheel
- Click **Static Mode** to return to static view

## Technical Implementation

### Backend (`pyvista_handler.py`)

#### New Method: `get_interactive_viewer_html()`
```python
def get_interactive_viewer_html(self, file_path, show_edges=True, color="lightblue"):
    """
    Generate a fully interactive HTML viewer with better controls.
    Uses PyVista's export_html with enhanced settings.
    """
```

**Features:**
- Uses PyVista's `export_html()` with `pythreejs` backend
- Fallback to `panel` backend if pythreejs fails
- Enhanced HTML with custom styling
- Full-screen viewer with responsive design
- Smooth shading enabled for better visuals

### Flask Route (`app.py`)

#### New Endpoint: `/api/mesh_interactive` (POST)
```python
@app.route("/api/mesh_interactive", methods=["POST"])
def api_mesh_interactive():
    """
    Generate an interactive HTML viewer for the mesh.
    Returns HTML content that can be embedded in an iframe.
    """
```

**Parameters:**
- `file_path` (str): Path to mesh file
- `show_edges` (bool): Edge visibility
- `color` (str): Mesh color

**Returns:** HTML content for interactive viewer

### Frontend

#### HTML Updates (`foamflask_frontend.html`)
- Added **Interactive Mode** button in mesh controls
- Added `<iframe>` element for interactive viewer
- Updated control visibility logic

#### JavaScript Functions (`foamflask_frontend.js`)

##### `toggleInteractiveMode()`
Handles switching between static and interactive modes:
- Creates a form to POST data to `/api/mesh_interactive`
- Loads interactive viewer in iframe
- Updates UI elements (button text, control visibility)
- Shows appropriate notifications

**State Management:**
- `isInteractiveMode` (boolean): Tracks current mode
- Hides camera position controls in interactive mode
- Restores controls when switching back to static mode

## Browser Compatibility

### Supported Browsers
- ✅ Chrome/Edge (Recommended)
- ✅ Firefox
- ✅ Safari
- ⚠️ Internet Explorer (Not supported)

### Requirements
- WebGL support (enabled by default in modern browsers)
- JavaScript enabled
- Minimum screen resolution: 1024x768

## Performance Considerations

### Static Mode
- **Rendering time**: 1-3 seconds (depends on mesh size)
- **Memory usage**: Low (single image)
- **Network**: Minimal (base64-encoded PNG)

### Interactive Mode
- **Initial load**: 3-10 seconds (depends on mesh complexity)
- **Memory usage**: Higher (full 3D scene in browser)
- **Network**: Larger payload (includes WebGL libraries)
- **Recommended for meshes**: < 500K cells

### Tips for Large Meshes
1. Use static mode for quick previews
2. Switch to interactive mode only when needed
3. Close interactive viewer when done (switch back to static)
4. Consider mesh decimation for very large files

## Troubleshooting

### Issue: Interactive viewer not loading
**Solutions:**
- Check browser console for errors
- Ensure pythreejs is installed: `pip install pythreejs`
- Try refreshing the page
- Check if WebGL is enabled in browser

### Issue: Mesh appears black or invisible
**Solutions:**
- Try changing the mesh color
- Toggle edge visibility
- Check if mesh file is valid
- Verify mesh has proper normals

### Issue: Slow performance in interactive mode
**Solutions:**
- Switch to static mode for large meshes
- Close other browser tabs
- Reduce mesh complexity if possible
- Use a more powerful device

### Issue: Controls not responding
**Solutions:**
- Ensure you're in the correct mode
- Refresh the mesh viewer
- Check if iframe loaded successfully
- Look for JavaScript errors in console

## API Reference

### PyVista Handler Methods

#### `get_interactive_viewer_html(file_path, show_edges, color)`
Generates interactive HTML viewer.

**Returns:** HTML string with embedded WebGL viewer

#### `load_mesh(file_path)`
Loads mesh and returns information.

**Returns:** Dictionary with mesh statistics

#### `get_mesh_screenshot(file_path, width, height, show_edges, color, camera_position)`
Generates static screenshot.

**Returns:** Base64-encoded PNG image

### Flask Endpoints

#### `POST /api/mesh_interactive`
Generate interactive viewer.

**Request Body:**
```json
{
  "file_path": "/path/to/mesh.vtp",
  "show_edges": true,
  "color": "lightblue"
}
```

**Response:** HTML content (text/html)

#### `POST /api/mesh_screenshot`
Generate static screenshot.

**Request Body:**
```json
{
  "file_path": "/path/to/mesh.vtp",
  "width": 1200,
  "height": 800,
  "show_edges": true,
  "color": "lightblue",
  "camera_position": "iso"
}
```

**Response:**
```json
{
  "success": true,
  "image": "base64_encoded_png_data"
}
```

## Examples

### Example 1: Loading a Bike Mesh
```javascript
// 1. Select tutorial with bike mesh
// 2. Refresh mesh list
// 3. Select "bike.vtp"
// 4. Click "Load Mesh"
// 5. Click "Interactive Mode"
// 6. Rotate and inspect the bike geometry
```

### Example 2: Comparing Views
```javascript
// Static mode: Quickly cycle through XY, XZ, YZ views
// Interactive mode: Freely rotate to find optimal angle
// Switch back to static mode and set camera to that angle
```

## Future Enhancements

Planned features:
- **Field data visualization**: Display scalar/vector fields on mesh
- **Clipping planes**: Cut through mesh to see internal structure
- **Measurement tools**: Distance and angle measurements
- **Animation**: Time-series visualization
- **Export options**: Save interactive viewer as standalone HTML
- **Comparison mode**: Side-by-side mesh comparison
- **Mesh quality metrics**: Display mesh quality indicators

## Credits

Built with:
- **PyVista**: 3D visualization library
- **VTK**: Visualization Toolkit
- **pythreejs**: Three.js integration for Jupyter
- **Panel**: High-level app and dashboarding solution
- **Flask**: Web framework
