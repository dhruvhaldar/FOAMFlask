from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional, Union
import uvicorn
import os
import json
import asyncio
import docker
from pathlib import Path
from loguru import logger
from pydantic import BaseModel, Field

# Configuration
CONFIG_FILE = "case_config.json"

class Settings(BaseModel):
    CASE_ROOT: str = str(Path("tutorial_cases").absolute())
    DOCKER_IMAGE: str = "haldardhruv/ubuntu_noble_openfoam:v12"
    OPENFOAM_VERSION: str = "12"
    CURRENT_CASE_DIR: str = ""

class CaseConfig(BaseModel):
    caseDirectory: str = Field(..., description="Path to the case directory")
    openfoamVersion: str = Field(..., description="OpenFOAM version for this case")

class UpdateCaseConfig(BaseModel):
    caseDirectory: Optional[str] = Field(None, description="Path to the case directory")
    openfoamVersion: Optional[str] = Field(None, description="OpenFOAM version for this case")

# Initialize FastAPI app
app = FastAPI(title="FOAMPilot API",
             description="Async OpenFOAM Web Interface",
             version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
settings = Settings()
docker_client = docker.from_env()
active_containers: Dict[str, dict] = {}

# Load configuration
def load_config():
    """Load configuration from case_config.json with sensible defaults."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # Handle missing fields in the config file
                return Settings(**{
                    "CASE_ROOT": data.get("CASE_ROOT", "tutorial_cases"),
                    "DOCKER_IMAGE": data.get("DOCKER_IMAGE", "haldardhruv/ubuntu_noble_openfoam:v12"),
                    "OPENFOAM_VERSION": data.get("OPENFOAM_VERSION", "12"),
                    "CURRENT_CASE_DIR": data.get("CURRENT_CASE_DIR", "")
                })
    except Exception as e:
        logger.warning(f"Could not load config file: {e}")
    return Settings()

# API Routes
@app.get("/")
async def root():
    return {"message": "FOAMPilot API is running"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

# Case management endpoints
@app.get("/api/case/config", response_model=CaseConfig)
async def get_case_config():
    """Get the current case configuration"""
    return {
        "caseDirectory": settings.CURRENT_CASE_DIR,
        "openfoamVersion": settings.OPENFOAM_VERSION
    }

@app.post("/api/case/config", response_model=CaseConfig)
async def update_case_config(config: UpdateCaseConfig):
    """Update the case configuration"""
    if config.caseDirectory is not None:
        # Validate the case directory exists
        case_path = Path(config.caseDirectory)
        if not case_path.exists() or not case_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Case directory does not exist: {config.caseDirectory}"
            )
        settings.CURRENT_CASE_DIR = str(case_path.absolute())
    
    if config.openfoamVersion is not None:
        settings.OPENFOAM_VERSION = config.openfoamVersion
    
    # Save the updated settings
    save_settings()
    
    return {
        "caseDirectory": settings.CURRENT_CASE_DIR,
        "openfoamVersion": settings.OPENFOAM_VERSION
    }

@app.post("/api/case/set_directory")
async def set_case_directory(directory: str):
    """Set the current case directory"""
    path = Path(directory)
    if not path.exists() or not path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Directory does not exist: {directory}"
        )
    
    settings.CURRENT_CASE_DIR = str(path.absolute())
    save_settings()
    
    return {"status": "success", "message": f"Case directory set to {settings.CURRENT_CASE_DIR}"}

def save_settings():
    """Save current settings to the config file"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "CASE_ROOT": settings.CASE_ROOT,
                "DOCKER_IMAGE": settings.DOCKER_IMAGE,
                "OPENFOAM_VERSION": settings.OPENFOAM_VERSION,
                "CURRENT_CASE_DIR": settings.CURRENT_CASE_DIR
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save settings"
        )

# WebSocket endpoint for logs
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # This is a simple echo server for now
            # In a real implementation, this would stream logs from containers
            data = await websocket.receive_text()
            await websocket.send_text(f"Log: {data}")
    except WebSocketDisconnect:
        logger.info("Client disconnected from logs")

# Case management endpoints
@app.get("/api/case/root")
async def get_case_root():
    return {"case_root": settings.CASE_ROOT}

@app.post("/api/tutorial/load")
async def load_tutorial(tutorial_name: str):
    # In a real implementation, this would load a tutorial case
    return {"status": "success", "message": f"Tutorial {tutorial_name} loaded"}

# Docker configuration endpoint
@app.get("/api/docker/config")
async def get_docker_config():
    """Return the current Docker configuration."""
    return {
        "dockerImage": settings.DOCKER_IMAGE,
        "openfoamVersion": settings.OPENFOAM_VERSION
    }

# Simulation control endpoints
@app.post("/api/simulation/run")
async def run_simulation():
    # In a real implementation, this would start a simulation
    return {"status": "started", "simulation_id": "sim_123"}

@app.get("/api/simulation/status/{simulation_id}")
async def get_simulation_status(simulation_id: str):
    # In a real implementation, this would check the status of a simulation
    return {"status": "running", "progress": 50}

if __name__ == "__main__":
    # Load settings
    settings = load_config()
    
    # Create case directory if it doesn't exist
    os.makedirs(settings.CASE_ROOT, exist_ok=True)
    
    # Start the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
