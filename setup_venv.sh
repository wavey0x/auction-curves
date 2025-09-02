#!/bin/bash
# ============================================================================
# Virtual Environment Setup Script for Auction System
# ============================================================================
# This script sets up a unified Python virtual environment with all dependencies
# Usage: ./setup_venv.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo -e "${BLUE}🔧 Setting up unified Python virtual environment for Auction System${NC}"
echo "============================================================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 is required but not found${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Found Python ${PYTHON_VERSION}${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}🔌 Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -e "${YELLOW}⬆️  Upgrading pip...${NC}"
pip install -q --upgrade pip

# Install dependencies
echo -e "${YELLOW}📚 Installing Python dependencies...${NC}"
if [ -f "$SCRIPT_DIR/requirements-working.txt" ]; then
    echo "Using requirements-working.txt (conflict-free dependencies)"
    pip install -q -r "$SCRIPT_DIR/requirements-working.txt"
elif [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo "Using requirements.txt (may have conflicts with eth-brownie)"
    pip install -q -r "$SCRIPT_DIR/requirements.txt" || {
        echo -e "${YELLOW}⚠️  Full requirements failed, installing core dependencies manually...${NC}"
        pip install -q web3 psycopg2-binary pyyaml fastapi uvicorn asyncpg sqlalchemy httpx rich
    }
else
    echo "No requirements file found, installing core dependencies..."
    pip install -q web3 psycopg2-binary pyyaml fastapi uvicorn asyncpg sqlalchemy httpx rich
fi

# Test imports
echo -e "${YELLOW}🧪 Testing dependency imports...${NC}"
python3 -c "
import web3
import psycopg2
import yaml
import fastapi
import uvicorn
print('✅ Core dependencies verified')
print(f'Web3 version: {web3.__version__}')
print(f'FastAPI version: {fastapi.__version__}')
"

echo ""
echo -e "${GREEN}🎉 Virtual environment setup completed successfully!${NC}"
echo "============================================================================"
echo -e "${BLUE}To use the virtual environment:${NC}"
echo ""
echo -e "${YELLOW}# Activate manually:${NC}"
echo "source venv/bin/activate"
echo ""
echo -e "${YELLOW}# Run development services:${NC}"
echo "./dev.sh"
echo ""
echo -e "${YELLOW}# Run governance backfill:${NC}"
echo "source venv/bin/activate && python3 scripts/backfill_governance.py"
echo ""
echo -e "${YELLOW}# Deactivate when done:${NC}"
echo "deactivate"
echo ""