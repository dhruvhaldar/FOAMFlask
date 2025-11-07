# Build System Utilities

## Overview

The `build_utils` module provides functionality for managing the build process of the FOAMPilot application, particularly focusing on asset minification and build automation in development and production environments.

## Table of Contents

- [Installation](#installation)
- [API Reference](#api-reference)
  - [init_build_system](#init_build_systemapp)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Build Configuration](#build-configuration)

## Installation

```bash
# Install build dependencies
pip install python-minifier
```

## API Reference

### `init_build_system(app)`

Initializes the build system with the Flask application. This function sets up automatic build processes that run before the first request in development mode and performs necessary checks in production.

#### Parameters
- `app` (Flask): The Flask application instance

#### Behavior

**Development Mode** (`ENV='development'`):
1. Checks for `python-minifier` installation
2. Executes `build.py` to process and minify assets
3. Logs build output and errors

**Production Mode** (`ENV='production'`):
1. Verifies existence of minified JavaScript files
2. Logs warnings if minified files are missing

#### Example Usage

```python
from flask import Flask
from build_utils import init_build_system

app = Flask(__name__)
app.config['ENV'] = 'development'  # or 'production'
init_build_system(app)
```

## Development Workflow

### Building Assets

1. **Automatic Build** (Development):
   - Triggered on first request when `ENV='development'`
   - Runs `python build.py` to process assets
   - Minifies JavaScript and CSS files

2. **Manual Build**:
   ```bash
   python build.py
   ```

### File Structure

```
static/
  ├── js/
  │   ├── foamflask_frontend.js      # Source
  │   └── foamflask_frontend.min.js  # Minified (generated)
  └── css/
      ├── styles.css                 # Source
      └── styles.min.css             # Minified (generated)
```

## Troubleshooting

### Common Issues

**Build Failures**
- **Symptom**: Build process fails with errors
- **Solution**:
  ```bash
  # Check build output
  python build.py
  
  # Ensure all dependencies are installed
  pip install -r requirements.txt
  pip install python-minifier
  ```

**Missing Minified Files**
- **Symptom**: Warnings about missing minified files in production
- **Solution**:
  ```bash
  # Run build manually
  python build.py
  
  # Verify files exist
  ls -l static/js/foamflask_frontend.min.js
  ```

## Build Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `'development'` | Application environment ('development' or 'production') |
| `DEBUG` | `True` in development | Enable/disable debug mode |

### Dependencies

- `python-minifier`: For JavaScript and CSS minification
- `Flask`: Web framework

## Best Practices

1. **Development Mode**:
   - Keep `ENV='development'` for automatic rebuilds
   - Monitor application logs for build output

2. **Production Mode**:
   - Run `python build.py` during deployment
   - Verify minified files exist before starting the server
   - Set `ENV='production'` in production

3. **Version Control**:
   - Include both source and minified files in version control
   - Add build artifacts to `.gitignore` if using CI/CD

## License

This documentation is part of the FOAMPilot project. See the main [LICENSE](../LICENSE) file for details.
