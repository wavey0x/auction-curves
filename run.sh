#!/bin/bash

# Auction House Launcher Script
# Starts all services in the correct order

set -e

echo "🏛️ Starting Auction House..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Port $1 is already in use${NC}"
        return 0
    else
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${BLUE}Waiting for $name to start...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $name is ready${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Attempt $attempt/$max_attempts - waiting for $name...${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ $name failed to start after $max_attempts attempts${NC}"
    return 1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check if brownie is installed
if ! command -v brownie &> /dev/null; then
    echo -e "${RED}❌ Brownie not found. Please install: pip install eth-brownie${NC}"
    exit 1
fi

# Check if node/npm is installed  
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found. Please install Node.js${NC}"
    exit 1
fi

# Check if PostgreSQL is running (Docker version)
if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ PostgreSQL not running. Starting Docker container...${NC}"
    if command -v docker &> /dev/null; then
        docker-compose up -d postgres
        sleep 5
    else
        echo -e "${RED}❌ Please start PostgreSQL Docker container manually${NC}"
        exit 1
    fi
fi

# Database should already exist in Docker container
echo -e "${GREEN}✅ PostgreSQL Docker container ready${NC}"

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Step 1: Start Anvil if not running
if ! check_port 8545; then
    echo -e "${BLUE}🔨 Starting Anvil blockchain...${NC}"
    anvil --chain-id 31337 --host 0.0.0.0 &
    ANVIL_PID=$!
    sleep 5
    
    if ! check_port 8545; then
        echo -e "${RED}❌ Failed to start Anvil${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Anvil started (PID: $ANVIL_PID)${NC}"
else
    echo -e "${GREEN}✅ Anvil already running${NC}"
fi

# Step 2: Deploy contracts
echo -e "${BLUE}🚀 Deploying test contracts and data...${NC}"
cd "$(dirname "$0")"

# Check if brownie networks are working
echo -e "${BLUE}Checking brownie network configuration...${NC}"
if brownie networks list | grep -q "anvil"; then
    NETWORK="anvil"
    echo -e "${GREEN}✅ Using anvil network${NC}"
else
    NETWORK="development"
    echo -e "${YELLOW}⚠️ Using development network (anvil not configured)${NC}"
fi

# Run deployment with verbose error reporting
echo -e "${BLUE}Running deployment script...${NC}"
if brownie run scripts/deploy/test_deployment.py --network $NETWORK; then
    echo -e "${GREEN}✅ Contracts deployed successfully${NC}"
else
    echo -e "${RED}❌ Contract deployment failed${NC}"
    echo -e "${RED}Check the output above for specific error details${NC}"
    echo -e "${YELLOW}Common issues:${NC}"
    echo -e "${YELLOW}  - Anvil not running on port 8545${NC}"
    echo -e "${YELLOW}  - Network configuration mismatch${NC}"
    echo -e "${YELLOW}  - Insufficient gas or gas price${NC}"
    echo -e "${YELLOW}  - Contract compilation issues${NC}"
    exit 1
fi

# Step 3: Start API backend
if ! check_port 8000; then
    echo -e "${BLUE}🖥️ Starting FastAPI backend...${NC}"
    cd monitoring/api
    
    # Install requirements if needed
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    DATABASE_URL="postgresql://postgres:password@localhost:5432/auction" uvicorn main:app --host 0.0.0.0 --port 8000 &
    API_PID=$!
    cd ../..
    
    if wait_for_service "http://localhost:8000/health" "FastAPI"; then
        echo -e "${GREEN}✅ API backend started (PID: $API_PID)${NC}"
    else
        echo -e "${RED}❌ API backend failed to start${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ API backend already running${NC}"
fi

# Step 4: Start React UI
if ! check_port 3000; then
    echo -e "${BLUE}⚛️ Starting React UI...${NC}"
    cd ui
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    
    npm run dev &
    UI_PID=$!
    cd ..
    
    if wait_for_service "http://localhost:3000" "React UI"; then
        echo -e "${GREEN}✅ React UI started (PID: $UI_PID)${NC}"
    else
        echo -e "${RED}❌ React UI failed to start${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ React UI already running${NC}"
fi

# Step 5: Start monitoring services
echo -e "${BLUE}📊 Starting monitoring services...${NC}"

# Price monitor
cd scripts/monitor
DATABASE_URL="postgresql://postgres:password@localhost:5432/auction" python3 price_monitor.py --once &
MONITOR_PID=$!
cd ../..
echo -e "${GREEN}✅ Price monitor started (PID: $MONITOR_PID)${NC}"

# Activity simulator  
brownie run scripts/simulate/continuous_activity.py --network $NETWORK &
SIMULATOR_PID=$!
echo -e "${GREEN}✅ Activity simulator started (PID: $SIMULATOR_PID)${NC}"

# Summary
echo -e "\n${GREEN}🎉 Auction House is now running!${NC}"
echo -e "\n📍 ${BLUE}Access Points:${NC}"
echo -e "   🌐 UI Dashboard:  ${YELLOW}http://localhost:3000${NC}"
echo -e "   🔌 API Docs:      ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "   ⛓️  Anvil RPC:     ${YELLOW}http://localhost:8545${NC}"

echo -e "\n🔄 ${BLUE}Running Services:${NC}"
echo -e "   📱 React UI       (PID: ${UI_PID:-'N/A'})"
echo -e "   🖥️  FastAPI       (PID: ${API_PID:-'N/A'})" 
echo -e "   🔨 Anvil         (PID: ${ANVIL_PID:-'N/A'})"
echo -e "   📊 Price Monitor  (PID: ${MONITOR_PID:-'N/A'})"
echo -e "   🤖 Simulator     (PID: ${SIMULATOR_PID:-'N/A'})"

echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"

# Trap Ctrl+C to cleanup
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    
    # Kill background processes
    for pid in $UI_PID $API_PID $ANVIL_PID $MONITOR_PID $SIMULATOR_PID; do
        if [ ! -z "$pid" ]; then
            kill $pid 2>/dev/null || true
        fi
    done
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running
wait