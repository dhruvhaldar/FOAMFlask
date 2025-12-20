## Purpose
Short, actionable guidance for AI coding agents working on FOAMPilot (aka FOAMFlask).
Focus: architecture, dev workflows, repo-specific conventions, integration points, and concrete examples.

## Quick start (developer commands)
- Create & activate a Windows venv (PowerShell):
  - `python -m venv .\environments\my-python313-venv-win`
  - `.\environments\my-python313-venv-win\Scripts\Activate.ps1`
- Install deps: `.\environments\my-python313-venv-win\Scripts\python.exe -m pip install -r requirements.txt`
- Run app: `.\environments\my-python313-venv-win\Scripts\python.exe app.py`
- Build assets (optional): `python build.py` (requires `python_minifier`)

## Big-picture architecture (what to read first)
- `app.py` — single Flask app; central router and orchestration. It is the place to add/remove HTTP routes and glue components.
- `backend/visualization/__init__.py` — PyVista mesh handler (global `mesh_visualizer`).
- `backend/post/isosurface.py` — isosurface generation and HTML exporter (`isosurface_visualizer`).
- `backend/plots/realtime_plots.py` — OpenFOAM field parsing and realtime data endpoints.
- `backend/mesh/mesher.py` — mesh-related helpers and visualizer wiring used by API endpoints.
- `build.py` and `build_utils.py` — local build/minify workflow used in development.
- `case_config.json` — persisted configuration (CASE_ROOT, DOCKER_IMAGE, OPENFOAM_VERSION); prefer using `load_config()`/`save_config()` in code changes.

Why these choices matter
- The server uses Docker (Docker SDK) to run OpenFOAM inside containers and maps host `CASE_ROOT` into the container run directory. Path normalization for Windows is explicitly handled in `app.py` (use `.as_posix()` when mapping volumes).
- Heavy computation/visualization is done server-side via PyVista/VTK; endpoints return either JSON, base64 images, streaming HTML or full interactive HTML blobs.

## Developer workflows & gotchas
- Running cases: `POST /load_tutorial` copies tutorials into the configured case root (via container). `POST /run` streams container logs as HTML lines (each line yielded with `<br>`). Preserve streaming behavior when editing.
- Log capture: `monitor_foamrun_log()` watches for `log.foamRun` and writes `foamrun_logs.txt` and an in-memory `foamrun_logs` dict — tests or edits that change file naming/locations must update this watcher.
- Docker usage: code uses `docker.from_env()` and `containers.run(...)` (see `app.py`). Containers are run detached or streamed; ensure proper cleanup (kill/remove) like the current code does.
- Windows path handling: `app.py` normalizes host paths for Docker (`Path(...).as_posix()`); follow the same pattern in new code that maps volumes.
- Global singletons: modules instantiate global handler objects at module-level (e.g. `mesh_visualizer`, `isosurface_visualizer`). Avoid re-instantiating those unless intentional — many endpoints expect a module-level instance.

## API/endpoint patterns (concrete examples)
- Field listing: `GET /api/available_fields?tutorial=<name>` → uses `get_available_fields(case_dir)` (see `backend/plots/realtime_plots.py`).
- Latest data: `GET /api/latest_data?tutorial=<name>` → constructs `OpenFOAMFieldParser(case_dir)` and calls `get_latest_time_data()`.
- Mesh interactive: `POST /api/mesh_interactive` → returns a full HTML viewer (string) created by PyVista's export functions. The code adds small delays on first calls to avoid race conditions — keep those if you reproduce behavior.
- Run case (streaming): `POST /run` with JSON `{tutorial, command, caseDir}` streams container logs as HTML. Preserve the generator-based streaming behavior when refactoring.

## Project-specific conventions
- Responses: many visualization helper modules return dicts containing `success` and error messages (e.g., `{'success': False, 'error': ...}`). Keep that shape for compatibility with front-end code.
- Logging: use the project logger names (`FOAMFlask` and submodules) and follow existing message formats (prefixes like `[FOAMFlask]`) to keep logs consistent.
- File discovery: mesh discovery searches common OpenFOAM locations (`VTK/`, `postProcessing/`, tutorial root). Use `os.walk` and preserve relative paths in returned JSON (`relative_path`).

## Integration & dependencies
- Docker (python `docker` SDK) — used to run OpenFOAM images (default in `case_config.json`).
- PyVista + VTK — server-side rendering/screenshot and HTML export. Requires proper native VTK support; off-screen rendering may need environment configuration on headless hosts.
- Requirements are pinned in `requirements.txt` (e.g. `pyvista==0.46.4`, `vtk==9.5.2`, `Flask==3.1.2`, `docker==7.1.0`). Respect those versions when adding features unless you run full compatibility tests.

## Edit-time checklist for safe changes
1. If touching Docker logic, run an end-to-end test with an actual container image (the repo expects `haldardhruv/ubuntu_noble_openfoam:v12` by default in `case_config.json`).
2. If changing streaming endpoints, preserve the generator/Response pattern so the frontend still receives incremental log lines.
3. When modifying visualization code (PyVista), remember that endpoints return either base64 PNGs or full HTML — changing return shapes must be coordinated with frontend JS in `static/js/`.
4. Update `docs/` (`app.md`, `PYVISTA_INTEGRATION.md`, `INTERACTIVE_MESH_VIEWER.md`) to reflect API/behavior changes.

## Quick examples to copy in tests or demos
- Set case root (PowerShell):
  - `curl -X POST -H "Content-Type: application/json" -d '{"caseDir":"E:\\Misc\\FOAMPilot\\run_folder"}' http://localhost:5000/set_case`
- List available fields:
  - `curl "http://localhost:5000/api/available_fields?tutorial=incompressible/simpleFoam/airFoil2D"`
- Run a case (streamed):
  - `curl -X POST -H "Content-Type: application/json" -d '{"tutorial":"incompressible/simpleFoam/airFoil2D","command":"Allrun","caseDir":"E:\\Misc\\FOAMPilot\\run_folder"}' http://localhost:5000/run`

## Where to look for more context
- `app.py` — main glue and examples of patterns (Docker, streaming, watchers)
- `backend/plots/realtime_plots.py` — field parsing examples (uniform vs nonuniform handling)
- `backend/visualization/__init__.py` and `backend/post/isosurface.py` — PyVista usage patterns and HTML export
- `docs/` — higher-level design notes and feature docs to mirror when you change behavior

---
If anything here is unclear or you want more examples (small unit tests, suggested improvements to endpoints, or an OpenAPI spec), tell me which area to expand and I will iterate.
