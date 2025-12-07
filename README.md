[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://opensource.org/licenses/GPL-3.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-f5d7e3)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-cyan)](https://flask.palletsprojects.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue)](https://www.typescriptlang.org/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.1.6-white)](https://tailwindcss.com/)
[![OpenFOAM](https://img.shields.io/badge/OpenFOAM-2506-green)](https://openfoam.org/)
[![pydoc3](https://img.shields.io/badge/pydoc3-0.11.6-blue.svg)](https://pdoc3.readthedocs.io/)

# FOAMFlask

**FOAMFlask** is an attempt to make a yet another lightweight web-based GUI for managing and running **OpenFOAM** tutorials and simulations. It allows users to easily select a tutorial, set a case directory, and execute OpenFOAM commands directly from a browser. Since this is targeted for beginners, the documentation has been kept as extensive as possible.

**Note**: Currently only loading and execution of OpenFOAM tutorials (`$FOAM_TUTORIALS`) is supported. Creating custom cases is planned.

**Note**: This program requires Docker to be installed and running, as it uses the OpenFOAM Docker image for its operations. Please ensure Docker is properly set up before proceeding with the installation.

---

## Features

- **Web Interface**: Intuitive web-based interface for OpenFOAM case management
- **Persistent Configuration**: Stores the **CASE_ROOT** across sessions
- **Tutorial Management**: Load and copy tutorials from the OpenFOAM tutorials directory
- **Command Execution**: Run common OpenFOAM commands (`blockMesh`, `simpleFoam`, `pimpleFoam`) with live output
- **Enhanced Output**: Color-coded console output for stdout, stderr, info, and tutorial messages
- **Version Compatibility**: Fully compatible with OpenFOAM 2506 (adjustable for other versions)
- **Security**: Hardened command execution with input validation and injection protection
- **Universal Compatibility**: Works with all OpenFOAM cases (incompressible, compressible, multiphase, etc.)
- **Automatic Field Detection**: Detects and plots available fields (p, U, nut, nuTilda, k, epsilon, omega, T, etc.)
- **Realtime Plotting**: Visualizes OpenFOAM simulation data as it runs with multiple plot types:
  - Pressure vs Time
  - Velocity components (Ux, Uy, Uz) and magnitude
  - Turbulence properties (nut, nuTilda, k, epsilon, omega)
  - Residuals (logarithmic scale)
- **Aerodynamic Analysis** (optional):
  - Pressure coefficient (Cp)
  - 3D velocity profiles
- **IsoSurface Extraction** (optional): Extract isosurfaces from OpenFOAM fields

## Installation

### Prerequisites
- [Docker](https://www.docker.com/) (required for OpenFOAM)
- [Node.js](https://nodejs.org/) (v14+ recommended)
- Python 3.8+
- Git

### Quick Start
1. **Clone the repository** and navigate to the project directory
2. **Set up the frontend** (see Frontend Setup below)
3. **Set up the backend** (see Backend Setup below)
4. **Run the application** (see Running the Application below)

### Frontend Setup

1. **Clone the repository**:
   ```bash
   # Linux/macOS
   git clone https://github.com/dhruvhaldar/FOAMFlask
   cd FOAMFlask
   
   # Windows (PowerShell)
   # git clone https://github.com/dhruvhaldar/FOAMFlask
   # cd FOAMFlask
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

3. **Build the frontend**:
   ```bash
   npm run build
   ```
   
   For development with auto-reload:
   ```bash
   npm run build:watch
   ```

### Backend Setup

#### Linux/macOS
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install pdoc for API documentation (optional)
pip install pdoc
```

#### Windows (PowerShell)
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt

# Install pdoc for API documentation (optional)
pip install pdoc
```

### Running the Application

#### Linux/macOS
```bash
# Ensure Docker is running
sudo systemctl start docker  # For Linux with systemd

# Start the application
python app.py 2>&1 | tee app.log
```

#### Windows (PowerShell)
```powershell
# Ensure Docker Desktop is running
# Start the application
python app.py 2>&1 | Tee-Object -FilePath app.log
```

### API Documentation

To generate API documentation:

```bash
# Linux/macOS
pdoc app.py build_utils.py --output-dir docs

# Windows (PowerShell)
python -m pdoc app.py build_utils.py --output-dir docs
```

Documentation will be available in the `docs` directory as HTML files.

## Usage
1. **Access the web interface**:
   Open your browser and navigate to `http://localhost:5000`

2. **Development mode** (optional):
   - For frontend development with auto-reload:
     ```bash
     npm run build:watch
     ```
   - In another terminal, run the Flask development server:
     ```bash
     export FLASK_DEBUG=1  # Linux/macOS
     # or
     $env:FLASK_DEBUG=1  # Windows PowerShell
     
     python app.py
     ```

3. **Set a case directory**:
Enter a path for your simulation cases.
Click `Set Case Dir`.

4. **Set OpenFOAM root directory**:
Enter a path for your OpenFOAM root directory.
Click `Set OpenFOAM Root`.

5. **Load a tutorial**:
Select a tutorial from the dropdown.
Click `Load Tutorial`.
The tutorial will be copied to your selected case directory.

6. **Run OpenFOAM commands**:
Use the buttons (blockMesh, simpleFoam, pimpleFoam) to execute commands.
Live output is shown in the console panel.

---

## Project Structure
```text
FOAMFlask/
├── app.py # Main Flask application
├── case_config.json # Stores the last used CASE_ROOT
├── package.json # Node.js dependencies and build scripts
├── tsconfig.json # TypeScript configuration
├── copy-built-js.mjs # Custom build script
├── requirements.txt # Python dependencies
├── static/
│ ├── html/
│ │ └── foamflask_frontend.html # HTML template
│ ├── ts/
│ │ └── foamflask_frontend.ts # TypeScript source code
│ ├── js/
│ │ └── foamflask_frontend.js # Compiled JavaScript (for browser)
│ ├── js-build/
│ │ └── foamflask_frontend.js # TypeScript compiler output
│ └── js/
│   └── frontend/
│       └── isosurface.js # PyVista integration
├── backend/
│   ├── mesh/
│   │   └── mesher.py # Mesh generation utilities
│   ├── plots/
│   │   └── realtime_plots.py # Real-time plotting backend
│   └── post/
│       └── isosurface.py # Post-processing utilities
├── test/
│   ├── check_coverage.py # Code coverage analysis script
│   ├── check_docstrings.py # Docstring coverage checker
│   ├── docker_test.py # Docker functionality tests
│   ├── pyvista_test.py # PyVista integration tests
│   ├── foamlib_test.py # FOAM library tests
│   └── bike.vtp # Test VTK file
├── docs/ # Generated documentation
├── environments/ # Python virtual environments
└── README.md # This file
```
---

## Screenshots
![FOAMFlask Lander](docs/images/foamflask_lander.png)

---

## FAQ

### Docker Desktop Warning
This program is dependent on Docker since it uses OpenFOAM docker image.

**Issue Description**: Warning on the backend console:`WARNING:FOAMFlask:[FOAMFlask] get_tutorials called but Docker Desktop is not running`. Frontend shows empty drop down for `Load Tutorial`. (For Linux/MacOS, the message is `Docker daemon not available. Make sure Docker Desktop is running. Details: Error while fetching server API version`)

**Explanation**: This means the application is trying to access Docker Desktop but it's either not running or not installed. 

**Resolution**: Here's how to resolve this:

For Windows:
1. Install Docker Desktop (if not already installed):
   - Download from [Docker's official website](https://www.docker.com/products/docker-desktop/)
   - Follow the installation instructions for your operating system
   - This build was tested on 4.45.0 (203075)

2. Start Docker Desktop
   - Launch Docker Desktop before running the FOAMFlask application
   - Wait for Docker to fully start (you'll see the Docker icon `Docker Desktop running` in your system tray/menu bar)

3. Restart FOAMFlask after Docker is running

4. In Docker Desktop settings, you have the option `Start Docker Desktop when you sign in to your computer` to ensure Docker Desktop runs automatically the next time you login.

For Linux/MacOS:
1. Install Docker Desktop on Linux (if not already installed):
   - Download from [Docker's official website](https://docs.docker.com/desktop/setup/install/linux/)
   - Follow the installation instructions for your operating system
   - This build was tested on Linux Mint 22.2
   - Docker engine is a part of Docker Desktop

2. Start/Enable Docker engine and check status to ensure it's working properly.

---

### Generate API Documentation

Github-flavored Markdown is already generated under `docs` directory as `app.md` and `build_utils.md`.

To generate Python-related API documentation, run the following command:

```powershell
.\environments\my-python313-venv-win\Scripts\python.exe -m pdoc app.py --output-dir docs
.\environments\my-python313-venv-win\Scripts\python.exe -m pdoc build_utils.py --output-dir docs
```

This generates HTML documentation in the `docs` directory as `app.html` and `build_utils.html`.

**Note**: Make sure to install pdoc first if not already installed:
```powershell
.\environments\my-python313-venv-win\Scripts\python.exe -m pip install pdoc
```

### Generate Frontend Documentation

To generate TypeScript API documentation for the frontend, run the following command:

```bash
npm run docs
```

This generates comprehensive documentation for all TypeScript files in `docs/frontend/` directory, including:
- **foamflask_frontend.ts** - Main frontend logic
- **frontend/isosurface.ts** - PyVista integration functions

The documentation includes function signatures, type definitions, and interactive HTML documentation.

### Testing

FOAMFlask includes a comprehensive test suite using pytest. The test suite includes unit tests, integration tests, and end-to-end tests for the application's core functionality.

#### Running Tests

1. **Install test dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

2. **Run all tests** with coverage:
   ```bash
   # Run all tests with coverage
   pytest --cov=app --cov=backend --cov-report=term-missing --cov-report=html
   ```

3. **Run specific test files** or individual tests:
   ```bash
   # Run a specific test file
   pytest test/test_app.py -v
   
   # Run a specific test function
   pytest test/test_app.py::test_index_route -v
   ```

4. **Run tests in parallel** (faster execution):
   ```bash
   pytest -n auto --cov=app --cov=backend
   ```

#### Test Coverage

To check test coverage and generate reports:

```bash
# Generate HTML coverage report (recommended)
pytest --cov=app --cov=backend --cov-report=html

# View coverage in terminal
pytest --cov=app --cov=backend --cov-report=term-missing

# Generate XML report (for CI/CD integration)
pytest --cov=app --cov=backend --cov-report=xml
```

**Coverage Reports**:
- HTML report will be generated in the `htmlcov` directory
- Open `htmlcov/index.html` in your browser to view the detailed coverage report
- The terminal report shows which lines are missing coverage

#### Test Structure

```
test/
├── conftest.py        # Test fixtures and configuration
├── test_app.py        # Main application tests
└── test_security.py   # Security-related tests
```

#### Writing New Tests

1. Create a new test file following the naming convention `test_*.py`
2. Use pytest fixtures from `conftest.py` when available
3. Follow the existing test patterns for consistency
4. Include docstrings explaining what each test verifies

#### Test Coverage Commands Reference

```bash
# Run all tests with coverage
pytest --cov=app --cov=backend

# Run tests without coverage
pytest

# Run tests with detailed output
pytest -v

# Run tests and stop after first failure
pytest -x

# Run tests and show output from print statements
pytest -s

# Run tests matching a specific pattern
pytest -k "test_name_pattern"
```

</details>

---

## Development

### Frontend Development Workflow

1. **Make changes to TypeScript files** (`static/ts/*.ts`)
2. **Compile to JavaScript**:
   ```bash
   npm run build        # One-time build
   npm run build:watch  # Auto-compile on changes (recommended for development)
   ```
3. **Refresh browser** to see changes

**Important**: Always edit files in `static/ts/` directory, never directly in `static/js/`. The `static/js/` files are overwritten during the build process.

---

### Usage

1. Load a tutorial case
2. Click "Show Plots" to enable realtime plotting
3. Run your OpenFOAM command (blockMesh, simpleFoam, etc.)
4. Watch the plots update in realtime
5. For aerodynamic cases, click "Show Aero Plots" for additional analysis

---

### Technical Details

The plotting system uses:
- **Plotly.js** for interactive browser-based plots (no external software needed)
- **Custom OpenFOAM parser** in `realtime_plots.py` that reads field files
- **Flask API endpoints** for serving plot data
- **Automatic field parsing** for both uniform and nonuniform fields

---

## License

FOAMFlask is released under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html) License.