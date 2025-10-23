[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://opensource.org/licenses/GPL-3.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-f5d7e3)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-cyan)](https://flask.palletsprojects.com/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.1.6-white)](https://tailwindcss.com/)
[![OpenFOAM](https://img.shields.io/badge/OpenFOAM-2506-green)](https://openfoam.org/)
[![pydoc3](https://img.shields.io/badge/pydoc3-0.11.6-blue.svg)](https://pdoc3.readthedocs.io/)

# FOAMFlask

**FOAMFlask** is a yet another lightweight web-based GUI for managing and running **OpenFOAM** tutorials and simulations. It allows users to easily select a tutorial, set a case directory, and execute OpenFOAM commands directly from a browser.

---

## Features

- Web interface for OpenFOAM case management.
- Persistently store the **CASE_ROOT** across sessions.
- Load and copy tutorials from the OpenFOAM tutorials directory.
- Run common OpenFOAM commands (`blockMesh`, `simpleFoam`, `pimpleFoam`) with live output.
- Color-coded console output for stdout, stderr, info, and tutorial messages.
- Fully compatible with OpenFOAM 2506 (adjustable for other versions).

---

## Installation

1. **Clone the repository**:

```bash
git clone https://github.com/dhruvhaldar/FOAMFlask
cd FOAMFlask
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Usage
1. **Run the server**:
```bash
python app.py
```
2. **Access the web interface**:
Open your browser and navigate to `http://localhost:5000`.

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
```
FOAMFlask/
├── app.py # Main Flask application
├── case_config.json # Stores the last used CASE_ROOT
├── static/
│ ├── FOAMFlask_frontend.html # HTML template
│ └── js/FOAMFlask_frontend.js # JavaScript logic
├── my-py-env/ # Optional: local Python virtual environment
├── requirements.txt # Python dependencies
└── README.md # This file
```

## License

FOAMFlask is released under the GPLv3 License.

## Realtime Plotting

FOAMFlask includes a powerful realtime plotting system that visualizes OpenFOAM simulation data as it runs.

### Features

- **Universal Compatibility**: Works with all OpenFOAM cases (incompressible, compressible, multiphase, etc.)
- **Automatic Field Detection**: Automatically detects and plots available fields (p, U, nut, nuTilda, k, epsilon, omega, T, etc.)
- **Realtime Updates**: Plots update every 2 seconds during simulation
- **Multiple Plot Types**:
  - Pressure vs Time
  - Velocity components (Ux, Uy, Uz) and magnitude
  - Turbulence properties (nut, nuTilda, k, epsilon, omega)
  - Residuals (logarithmic scale)
- **Aerodynamic Analysis** (optional):
  - Pressure coefficient (Cp)
  - 3D velocity profiles

### Usage

1. Load a tutorial case
2. Click "Show Plots" to enable realtime plotting
3. Run your OpenFOAM command (blockMesh, simpleFoam, etc.)
4. Watch the plots update in realtime
5. For aerodynamic cases, click "Show Aero Plots" for additional analysis

### Technical Details

The plotting system uses:
- **Plotly.js** for interactive browser-based plots (no external software needed)
- **Custom OpenFOAM parser** in `realtime_plots.py` that reads field files
- **Flask API endpoints** for serving plot data
- **Automatic field parsing** for both uniform and nonuniform fields

## For Developers

### Quick Start
```powershell
.\my-python313-venv-win\Scripts\python.exe app.py
```

### Installing Dependencies
```powershell
.\my-python313-venv-win\Scripts\python.exe -m pip install -r requirements.txt
```
