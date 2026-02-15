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
            sudo apt-get update && sudo apt-get install -y python3 python3-venv
        elif check_cmd dnf; then
            sudo dnf install -y python3
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

# --- uv ---
if check_cmd uv; then
    echo -e "${GREEN}✓ uv found${NC}"
else
    echo -e "${YELLOW}uv not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Update Path for current session
    export PATH="$HOME/.local/bin:$PATH"
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
echo -e "${BLUE}Setting up Python environment with uv...${NC}"
uv venv
echo -e "${GREEN}Created virtual environment with uv${NC}"

echo "Installing Python dependencies with uv..."
uv sync

# Install Rust Accelerator
if [ -d "backend/accelerator" ]; then
    echo -e "${BLUE}Building Rust Accelerator...${NC}"
    if check_cmd cargo; then
        uv add ./backend/accelerator
        echo -e "${GREEN}✓ Rust Accelerator installed${NC}"
    else
        echo -e "${YELLOW}Warning: Cargo not found. Rust accelerator will be skipped (slower performance).${NC}"
    fi
fi

# 5. Build Frontend
echo -e "${BLUE}Building Frontend...${NC}"
pnpm install
pnpm run build

# 6. Launch Application
echo -e "${BLUE}=== Installation Complete! ===${NC}"
echo -e "${GREEN}Starting FOAMFlask...${NC}"
echo -e "Access the app at: http://localhost:5000"

# Use uv run for modern dependency management
uv run app.py
