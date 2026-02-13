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
  - [Shared Architecture](#shared-architecture)
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
   uv sync
   ```

   Additional dependencies for interactive mode:
   ```bash
   uv add pythreejs==2.4.2 panel==1.5.4
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

### Shared Architecture

Both Geometry and Mesh visualization now share a common backend foundation to ensure consistency and maintainability.

#### Backend (`backend/visualization/base.py`)
A `BaseVisualizer` class provides shared functionality:
- **File Validation**: Secure path handling and extension checking.
- **Safe Loading**: Handles GZIP decompression and secure file reading.
- **Mesh Decimation**: Shared logic for reducing mesh complexity for web display (using `decimate_pro` where available).
- **HTML Export**: Unified PyVista export settings for consistent web rendering.

#### Frontend (`foamflask_frontend.ts`)
A shared `loadInteractiveViewerCommon` function handles the lifecycle of loading interactive viewers:
- **UI State**: Manages loading spinners, buttons, and placeholders.
- **Error Handling**: Unified notification and error reporting.
- **API Communication**: Handles POST requests to visualization endpoints.

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

## API Reference

### Flask Endpoints

#### `POST /api/mesh_interactive`
Generate interactive viewer for mesh files.

**Request Body**:
```json
{
  "file_path": "/path/to/mesh.vtp",
  "show_edges": true,
  "color": "lightblue"
}
```

**Response**: HTML content (text/html)

#### `POST /api/geometry/view`
Generate interactive viewer for geometry (STL) files.

**Request Body**:
```json
{
  "caseName": "myCase",
  "filename": "geometry.stl",
  "optimize": true
}
```

**Response**: HTML content (text/html)

## Contributing

We welcome contributions to improve the Interactive Mesh Viewer:

1. Report bugs and feature requests
2. Submit pull requests
3. Improve documentation
4. Test with different mesh types

Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.
