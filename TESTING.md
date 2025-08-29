# 🧪 Auction House Testing Guide

This document outlines the comprehensive testing strategy for the Auction House project, including unit tests, integration tests, and end-to-end testing workflows.

## Overview

The Auction House project includes three levels of testing:

1. **Unit Tests** - Smart contract functionality 
2. **Integration Tests** - API endpoint validation
3. **End-to-End Tests** - Full system stack verification

## Quick Start

### Run All Tests
```bash
./run-tests.sh
```

### Run Specific Test Types
```bash
./run-tests.sh unit         # Smart contract tests only
./run-tests.sh integration  # API tests only  
./run-tests.sh e2e          # Full system tests only
```

### Manual E2E Testing
```bash
./test-e2e.sh
```

## Test Structure

```
tests/
├── conftest.py           # Pytest configuration
├── test_auction.py       # Smart contract unit tests
└── ...

run-tests.sh             # Main test runner
test-e2e.sh             # E2E test workflow
TESTING.md              # This documentation
```

## 1. Unit Tests (Smart Contracts)

### What's Tested
- Contract deployment and initialization
- Token enabling/disabling functionality
- Auction kicking (starting) mechanisms
- Price calculation and decay over time
- Auction taking (execution) logic
- Access control and security boundaries
- Edge cases and error conditions

### Test Framework
- **Framework**: Pytest with Brownie integration
- **Blockchain**: Anvil (local Ethereum node)
- **Location**: `tests/test_auction.py`

### Key Test Cases

#### Deployment Tests
```python
def test_deployment():
    """Verify contract deploys with correct parameters"""
    assert auction.auction_length() == 3600
    assert auction.starting_price() == 1000000
    # ... more assertions
```

#### Price Calculation Tests  
```python
def test_get_price_calculation():
    """Test price decay formula over time"""
    # Price should decay according to step_decay parameter
    # Verify prices never go negative
    # Test boundary conditions
```

#### Auction Lifecycle Tests
```python
def test_kick_auction():
    """Test starting an auction"""
    
def test_take_auction():  
    """Test executing trades during auction"""
```

### Running Unit Tests

```bash
# Prerequisites
anvil --host 0.0.0.0 --port 8545  # In separate terminal

# Run tests
cd contracts
brownie compile
cd ../tests  
python3 -m pytest test_auction.py -v
```

## 2. Integration Tests (API)

### What's Tested
- API endpoint availability and response codes
- Response data structure validation
- Cross-origin resource sharing (CORS)
- Error handling and edge cases
- API proxy configuration

### Test Framework
- **Tools**: cURL + JSON parsing
- **Server**: FastAPI development server
- **Location**: Integrated into `run-tests.sh`

### API Endpoints Tested
- `GET /health` - Health check
- `GET /auctions` - Auction listings
- `GET /tokens` - Token information
- `GET /activity/kicks` - Kick events
- `GET /activity/takes` - Take events  
- `GET /analytics/overview` - System statistics

### Running Integration Tests

```bash
# Start API server
cd monitoring/api
python3 simple_server.py  # In separate terminal

# Run integration tests
./run-tests.sh integration
```

## 3. End-to-End Tests (Full System)

### What's Tested
- Complete system stack integration
- Blockchain ↔ API ↔ UI data flow
- Smart contract deployment workflow
- UI proxy configuration
- Real-time data updates
- Cross-service communication

### Test Framework
- **Orchestration**: Bash scripting
- **Components**: Anvil + Brownie + FastAPI + React/Vite
- **Location**: `test-e2e.sh`

### E2E Test Workflow

1. **Dependency Check** - Verify all tools installed
2. **Blockchain Setup** - Start Anvil local node
3. **Contract Deployment** - Deploy tokens and auctions
4. **API Server** - Start FastAPI backend
5. **API Validation** - Test all endpoints
6. **UI Server** - Start React development server
7. **Proxy Testing** - Verify UI ↔ API communication
8. **System Validation** - Confirm full stack operational
9. **Status Summary** - Report system health

### Running E2E Tests

```bash
# Full automated workflow
./test-e2e.sh

# This will:
# 1. Start all services
# 2. Deploy contracts  
# 3. Validate system health
# 4. Keep services running for manual testing
```

### E2E Test Output Example

```
🏠 Starting Auction House E2E Testing Workflow...
📋 Checking dependencies...
✅ All dependencies found
📋 Starting Anvil local blockchain...
✅ Anvil started on port 8545
📋 Compiling and deploying smart contracts...
✅ Contracts compiled successfully
✅ Deployment script started
📋 Starting FastAPI server...
✅ API server started on port 8000
📋 Testing API endpoints...
✅ All API endpoints working
📋 Starting UI development server...
✅ UI development server started on port 3000
✅ UI API proxy working correctly
📋 Running final system validation...
✅ All systems operational!

🎉 End-to-End Test PASSED!

📊 System Status:
  • Blockchain: Anvil running on http://localhost:8545
  • API Server: FastAPI running on http://localhost:8000
  • UI Dashboard: React app running on http://localhost:3000
```

## Test Data and Fixtures

### Smart Contract Test Data
- **Test Tokens**: MockERC20Enhanced contracts with configurable decimals
- **Test Accounts**: 10 Brownie test accounts with ETH
- **Test Scenarios**: Various auction configurations and time progressions

### API Test Data  
- **Mock Auctions**: 20 test auctions with different states
- **Mock Tokens**: USDC, USDT, WETH with realistic metadata
- **Mock Events**: Kick and take events with timestamps

### UI Test Data
- **Proxy Testing**: Validates `/api/*` routing to backend
- **Data Flow**: Confirms React components receive API data
- **Real-time Updates**: Tests WebSocket connections (when available)

## Continuous Integration

### Local Development Workflow
```bash
# Before committing code:
./run-tests.sh unit         # Fast contract tests
./run-tests.sh integration  # API validation
git commit -m "feature: ..."

# Before deploying:
./run-tests.sh e2e         # Full system test
```

### Automated Testing Pipeline
The project is designed to support CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run Unit Tests
  run: ./run-tests.sh unit
  
- name: Run Integration Tests  
  run: ./run-tests.sh integration
  
- name: Run E2E Tests
  run: ./run-tests.sh e2e
```

## Debugging Test Failures

### Log Files
All tests write detailed logs to `/tmp/`:
- `/tmp/unit_tests.log` - Smart contract test output
- `/tmp/integration_api.log` - API server logs  
- `/tmp/e2e_test.log` - Full E2E workflow logs
- `/tmp/anvil.log` - Blockchain node logs
- `/tmp/vite.log` - UI development server logs

### Common Issues

#### Unit Tests Failing
```bash
# Check if Anvil is running
curl http://localhost:8545

# Verify contract compilation
cd contracts && brownie compile

# Check test dependencies
pip install eth-brownie pytest
```

#### Integration Tests Failing  
```bash
# Verify API server status
curl http://localhost:8000/health

# Check API logs
tail -f /tmp/integration_api.log
```

#### E2E Tests Failing
```bash
# Check all service status
curl http://localhost:8545  # Anvil
curl http://localhost:8000/health  # API
curl http://localhost:3000  # UI

# Review full E2E log
cat /tmp/e2e_test.log
```

## Performance Testing

### Load Testing API Endpoints
```bash
# Install apache bench
brew install httpie

# Test API performance
for i in {1..100}; do
  curl -s http://localhost:8000/auctions > /dev/null &
done
wait
```

### Contract Gas Usage Analysis
```python
# In brownie console
>>> tx = auction.kick(token_address)
>>> tx.gas_used
124590

>>> tx = auction.take(from_token, to_token, amount)  
>>> tx.gas_used
187320
```

## Security Testing

### Smart Contract Security
- **Access Control**: Only owner can enable tokens
- **Reentrancy**: Safe token transfers
- **Integer Overflow**: Using Solidity 0.8+ safe math
- **Price Manipulation**: Monotonic decay function

### API Security
- **CORS**: Properly configured origins
- **Input Validation**: Parameter sanitization
- **Rate Limiting**: Built into FastAPI
- **Error Handling**: No sensitive data in responses

## Test Coverage

### Smart Contract Coverage
- Contract deployment: ✅
- Token management: ✅  
- Auction lifecycle: ✅
- Price calculations: ✅
- Access control: ✅
- Error conditions: ✅

### API Coverage
- All REST endpoints: ✅
- Error responses: ✅
- CORS handling: ✅
- Data validation: ✅

### E2E Coverage  
- Full deployment workflow: ✅
- Multi-service integration: ✅
- UI data binding: ✅
- Real-time updates: ✅

## Contributing Tests

When adding new features, please include:

1. **Unit tests** for new smart contract functions
2. **Integration tests** for new API endpoints
3. **E2E validation** if adding new UI components
4. **Documentation updates** for new test procedures

### Test Naming Convention
- `test_<functionality>()` - Basic functionality tests
- `test_<functionality>_fails()` - Error condition tests  
- `test_<functionality>_edge_cases()` - Boundary condition tests

---

## Support

For testing issues:
1. Check the logs in `/tmp/`
2. Verify all dependencies are installed
3. Ensure no conflicting processes on ports 8545, 8000, 3000
4. Review this documentation for troubleshooting steps

Happy testing! 🧪✨