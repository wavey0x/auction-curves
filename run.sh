#!/bin/bash

# Auction Launcher Script
# Unified script to run auction system in different modes
# Usage: ./run.sh [dev|mock|prod] [--ui] [--help]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MODE="dev"
START_UI="true"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Help function
show_help() {
    echo "🏛️ Auction System Launcher"
    echo ""
    echo "Usage: ./run.sh [MODE] [OPTIONS]"
    echo ""
    echo "MODES:"
    echo "  dev     Development mode with Anvil blockchain + PostgreSQL + Rindexer (default)"
    echo "  mock    Mock mode with hardcoded data (no blockchain/database required)" 
    echo "  prod    Production mode with multi-network support"
    echo ""
    echo "OPTIONS:"
    echo "  --no-ui     Skip starting the React UI"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Start in development mode with UI"
    echo "  ./run.sh mock               # Start in mock mode"
    echo "  ./run.sh prod --no-ui       # Start in production mode without UI"
    echo "  ./run.sh dev --help         # Show this help"
    echo ""
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        dev|mock|prod)
            MODE="$1"
            shift
            ;;
        --no-ui)
            START_UI="false"
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🏛️ Starting Auction System in $(echo ${MODE} | tr '[:lower:]' '[:upper:]') mode..."

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
    local max_attempts=${3:-30}
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

# Set environment based on mode
setup_environment() {
    # Check if unified .env file exists
    if [ ! -f .env ]; then
        echo -e "${RED}❌ .env file not found${NC}"
        echo -e "${YELLOW}Please create .env file from template${NC}"
        exit 1
    fi
    
    # Source the unified .env file
    set -a
    source .env
    set +a
    
    # Override APP_MODE with script parameter
    export APP_MODE="$MODE"
    
    # Set mode-specific environment variables from unified config
    case $MODE in
        dev)
            export DATABASE_URL="$DEV_DATABASE_URL"
            export RINDEXER_DATABASE_URL="$DEV_RINDEXER_DATABASE_URL"
            export NETWORKS_ENABLED="$DEV_NETWORKS_ENABLED"
            export CORS_ORIGINS="$DEV_CORS_ORIGINS"
            export ANVIL_RPC_URL="$DEV_ANVIL_RPC_URL"
            export FACTORY_ADDRESS="$DEV_FACTORY_ADDRESS"
            export START_BLOCK="$DEV_START_BLOCK"
            ;;
        mock)
            export DATABASE_URL="$MOCK_DATABASE_URL"
            export RINDEXER_DATABASE_URL="$MOCK_RINDEXER_DATABASE_URL"
            export NETWORKS_ENABLED="$MOCK_NETWORKS_ENABLED"
            export CORS_ORIGINS="$MOCK_CORS_ORIGINS"
            ;;
        prod)
            export DATABASE_URL="$PROD_DATABASE_URL"
            export RINDEXER_DATABASE_URL="$PROD_RINDEXER_DATABASE_URL"
            export NETWORKS_ENABLED="$PROD_NETWORKS_ENABLED"
            export CORS_ORIGINS="$PROD_CORS_ORIGINS"
            export WEB3_INFURA_PROJECT_ID="$PROD_WEB3_INFURA_PROJECT_ID"
            
            # Set network-specific variables for production
            export ETHEREUM_RPC_URL="$PROD_ETHEREUM_RPC_URL"
            export POLYGON_RPC_URL="$PROD_POLYGON_RPC_URL"
            export ARBITRUM_RPC_URL="$PROD_ARBITRUM_RPC_URL"
            export OPTIMISM_RPC_URL="$PROD_OPTIMISM_RPC_URL"
            export BASE_RPC_URL="$PROD_BASE_RPC_URL"
            
            export ETHEREUM_FACTORY_ADDRESS="$PROD_ETHEREUM_FACTORY_ADDRESS"
            export POLYGON_FACTORY_ADDRESS="$PROD_POLYGON_FACTORY_ADDRESS"
            export ARBITRUM_FACTORY_ADDRESS="$PROD_ARBITRUM_FACTORY_ADDRESS"
            export OPTIMISM_FACTORY_ADDRESS="$PROD_OPTIMISM_FACTORY_ADDRESS"
            export BASE_FACTORY_ADDRESS="$PROD_BASE_FACTORY_ADDRESS"
            
            export ETHEREUM_START_BLOCK="$PROD_ETHEREUM_START_BLOCK"
            export POLYGON_START_BLOCK="$PROD_POLYGON_START_BLOCK"
            export ARBITRUM_START_BLOCK="$PROD_ARBITRUM_START_BLOCK"
            export OPTIMISM_START_BLOCK="$PROD_OPTIMISM_START_BLOCK"
            export BASE_START_BLOCK="$PROD_BASE_START_BLOCK"
            
            # Validate production requirements
            if [ -z "$DATABASE_URL" ] || [ -z "$NETWORKS_ENABLED" ]; then
                echo -e "${RED}❌ Production mode requires valid database and network configuration${NC}"
                echo -e "${YELLOW}Please configure PROD_* variables in .env${NC}"
                exit 1
            fi
            ;;
    esac
    
    echo -e "${GREEN}✅ Environment configured for ${MODE} mode${NC}"
    echo -e "${BLUE}   Database: ${DATABASE_URL}${NC}"
    echo -e "${BLUE}   Networks: ${NETWORKS_ENABLED}${NC}"
}

# Kill existing processes for clean restart
kill_existing_processes() {
    if [ "$MODE" = "dev" ]; then
        echo -e "${BLUE}🔪 Killing existing processes for clean restart...${NC}"
        
        # Kill any existing processes
        pkill -f anvil 2>/dev/null || true
        pkill -f "python.*indexer.py" 2>/dev/null || true
        pkill -f "python.*app.py" 2>/dev/null || true
        pkill -f "uvicorn.*app" 2>/dev/null || true
        pkill -f "brownie.*continuous_activity" 2>/dev/null || true
        pkill -f "npm run dev" 2>/dev/null || true
        pkill -f "vite" 2>/dev/null || true
        pkill -f "node.*vite" 2>/dev/null || true
        
        # Kill processes by port (more reliable for UI)
        for port in 3000 8000 8545; do
            pids=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$pids" ]; then
                echo "$pids" | xargs kill -9 2>/dev/null || true
            fi
        done
        
        # Give processes time to terminate
        sleep 3
        
        # Force kill if still running
        pkill -9 -f anvil 2>/dev/null || true
        pkill -9 -f "python.*indexer.py" 2>/dev/null || true
        pkill -9 -f "npm run dev" 2>/dev/null || true
        pkill -9 -f vite 2>/dev/null || true
        
        echo -e "${GREEN}✅ Existing processes cleaned${NC}"
    fi
}

# Check prerequisites based on mode
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites for ${MODE} mode...${NC}"
    
    case $MODE in
        dev)
            # Check brownie
            if ! command -v brownie &> /dev/null; then
                echo -e "${RED}❌ Brownie not found. Install: pip install eth-brownie${NC}"
                exit 1
            fi
            
            # Check PostgreSQL connection with configured DATABASE_URL
            if ! psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
                echo -e "${YELLOW}⚠️ Cannot connect to PostgreSQL with configured DATABASE_URL${NC}"
                echo -e "${YELLOW}   Trying to start Docker container...${NC}"
                if command -v docker-compose &> /dev/null; then
                    docker-compose up -d postgres
                    sleep 5
                    # Test connection again
                    if ! psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
                        echo -e "${RED}❌ Still cannot connect to database after starting Docker${NC}"
                        echo -e "${RED}   Check your DATABASE_URL: $DATABASE_URL${NC}"
                        exit 1
                    fi
                else
                    echo -e "${RED}❌ Please start PostgreSQL manually or install Docker Compose${NC}"
                    exit 1
                fi
            fi
            
            # Check Python3 for custom indexer
            if ! command -v python3 &> /dev/null; then
                echo -e "${RED}❌ Python3 not found. Required for custom indexer${NC}"
                exit 1
            fi
            ;;
        mock)
            # Mock mode has minimal requirements - just Python and Node
            ;;
        prod)
            # Production mode requires all components
            if ! command -v python3 &> /dev/null; then
                echo -e "${RED}❌ Python3 not found. Required for custom indexer${NC}"
                exit 1
            fi
            ;;
    esac
    
    # Check Node.js (required for all modes if UI is enabled)
    if [ "$START_UI" = "true" ] && ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ npm not found. Please install Node.js${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Check database consistency and create missing tables
check_database_consistency() {
    if [ "$MODE" = "mock" ]; then
        return 0  # No database needed for mock mode
    fi
    
    echo -e "${BLUE}🔍 Checking database consistency...${NC}"
    
    # Check if database exists and is accessible
    if ! psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
        echo -e "${RED}❌ Cannot connect to database: $DATABASE_URL${NC}"
        return 1
    fi
    
    # List of required tables
    local required_tables=("auctions" "rounds" "takes" "tokens" "price_history" "indexer_state")
    local missing_tables=()
    
    # Check each required table
    for table in "${required_tables[@]}"; do
        if ! psql "$DATABASE_URL" -c "SELECT 1 FROM $table LIMIT 1;" >/dev/null 2>&1; then
            missing_tables+=("$table")
        fi
    done
    
    # Report missing tables
    if [ ${#missing_tables[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️ Missing tables detected: ${missing_tables[*]}${NC}"
        echo -e "${BLUE}   Applying schema to ensure consistency...${NC}"
        
        # Apply schema (will create missing tables)
        if [ -f "data/postgres/schema.sql" ]; then
            if psql "$DATABASE_URL" < data/postgres/schema.sql >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Schema applied successfully${NC}"
            else
                echo -e "${RED}❌ Failed to apply schema${NC}"
                return 1
            fi
        else
            echo -e "${RED}❌ Schema file not found: data/postgres/schema.sql${NC}"
            return 1
        fi
    fi
    
    # Verify all tables now exist
    local still_missing=()
    for table in "${required_tables[@]}"; do
        if ! psql "$DATABASE_URL" -c "SELECT 1 FROM $table LIMIT 1;" >/dev/null 2>&1; then
            still_missing+=("$table")
        fi
    done
    
    if [ ${#still_missing[@]} -gt 0 ]; then
        echo -e "${RED}❌ Tables still missing after schema application: ${still_missing[*]}${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Database consistency check passed${NC}"
}

# Start blockchain (dev mode only)
start_blockchain() {
    if [ "$MODE" = "dev" ]; then
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
    fi
}

# Deploy contracts (dev mode only)  
deploy_contracts() {
    if [ "$MODE" = "dev" ]; then
        echo -e "${BLUE}🚀 Deploying test contracts...${NC}"
        
        # Determine network
        if brownie networks list | grep -q "anvil"; then
            NETWORK="anvil"
        else
            NETWORK="development"  
        fi
        
        if brownie run scripts/deploy/test_deployment.py --network $NETWORK; then
            echo -e "${GREEN}✅ Contracts deployed successfully${NC}"
            
            # Update indexer config with deployed addresses
            echo -e "${BLUE}📝 Updating indexer config with deployed addresses...${NC}"
            if python3 scripts/update_indexer_config.py; then
                echo -e "${GREEN}✅ Indexer config updated successfully${NC}"
            else
                echo -e "${RED}❌ Failed to update indexer config${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Contract deployment failed${NC}"
            exit 1
        fi
    fi
}

# Start API backend
start_api() {
    if ! check_port 8000; then
        echo -e "${BLUE}🖥️ Starting API in ${MODE} mode...${NC}"
        cd monitoring/api
        
        # Setup Python environment
        if [ ! -d "venv" ]; then
            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt
        else
            source venv/bin/activate
        fi
        
        case $MODE in
            dev)
                python3 app.py &
                ;;
            mock)
                python3 simple_server.py &
                ;;
            prod)
                python3 app.py &
                ;;
        esac
        
        API_PID=$!
        cd "$SCRIPT_DIR"
        
        if wait_for_service "http://localhost:8000/health" "$(echo ${MODE} | tr '[:lower:]' '[:upper:]') API"; then
            echo -e "${GREEN}✅ API started (PID: $API_PID)${NC}"
        else
            echo -e "${RED}❌ API failed to start${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ API already running${NC}"
    fi
}

# Clean dev mode data
cleanup_dev_data() {
    if [ "$MODE" = "dev" ]; then
        echo -e "${BLUE}🧹 Cleaning dev mode data...${NC}"
        
        # Clean indexer logs and temporary files
        echo -e "${BLUE}   Cleaning indexer state files...${NC}"
        rm -f indexer/*.log
        rm -f indexer/config.yaml.backup
        
        # Clean deployment artifacts for fresh start
        echo -e "${BLUE}   Cleaning deployment artifacts...${NC}"
        rm -f deployment_info.json
        
        # Reset custom indexer state for fresh start
        echo -e "${BLUE}   Resetting indexer state...${NC}"
        psql "$DATABASE_URL" -c "
            TRUNCATE TABLE indexer_state CASCADE;
        " >/dev/null 2>&1
        
        # Truncate business logic tables (only if they exist)
        echo -e "${BLUE}   Truncating business logic tables...${NC}"
        for table in auctions rounds takes tokens price_history; do
            psql "$DATABASE_URL" -c "
                DO \$\$ BEGIN
                    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table') THEN
                        EXECUTE 'TRUNCATE TABLE $table CASCADE';
                    END IF;
                END \$\$;
            " >/dev/null 2>&1
        done
        
        # Give database operations time to complete
        sleep 2
        
        echo -e "${GREEN}✅ Dev data cleaned (Custom indexer reset)${NC}"
    fi
}

# Start indexer (dev and prod modes)
start_indexer() {
    if [ "$MODE" = "dev" ] || [ "$MODE" = "prod" ]; then
        echo -e "${BLUE}📊 Starting custom indexer...${NC}"
        cd indexer
        
        # Setup Python environment for indexer
        if [ ! -d "venv" ]; then
            echo -e "${BLUE}Creating Python environment for indexer...${NC}"
            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt
        else
            source venv/bin/activate
        fi
        
        case $MODE in
            dev)
                # Run indexer for local network only
                if [ -f "config.yaml" ]; then
                    echo -e "${BLUE}Using config with deployed factory addresses${NC}"
                else
                    echo -e "${YELLOW}⚠️ Config file config.yaml not found${NC}"
                fi
                python3 indexer.py --network local &
                ;;
            prod)
                # Run indexer for all configured networks
                python3 indexer.py &
                ;;
        esac
        
        INDEXER_PID=$!
        cd "$SCRIPT_DIR"
        echo -e "${GREEN}✅ Custom indexer started (PID: $INDEXER_PID)${NC}"
    fi
}

# Start React UI
start_ui() {
    if [ "$START_UI" = "true" ]; then
        if ! check_port 3000; then
            echo -e "${BLUE}⚛️ Starting React UI...${NC}"
            cd ui
            
            if [ ! -d "node_modules" ]; then
                npm install
            fi
            
            case $MODE in
                prod)
                    # Build and serve for production
                    npm run build
                    npx serve -s build -l 3000 &
                    ;;
                *)
                    # Development server for dev and mock modes
                    npm run dev &
                    ;;
            esac
            
            UI_PID=$!
            cd "$SCRIPT_DIR"
            
            if wait_for_service "http://localhost:3000" "React UI"; then
                echo -e "${GREEN}✅ React UI started (PID: $UI_PID)${NC}"
            else
                echo -e "${YELLOW}⚠️ React UI failed to start${NC}"
            fi
        else
            echo -e "${GREEN}✅ React UI already running${NC}"
        fi
    fi
}

# Start monitoring services (dev mode only)
start_monitoring() {
    if [ "$MODE" = "dev" ]; then
        echo -e "${BLUE}📊 Starting monitoring services...${NC}"
        
        # Price monitor
        cd scripts/monitor
        DATABASE_URL="$DATABASE_URL" python3 price_monitor.py --once &
        MONITOR_PID=$!
        cd "$SCRIPT_DIR"
        echo -e "${GREEN}✅ Price monitor started (PID: $MONITOR_PID)${NC}"
        
        # Activity simulator
        if brownie networks list | grep -q "anvil"; then
            NETWORK="anvil"
        else
            NETWORK="development"
        fi
        brownie run scripts/simulate/continuous_activity.py --network $NETWORK &
        SIMULATOR_PID=$!
        echo -e "${GREEN}✅ Activity simulator started (PID: $SIMULATOR_PID)${NC}"
    fi
}

# Show summary
show_summary() {
    echo -e "\n${GREEN}🎉 Auction System is running in $(echo ${MODE} | tr '[:lower:]' '[:upper:]') mode!${NC}"
    echo -e "\n📍 ${BLUE}Access Points:${NC}"
    
    if [ "$START_UI" = "true" ]; then
        echo -e "   🌐 UI Dashboard:  ${YELLOW}http://localhost:3000${NC}"
    fi
    
    echo -e "   🔌 API Health:    ${YELLOW}http://localhost:8000/health${NC}"
    echo -e "   📊 API Docs:      ${YELLOW}http://localhost:8000/docs${NC}"
    
    if [ "$MODE" = "dev" ]; then
        echo -e "   ⛓️  Anvil RPC:     ${YELLOW}http://localhost:8545${NC}"
    fi
    
    echo -e "\n🎯 ${BLUE}Mode Features:${NC}"
    case $MODE in
        dev)
            echo -e "   ✅ Real blockchain (Anvil)"
            echo -e "   ✅ Real database (PostgreSQL)" 
            echo -e "   ✅ Smart contract deployment"
            echo -e "   ✅ Event indexing (Custom Web3.py)"
            echo -e "   ✅ Price monitoring & simulation"
            ;;
        mock)
            echo -e "   ✅ Hardcoded test data"
            echo -e "   ✅ No blockchain required"
            echo -e "   ✅ No database required"
            echo -e "   ✅ Fast startup for UI testing"
            ;;
        prod)
            echo -e "   ✅ Multi-network support: ${NETWORKS_ENABLED:-'configured'}"
            echo -e "   ✅ Production database"
            echo -e "   ✅ Real blockchain indexing"
            echo -e "   ✅ High-performance configuration"
            ;;
    esac
    
    echo -e "\n🔄 ${BLUE}Running Services:${NC}"
    if [ "$START_UI" = "true" ]; then
        echo -e "   📱 React UI       (PID: ${UI_PID:-'N/A'})"
    fi
    echo -e "   🖥️  $(echo ${MODE} | sed 's/./\U&/') API      (PID: ${API_PID:-'N/A'})"
    
    if [ "$MODE" = "dev" ]; then
        echo -e "   🔨 Anvil         (PID: ${ANVIL_PID:-'N/A'})"
        echo -e "   📊 Price Monitor  (PID: ${MONITOR_PID:-'N/A'})"
        echo -e "   🤖 Simulator     (PID: ${SIMULATOR_PID:-'N/A'})"
    fi
    
    if [ "$MODE" = "dev" ] || [ "$MODE" = "prod" ]; then
        echo -e "   📊 Indexer       (PID: ${INDEXER_PID:-'N/A'})"
    fi
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    
    # Kill all background processes
    for pid in $UI_PID $API_PID $ANVIL_PID $INDEXER_PID $MONITOR_PID $SIMULATOR_PID; do
        if [ ! -z "$pid" ]; then
            kill $pid 2>/dev/null || true
        fi
    done
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Main execution
main() {
    trap cleanup SIGINT SIGTERM
    
    setup_environment
    cleanup_dev_data
    kill_existing_processes
    check_prerequisites
    check_database_consistency
    start_blockchain
    deploy_contracts
    start_api
    start_indexer
    start_ui
    start_monitoring
    show_summary
    
    echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"
    
    # Keep script running
    wait
}

# Run main function
main "$@"