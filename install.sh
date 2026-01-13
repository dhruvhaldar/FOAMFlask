#!/bin/bash
set -e

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== FOAMFlask Installer ===${NC}"

# 1. OS Detection
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo -e "${BLUE}Detected OS: ${MACHINE}${NC}"

# Function to check command existence
check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# 2. Check & Install System Tools (Python, Node, Docker)
echo -e "${BLUE}Checking system requirements...${NC}"

# --- Python ---
if check_cmd python3; then
    echo -e "${GREEN}✓ Python 3 found${NC}"
else
    echo -e "${YELLOW}Python 3 not found. Attempting install...${NC}"
    if [ "$MACHINE" == "Linux" ]; then
        if check_cmd apt-get; then
            sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
        elif check_cmd dnf; then
            sudo dnf install -y python3 python3-pip
        else
            echo -e "${RED}Could not install Python 3. Please install manually.${NC}"
            exit 1
        fi
    elif [ "$MACHINE" == "Mac" ]; then
        if check_cmd brew; then
            brew install python
        else
            echo -e "${RED}Homebrew not found. Please install Python manually.${NC}"
            exit 1
        fi
    fi
fi

# --- Node.js ---
if check_cmd node; then
    echo -e "${GREEN}✓ Node.js found${NC}"
else
    echo -e "${YELLOW}Node.js not found. Attempting install...${NC}"
    if [ "$MACHINE" == "Linux" ]; then
        if check_cmd apt-get; then
             # Using NodeSource is better, but sticking to standard repos for simplicity/safety
             sudo apt-get install -y nodejs npm
        else
             echo -e "${RED}Please install Node.js manually.${NC}"
             exit 1
        fi
    elif [ "$MACHINE" == "Mac" ]; then
        brew install node
    fi
fi

# --- Docker ---
if check_cmd docker; then
    echo -e "${GREEN}✓ Docker found${NC}"
else
    echo -e "${YELLOW}Docker not found.${NC}"
    echo -e "${RED}Please install Docker manually (Docker Desktop recommended).${NC}"
    echo -e "Visit: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# 3. Check & Install pnpm
echo -e "${BLUE}Checking pnpm...${NC}"
if check_cmd pnpm; then
    echo -e "${GREEN}✓ pnpm found${NC}"
else
    echo -e "${YELLOW}pnpm not found. Installing via corepack/npm...${NC}"
    # Try corepack first (bundled with newer Node)
    if corepack enable 2>/dev/null; then
         echo -e "${GREEN}Enabled pnpm via corepack${NC}"
    else
         # Fallback to npm global install
         # Might require sudo on some Linux setups, but we try without first
         npm install -g pnpm || sudo npm install -g pnpm
    fi
fi

# 4. Setup Python Environment
echo -e "${BLUE}Setting up Python environment...${NC}"
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}Created virtual environment in $VENV_DIR${NC}"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Build Frontend
echo -e "${BLUE}Building Frontend...${NC}"
pnpm install
pnpm run build

# 6. Launch Application
echo -e "${BLUE}=== Installation Complete! ===${NC}"
echo -e "${GREEN}Starting FOAMFlask...${NC}"
echo -e "Access the app at: http://localhost:5000"

python app.py
