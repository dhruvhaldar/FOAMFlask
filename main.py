
import asyncio
import logging
import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

# Import existing logic
import app as flask_app_module
from backend.plots.realtime_plots import OpenFOAMFieldParser, get_available_fields, _TIME_SERIES_CACHE

# Initialize FastAPI
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("FOAMFlask")

# --- Helper Functions ---

def get_current_case_root():
    return flask_app_module.CASE_ROOT

def validate_path(tutorial: str) -> Path:
    case_root = get_current_case_root()
    if not case_root:
        raise HTTPException(status_code=500, detail="Case root not set")

    try:
        # Re-use the validation logic from app.py
        # We assume tutorial name is passed, not full path
        tutorial_name = os.path.basename(tutorial)
        return flask_app_module.validate_safe_path(case_root, tutorial_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- WebSocket Endpoint ---

@app.websocket("/ws/data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    tutorial = websocket.query_params.get("tutorial")
    if not tutorial:
        await websocket.close(code=1008)
        return

    try:
        case_dir = validate_path(tutorial)
    except Exception:
        await websocket.close(code=1008)
        return

    parser = OpenFOAMFieldParser(str(case_dir))

    last_etag = None

    try:
        while True:
            # Check for updates
            # We use the same ETag logic as in app.py but async-friendly structure
            # (Note: parser itself is sync/CPU bound, run in threadpool if needed,
            # but for now we just run it directly as it's fast with Rust)

            # Check if case exists
            if not case_dir.exists():
                await asyncio.sleep(1)
                continue

            try:
                # Optimized check similar to app.py
                # 1. Check log file mtime
                log_file = case_dir / "log.foamRun"
                log_mtime = 0.0
                if log_file.exists():
                    log_mtime = log_file.stat().st_mtime

                # 2. Check latest time dir mtime
                # We need to list dirs to find latest
                # parser.get_time_directories() uses caching
                time_dirs = parser.get_time_directories()
                latest_dir_mtime = 0.0
                if time_dirs:
                    latest_time_path = case_dir / time_dirs[-1]
                    if latest_time_path.exists():
                        latest_dir_mtime = latest_time_path.stat().st_mtime

                current_etag = f"{log_mtime}-{latest_dir_mtime}"

                if current_etag != last_etag:
                    # Fetch data
                    # Running parser in threadpool to avoid blocking event loop
                    # especially if Rust accelerator is NOT active
                    data = await asyncio.to_thread(parser.get_all_time_series_data, 100)

                    # Also fetch residuals
                    residuals = await asyncio.to_thread(parser.get_residuals_from_log)

                    # Send payload
                    await websocket.send_json({
                        "plot_data": data,
                        "residuals": residuals,
                        "timestamp": asyncio.get_event_loop().time()
                    })

                    last_etag = current_etag

            except Exception as e:
                logger.error(f"Error in websocket loop: {e}")
                # Don't crash connection, just retry

            await asyncio.sleep(0.5) # Poll interval

    except WebSocketDisconnect:
        pass

# --- High-Performance API Overrides ---

@app.get("/api/plot_data")
async def api_plot_data_fast(tutorial: str, request: Request):
    """Async wrapper for plot data."""
    # Logic mirrors app.py but uses async execution for file I/O heavy parts if we were fully async
    # Here we just offload to thread to keep server responsive

    # Check ETag from headers
    if_none_match = request.headers.get("if-none-match")

    try:
        case_dir = validate_path(tutorial)
    except Exception as e:
         # Fallback to sync exception handling
         raise e

    if not case_dir.exists():
         raise HTTPException(status_code=404, detail="Case directory not found")

    # We replicate the caching logic to return 304 efficiently
    parser = OpenFOAMFieldParser(str(case_dir))

    # Offload to thread
    def get_data_sync():
        time_dirs = parser.get_time_directories()
        etag = None
        if time_dirs:
             latest_time = time_dirs[-1]
             latest_time_path = case_dir / latest_time
             try:
                 case_mtime = os.stat(str(case_dir)).st_mtime
                 latest_dir_mtime = os.stat(str(latest_time_path)).st_mtime
                 etag = f'"{case_mtime}-{latest_dir_mtime}"'
             except OSError:
                 pass

        if etag and if_none_match == etag:
            return None, etag

        data = parser.get_all_time_series_data(max_points=100)
        return data, etag

    data, etag = await asyncio.to_thread(get_data_sync)

    if data is None and etag:
        return Response(status_code=304, headers={"ETag": etag})

    # Serialize with orjson (FastAPI uses it by default if installed? No, needs generic)
    # We'll use our own response to ensure orjson is used

    # Orjson response
    import orjson
    return Response(
        content=orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NAIVE_UTC),
        media_type="application/json",
        headers={"ETag": etag} if etag else {}
    )

# Mount the Flask app for all other routes
# This must be LAST
app.mount("/", WSGIMiddleware(flask_app_module.app))

if __name__ == "__main__":
    import uvicorn
    # Use environment variables for config
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = 5000
    uvicorn.run(app, host=host, port=port)
