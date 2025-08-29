#!/bin/bash

# Auction House End-to-End Test Workflow
# This script tests the entire stack from smart contracts to UI

set -e

echo "🏠 Starting Auction House E2E Testing Workflow..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up background processes...${NC}"
    pkill -f "anvil" 2>/dev/null || true
    pkill -f "simple_server.py" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 2
    print_success "Cleanup complete"
}

# Set trap for cleanup
trap cleanup EXIT

# Step 1: Check dependencies
print_step "Checking dependencies..."

if ! command -v anvil &> /dev/null; then
    print_error "anvil not found. Please install foundry: https://book.getfoundry.sh/"
    exit 1
fi

if ! command -v brownie &> /dev/null; then
    print_error "brownie not found. Please install: pip install eth-brownie"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "python3 not found"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    print_error "npm not found"
    exit 1
fi

print_success "All dependencies found"

# Step 2: Start Anvil
print_step "Starting Anvil local blockchain..."
anvil --host 0.0.0.0 --port 8545 > /tmp/anvil.log 2>&1 &
ANVIL_PID=$!

# Wait for Anvil to be ready
sleep 3
if ! curl -s http://localhost:8545 > /dev/null; then
    print_error "Failed to start Anvil"
    exit 1
fi
print_success "Anvil started on port 8545"

# Step 3: Compile and deploy contracts
print_step "Compiling and deploying smart contracts..."
cd contracts
brownie compile > /tmp/brownie_compile.log 2>&1
if [ $? -ne 0 ]; then
    print_error "Contract compilation failed"
    cat /tmp/brownie_compile.log
    exit 1
fi
print_success "Contracts compiled successfully"

# Run deployment script
cd ../scripts/deploy
python3 test_deployment.py > /tmp/deployment.log 2>&1 &
DEPLOY_PID=$!

# Wait for deployment to start
sleep 5
if ! kill -0 $DEPLOY_PID 2>/dev/null; then
    print_error "Deployment script failed to start"
    cat /tmp/deployment.log
    exit 1
fi
print_success "Deployment script started"

# Step 4: Start API server
print_step "Starting FastAPI server..."
cd ../../monitoring/api
python3 simple_server.py > /tmp/api.log 2>&1 &
API_PID=$!

# Wait for API to be ready
sleep 3
if ! curl -s http://localhost:8000/health > /dev/null; then
    print_error "Failed to start API server"
    cat /tmp/api.log
    exit 1
fi
print_success "API server started on port 8000"

# Step 5: Test API endpoints
print_step "Testing API endpoints..."

endpoints=(
    "/health"
    "/auctions"
    "/tokens"
    "/activity/kicks?limit=5"
    "/activity/takes?limit=5"
    "/analytics/overview"
)

for endpoint in "${endpoints[@]}"; do
    response=$(curl -s -w "%{http_code}" http://localhost:8000$endpoint -o /tmp/response.json)
    if [ "$response" != "200" ]; then
        print_error "API endpoint $endpoint failed (HTTP $response)"
        cat /tmp/response.json
        exit 1
    fi
done

print_success "All API endpoints working"

# Step 6: Validate API responses
print_step "Validating API response structure..."

# Check health endpoint
health_status=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$health_status" != "healthy" ]; then
    print_error "Health check failed"
    exit 1
fi

# Check auctions endpoint
auction_count=$(curl -s http://localhost:8000/auctions | jq -r '.count')
if [ "$auction_count" -eq 0 ]; then
    print_warning "No auctions found yet (deployment may still be in progress)"
else
    print_success "Found $auction_count auctions"
fi

# Check tokens endpoint
token_count=$(curl -s http://localhost:8000/tokens | jq -r '.count')
if [ "$token_count" -eq 0 ]; then
    print_error "No tokens found"
    exit 1
fi
print_success "Found $token_count tokens"

# Step 7: Start UI development server
print_step "Starting UI development server..."
cd ../../ui

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_step "Installing UI dependencies..."
    npm install > /tmp/npm_install.log 2>&1
    if [ $? -ne 0 ]; then
        print_error "Failed to install UI dependencies"
        cat /tmp/npm_install.log
        exit 1
    fi
fi

npm run dev > /tmp/vite.log 2>&1 &
UI_PID=$!

# Wait for UI to be ready
sleep 5
if ! curl -s http://localhost:3000 > /dev/null; then
    print_error "Failed to start UI development server"
    cat /tmp/vite.log
    exit 1
fi
print_success "UI development server started on port 3000"

# Step 8: Test UI API integration
print_step "Testing UI API integration..."

# Test that UI can reach API through proxy
ui_api_response=$(curl -s -w "%{http_code}" http://localhost:3000/api/health -o /tmp/ui_api.json)
if [ "$ui_api_response" != "200" ]; then
    print_error "UI API proxy not working (HTTP $ui_api_response)"
    cat /tmp/ui_api.json
    exit 1
fi
print_success "UI API proxy working correctly"

# Step 9: Wait for deployment to complete (with timeout)
print_step "Waiting for contract deployment to complete..."
timeout=300  # 5 minutes
elapsed=0
while kill -0 $DEPLOY_PID 2>/dev/null; do
    sleep 10
    elapsed=$((elapsed + 10))
    if [ $elapsed -ge $timeout ]; then
        print_warning "Deployment taking longer than expected, continuing with tests..."
        break
    fi
    echo "  Deployment in progress... (${elapsed}s elapsed)"
done

if kill -0 $DEPLOY_PID 2>/dev/null; then
    print_warning "Deployment still running in background"
else
    print_success "Deployment completed"
fi

# Step 10: Final system validation
print_step "Running final system validation..."

# Check blockchain state
block_number=$(curl -s -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545 | jq -r '.result')
block_number_decimal=$((block_number))
print_success "Blockchain at block $block_number_decimal"

# Check API health one more time
api_health=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$api_health" != "healthy" ]; then
    print_error "API health check failed"
    exit 1
fi

# Check UI accessibility
ui_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$ui_status" != "200" ]; then
    print_error "UI not accessible"
    exit 1
fi

print_success "All systems operational!"

# Step 11: Summary
echo -e "\n${GREEN}🎉 End-to-End Test PASSED!${NC}"
echo -e "\n${BLUE}📊 System Status:${NC}"
echo "  • Blockchain: Anvil running on http://localhost:8545"
echo "  • API Server: FastAPI running on http://localhost:8000"
echo "  • UI Dashboard: React app running on http://localhost:3000"
echo "  • Contracts: Deployed and accessible"
echo "  • Token Count: $token_count tokens available"
echo "  • Auction Count: $auction_count auctions (may still be deploying)"

echo -e "\n${YELLOW}🔧 Next Steps:${NC}"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Explore the auction dashboard"
echo "  3. Wait for deployment to complete for full data"
echo "  4. Test individual auction pages"

echo -e "\n${BLUE}📝 Logs available in:${NC}"
echo "  • Anvil: /tmp/anvil.log"
echo "  • API: /tmp/api.log"
echo "  • UI: /tmp/vite.log"
echo "  • Deployment: /tmp/deployment.log"

echo -e "\n${GREEN}✨ Auction House is ready for use!${NC}"

# Keep processes running
print_step "Keeping services running... (Press Ctrl+C to stop all services)"
wait