# Interactive Mesh Viewer

## Overview

The Interactive Mesh Viewer is a powerful tool for visualizing OpenFOAM mesh files with both static and interactive rendering capabilities. It's designed to work seamlessly within the FOAMPilot web interface, providing fluid 3D visualization of complex meshes directly in the browser.

## Table of Contents

- [Features](#features)
  - [Static Mode](#static-mode)
  - [Interactive Mode](#interactive-mode)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [User Guide](#user-guide)
  - [Loading a Mesh](#loading-a-mesh)
  - [Viewing Modes](#viewing-modes)
  - [Navigation Controls](#navigation-controls)
- [Technical Details](#technical-details)
  - [Architecture](#architecture)
  - [Performance](#performance)
  - [Browser Support](#browser-support)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## Features

### Static Mode

Ideal for quick previews and documentation, Static Mode offers:

- **High-Performance Rendering**
  - Instant loading of pre-rendered images
  - Consistent output for documentation
  - Fixed resolution (1200×800) for predictable results

- **Visual Customization**
  - **Color Schemes**: Choose from multiple preset colors
  - **Edge Display**: Toggle mesh edges on/off
  - **View Presets**: Standard orthographic (XY, XZ, YZ) and isometric views
  - **Camera Control**: Adjust position and orientation

- **Export Capabilities**
  - Save high-quality PNG images
  - Copy to clipboard functionality
  - Consistent rendering across sessions

### Interactive Mode

Designed for in-depth analysis, Interactive Mode provides:

- **Full 3D Navigation**
  - **Rotation**: Left-click + drag
  - **Panning**: Right-click + drag
  - **Zoom**: Scroll wheel or pinch gesture
  - **Reset View**: Double-click to reset camera

- **Advanced Visualization**
  - Smooth shading and lighting
  - Real-time updates
  - Adaptive resolution for optimal performance
  - Fullscreen mode for detailed inspection

- **Performance Optimizations**
  - Level-of-detail (LOD) rendering
  - Progressive loading for large meshes
  - WebGL acceleration

## Getting Started

### Prerequisites

Before using the Interactive Mesh Viewer, ensure you have:

- Python 3.8 or higher
- Modern web browser with WebGL 2.0 support
- Sufficient system resources (8GB+ RAM recommended for large meshes)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/foampilot.git
   cd foampilot
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Additional dependencies for interactive mode:
   ```bash
   pip install pythreejs==2.4.2 panel==1.5.4
   ```

## User Guide

### Loading a Mesh

1. **Access the Viewer**
   - Launch the FOAMPilot application
   - Navigate to the Mesh tab in the web interface

2. **Select a Tutorial**
   - Choose from available tutorials in the dropdown
   - Or specify a custom case directory

3. **Load the Mesh**
   - Click "Refresh List" to scan for mesh files
   - Select a mesh file from the dropdown
   - Click "Load Mesh" to begin visualization

### Viewing Modes

#### Switching Between Modes
- Use the "Interactive Mode" toggle to switch between static and interactive views
- Static mode is recommended for quick previews
- Interactive mode enables full 3D manipulation

#### Static Mode Features
- **View Presets**: Select from standard views (XY, XZ, YZ, Isometric)
- **Visual Settings**:
  - Toggle edge visibility
  - Change mesh color
  - Adjust lighting
- **Export Options**:
  - Save as PNG
  - Copy to clipboard
  - Generate shareable links

#### Interactive Mode Features
- **Navigation Controls**:
  - Rotate: Left-click + drag
  - Pan: Right-click + drag
  - Zoom: Scroll wheel or pinch gesture
  - Reset View: Double-click
- **Display Options**:
  - Toggle wireframe mode
  - Adjust point size
  - Change background color
  - Enable/disable axes

### Navigation Controls

| Action | Mouse | Touch |
|--------|-------|-------|
| Rotate | Left-click + drag | One-finger drag |
| Pan | Right-click + drag | Two-finger drag |
| Zoom | Scroll wheel | Pinch gesture |
| Reset View | Double-click | Double-tap |
| Fullscreen | Click fullscreen button | N/A |

## Technical Details

### Architecture

The Interactive Mesh Viewer is built on:

1. **Frontend**:
   - PyVista for 3D visualization
   - pythreejs for WebGL rendering
   - Panel for interactive widgets
   - Custom JavaScript for UI controls

2. **Backend**:
   - Flask web server
   - PyVista for mesh processing
   - Asynchronous task handling

### Performance

- **Recommended Mesh Sizes**:
  - Small: < 100,000 cells (optimal)
  - Medium: 100,000 - 1,000,000 cells (good performance)
  - Large: > 1,000,000 cells (reduced performance)

- **Optimization Tips**:
  - Use static mode for large meshes
  - Disable edges in interactive mode
  - Reduce mesh resolution if possible
  - Close other memory-intensive applications

### Browser Support

| Browser | Version | Notes |
|---------|---------|-------|
| Chrome | 90+ | Recommended |
| Firefox | 85+ | Good support |
| Edge | 90+ | Good support |
| Safari | 14+ | Limited testing |
| Mobile | Varies | Basic support |

## Troubleshooting

### Common Issues

#### Mesh Fails to Load
- **Symptom**: Blank screen or error message
- **Solutions**:
  - Verify file path is correct
  - Check file permissions
  - Ensure mesh file is not corrupted

#### Poor Performance
- **Symptom**: Slow rendering or unresponsive UI
- **Solutions**:
  - Switch to static mode
  - Reduce mesh resolution
  - Close other applications
  - Update graphics drivers

#### WebGL Errors
- **Symptom**: "WebGL not supported" or rendering artifacts
- **Solutions**:
  - Update browser to latest version
  - Enable WebGL in browser settings
  - Check browser console for specific errors

## API Reference

### Endpoints

#### `GET /api/available_meshes`
List available mesh files in the current case.

**Parameters**:
- `tutorial` (string): Name of the tutorial
- `caseDir` (string, optional): Custom case directory

**Response**:
```json
{
  "meshes": ["path/to/mesh1.vtk", "path/to/mesh2.vtk"],
  "status": "success"
}
```

#### `POST /api/load_mesh`
Load a mesh file for visualization.

**Request Body**:
```json
{
  "file_path": "path/to/mesh.vtk",
  "show_edges": true,
  "color": "lightblue"
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
    "volume": 500.0
  }
}
```

## Contributing

We welcome contributions to improve the Interactive Mesh Viewer:

1. Report bugs and feature requests
2. Submit pull requests
3. Improve documentation
4. Test with different mesh types

Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

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
