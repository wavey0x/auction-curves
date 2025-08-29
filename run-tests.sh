#!/bin/bash

# Auction House Test Runner
# Runs unit tests, integration tests, and E2E tests

set -e

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

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🧪 Auction House Test Suite"
echo "=========================="

# Parse command line arguments
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    "unit")
        echo "Running unit tests only..."
        ;;
    "integration") 
        echo "Running integration tests only..."
        ;;
    "e2e")
        echo "Running E2E tests only..."
        ;;
    "all")
        echo "Running all tests..."
        ;;
    *)
        echo "Usage: $0 [unit|integration|e2e|all]"
        exit 1
        ;;
esac

# Step 1: Unit Tests (Smart Contracts)
if [ "$TEST_TYPE" = "unit" ] || [ "$TEST_TYPE" = "all" ]; then
    print_step "Running smart contract unit tests..."
    
    # Check if Anvil is running
    if ! curl -s http://localhost:8545 > /dev/null; then
        print_error "Anvil not running. Starting Anvil..."
        anvil --host 0.0.0.0 --port 8545 > /tmp/test_anvil.log 2>&1 &
        ANVIL_PID=$!
        sleep 3
        CLEANUP_ANVIL=true
    fi
    
    cd contracts
    
    # Compile contracts
    print_step "Compiling contracts..."
    brownie compile > /tmp/brownie_test_compile.log 2>&1
    if [ $? -ne 0 ]; then
        print_error "Contract compilation failed"
        cat /tmp/brownie_test_compile.log
        exit 1
    fi
    
    # Run tests
    print_step "Running pytest on smart contracts..."
    cd ../tests
    python3 -m pytest test_auction.py -v > /tmp/unit_tests.log 2>&1
    if [ $? -eq 0 ]; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed"
        cat /tmp/unit_tests.log
        exit 1
    fi
    
    cd ..
    
    # Cleanup Anvil if we started it
    if [ "$CLEANUP_ANVIL" = true ]; then
        kill $ANVIL_PID 2>/dev/null || true
    fi
fi

# Step 2: Integration Tests (API)
if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
    print_step "Running API integration tests..."
    
    # Start API server if not running
    if ! curl -s http://localhost:8000/health > /dev/null; then
        print_step "Starting API server for integration tests..."
        cd monitoring/api
        python3 simple_server.py > /tmp/integration_api.log 2>&1 &
        API_PID=$!
        cd ../..
        sleep 3
        CLEANUP_API=true
    fi
    
    # Test API endpoints
    print_step "Testing API endpoints..."
    
    endpoints=(
        "/health"
        "/auctions" 
        "/tokens"
        "/activity/kicks?limit=5"
        "/activity/takes?limit=5"
        "/analytics/overview"
    )
    
    failed_endpoints=()
    
    for endpoint in "${endpoints[@]}"; do
        response=$(curl -s -w "%{http_code}" http://localhost:8000$endpoint -o /tmp/endpoint_test.json)
        if [ "$response" != "200" ]; then
            failed_endpoints+=("$endpoint")
        fi
    done
    
    if [ ${#failed_endpoints[@]} -eq 0 ]; then
        print_success "All API endpoints working"
    else
        print_error "Failed endpoints: ${failed_endpoints[*]}"
        exit 1
    fi
    
    # Cleanup API if we started it
    if [ "$CLEANUP_API" = true ]; then
        kill $API_PID 2>/dev/null || true
    fi
fi

# Step 3: End-to-End Tests
if [ "$TEST_TYPE" = "e2e" ] || [ "$TEST_TYPE" = "all" ]; then
    print_step "Running End-to-End tests..."
    
    # Check if UI dependencies are installed
    if [ ! -d "ui/node_modules" ]; then
        print_step "Installing UI dependencies..."
        cd ui
        npm install > /tmp/e2e_npm_install.log 2>&1
        if [ $? -ne 0 ]; then
            print_error "Failed to install UI dependencies"
            exit 1
        fi
        cd ..
    fi
    
    # Run the E2E test script
    timeout 600 ./test-e2e.sh > /tmp/e2e_test.log 2>&1
    if [ $? -eq 0 ]; then
        print_success "E2E tests passed"
    else
        print_error "E2E tests failed"
        tail -50 /tmp/e2e_test.log
        exit 1
    fi
fi

# Summary
echo ""
print_success "🎉 All tests completed successfully!"
echo ""
echo "📊 Test Summary:"

if [ "$TEST_TYPE" = "unit" ] || [ "$TEST_TYPE" = "all" ]; then
    echo "  ✅ Unit Tests: Smart contract functionality verified"
fi

if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
    echo "  ✅ Integration Tests: API endpoints working correctly"  
fi

if [ "$TEST_TYPE" = "e2e" ] || [ "$TEST_TYPE" = "all" ]; then
    echo "  ✅ E2E Tests: Full system stack operational"
fi

echo ""
echo "📝 Logs available in /tmp/ directory:"
echo "  - Unit tests: /tmp/unit_tests.log"
echo "  - Integration tests: /tmp/integration_api.log"  
echo "  - E2E tests: /tmp/e2e_test.log"
echo ""
print_success "Auction House testing complete! 🏠"