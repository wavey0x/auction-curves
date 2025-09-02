#!/bin/bash

# Modern Development Orchestration Script for Auction System
# Starts all services needed for local development in a unified way
# Usage: ./dev.sh [OPTIONS]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION_NAME="auction_dev"
LOG_DIR="$SCRIPT_DIR/logs"
SERVICES=("postgres" "api" "indexer" "ui" "prices")

# Default options
ATTACH_SESSION=false
SKIP_UI=false
USE_TMUX=true
USE_MOCK_DATA=false

# Create logs directory
mkdir -p "$LOG_DIR"

show_help() {
    cat <<EOF
🏛️ Auction System Development Orchestrator

Usage: ./dev.sh [OPTIONS]

OPTIONS:
  --mock          Use mock data provider (no database required)
  --no-ui         Skip starting the React UI
  --attach        Attach to tmux session after starting services
  --no-tmux       Use background processes instead of tmux
  --help, -h      Show this help message

SERVICES MANAGED:
  📦 PostgreSQL   Database (via Docker if needed)
  🖥️  API Server   FastAPI backend on port 8000
  📊 Indexer      Custom Web3.py blockchain indexer
  ⚛️  React UI     Vite dev server on port 3000
  💰 Price Services All pricing services (ypm, odos, enso)

EXAMPLES:
  ./dev.sh                    # Start all services with tmux
  ./dev.sh --mock             # Start with mock data (no database)
  ./dev.sh --no-ui            # Start without React UI
  ./dev.sh --attach           # Start and attach to session
  ./dev.sh --no-tmux          # Use background processes

CONTROL:
  • Use 'tmux attach -t $SESSION_NAME' to connect to session
  • Use Ctrl+C to stop all services
  • Individual service logs in ./logs/
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mock)
            USE_MOCK_DATA=true
            shift
            ;;
        --no-ui)
            SKIP_UI=true
            shift
            ;;
        --attach)
            ATTACH_SESSION=true
            shift
            ;;
        --no-tmux)
            USE_TMUX=false
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Progress tracking
TOTAL_STEPS=0
CURRENT_STEP=0

# Calculate total steps based on configuration
calculate_steps() {
    TOTAL_STEPS=7  # Base steps: env, prereq, db, cleanup, tmux, api, indexer, pricing
    if [ "$SKIP_UI" = false ]; then
        TOTAL_STEPS=$((TOTAL_STEPS + 1))  # UI service
    fi
    if [ "$USE_MOCK_DATA" = true ]; then
        TOTAL_STEPS=$((TOTAL_STEPS - 2))  # No indexer/pricing in mock mode
    fi
}

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    local progress="[$CURRENT_STEP/$TOTAL_STEPS]"
    local bar_length=20
    local filled=$((CURRENT_STEP * bar_length / TOTAL_STEPS))
    local empty=$((bar_length - filled))
    local bar="$(printf '%*s' $filled '' | tr ' ' '█')$(printf '%*s' $empty '' | tr ' ' '░')"
    echo -e "${BLUE}[$(date +'%H:%M:%S')] $progress [$bar] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if port is in use
check_port() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            return 0
        fi
        
        sleep 2
        ((attempt++))
    done
    
    error "$name failed to start after $max_attempts attempts"
    return 1
}

# Load environment variables
load_environment() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        error ".env file not found"
        echo "Please create .env file based on .env.example"
        exit 1
    fi
    
    # Load .env file
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    
    # Set development mode explicitly
    export APP_MODE="dev"
    
    # Use dev-specific variables
    export DATABASE_URL="${DEV_DATABASE_URL:-postgresql://wavey@localhost:5433/auction_dev}"
    export NETWORKS_ENABLED="${DEV_NETWORKS_ENABLED:-local}"
    export CORS_ORIGINS="${DEV_CORS_ORIGINS:-http://localhost:3000}"
    
    # Map production Ethereum variables for development indexing
    export ETHEREUM_RPC_URL="${PROD_ETHEREUM_RPC_URL:-https://guest:guest@eth.wavey.info}"
    export ETHEREUM_FACTORY_ADDRESS="${PROD_ETHEREUM_FACTORY_ADDRESS:-0xCfA510188884F199fcC6e750764FAAbE6e56ec40}"
    export ETHEREUM_START_BLOCK="${PROD_ETHEREUM_START_BLOCK:-21835027}"
    
    log "Environment loaded (mode: $APP_MODE)"
    log "Database: $DATABASE_URL"
    log "Networks: $NETWORKS_ENABLED"
}

# Setup unified virtual environment
setup_venv() {
    step "Setting up unified Python virtual environment..."
    
    # Check if virtual environment exists
    if [ ! -d "$SCRIPT_DIR/venv" ]; then
        log "Creating virtual environment..."
        python3 -m venv "$SCRIPT_DIR/venv"
    fi
    
    # Activate virtual environment and install dependencies
    source "$SCRIPT_DIR/venv/bin/activate"
    
    # Check if dependencies are installed by testing for key packages
    if ! python3 -c "import web3, psycopg2, fastapi" 2>/dev/null; then
        log "Installing Python dependencies..."
        pip install -q --upgrade pip
        
        # Try the working requirements file first, fallback to main requirements
        if [ -f "$SCRIPT_DIR/requirements-working.txt" ]; then
            pip install -q -r "$SCRIPT_DIR/requirements-working.txt"
        else
            # Install core dependencies manually to avoid conflicts
            pip install -q web3 psycopg2-binary pyyaml fastapi uvicorn asyncpg sqlalchemy httpx
        fi
        
        success "Dependencies installed"
    else
        log "Dependencies already installed"
    fi
    
    # Test that we can import required modules
    if python3 -c "import web3, psycopg2; print('✅ Core dependencies verified')" 2>/dev/null; then
        success "Virtual environment ready"
    else
        error "Virtual environment setup failed - dependencies not working"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Python
    if ! command_exists python3; then
        missing_deps+=("python3")
    fi
    
    # Check Node.js if UI is enabled
    if [ "$SKIP_UI" = false ] && ! command_exists npm; then
        missing_deps+=("npm")
    fi
    
    # Check tmux if using tmux
    if [ "$USE_TMUX" = true ] && ! command_exists tmux; then
        warn "tmux not found, falling back to background processes"
        USE_TMUX=false
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
}

# Check database connectivity
check_database() {
    log "Checking database connectivity..."
    
    if ! psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
        warn "Cannot connect to database, trying to start Docker container..."
        
        if command_exists docker-compose; then
            docker-compose up -d postgres
            sleep 5
            
            if ! psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
                error "Still cannot connect to database"
                echo "Please ensure PostgreSQL is running with correct credentials"
                echo "Expected connection: $DATABASE_URL"
                exit 1
            fi
        else
            error "PostgreSQL not accessible and Docker Compose not available"
            exit 1
        fi
    fi
    
    success "Database connection verified"
}

# Kill existing processes for clean start
cleanup_existing() {
    log "Cleaning up existing processes..."
    
    # Kill tmux session if it exists
    if [ "$USE_TMUX" = true ] && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        tmux kill-session -t "$SESSION_NAME"
        log "Killed existing tmux session"
    fi
    
    # Kill processes by port
    for port in 3000 8000; do
        pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
            log "Killed processes on port $port"
        fi
    done
    
    # Kill specific processes
    pkill -f "python.*indexer.py" 2>/dev/null || true
    pkill -f "python.*app.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    sleep 2
}

# Setup tmux session
setup_tmux() {
    if [ "$USE_TMUX" = false ]; then
        return 0
    fi
    
    log "Setting up tmux session: $SESSION_NAME"
    
    # Create new session detached
    tmux new-session -d -s "$SESSION_NAME" -n "main"
    
    # Create panes for each service
    tmux send-keys -t "$SESSION_NAME:main" "echo 'Auction Development Environment'" Enter
    tmux send-keys -t "$SESSION_NAME:main" "echo 'Services starting...'" Enter
    
    # Split window into panes
    tmux split-window -t "$SESSION_NAME:main" -v
    tmux split-window -t "$SESSION_NAME:main" -h
    tmux select-pane -t "$SESSION_NAME:main" -U
    tmux split-window -t "$SESSION_NAME:main" -h
    
    if [ "$SKIP_UI" = false ]; then
        tmux select-pane -t "$SESSION_NAME:main" -D
        tmux select-pane -t "$SESSION_NAME:main" -L
        tmux split-window -t "$SESSION_NAME:main" -v
    fi
    
    # Select first pane
    tmux select-pane -t "$SESSION_NAME:main" -t 0
    
}

# Start API service
start_api() {
    if [ "$USE_MOCK_DATA" = true ]; then
        step "Starting API service (mock mode)..."
        local cmd="source '$SCRIPT_DIR/venv/bin/activate' && cd '$SCRIPT_DIR/monitoring/api' && python3 app.py --mock"
    else
        step "Starting API service (database mode)..."
        local cmd="source '$SCRIPT_DIR/venv/bin/activate' && cd '$SCRIPT_DIR/monitoring/api' && python3 app.py"
    fi
    local log_file="$LOG_DIR/api_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 1 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/api.pid"
    fi
    
    # Wait for API to be ready
    sleep 5
    if wait_for_service "http://localhost:8000/health" "API"; then
        success "API service ready on port 8000"
    else
        error "Failed to start API service"
        exit 1
    fi
}

# Start indexer service
start_indexer() {
    if [ "$USE_MOCK_DATA" = true ]; then
        return 0
    fi
    
    step "Starting indexer service..."
    
    local cmd="source '$SCRIPT_DIR/venv/bin/activate' && cd '$SCRIPT_DIR/indexer' && python3 indexer.py --network \${DEV_INDEXER_NETWORKS:-ethereum,local}"
    local log_file="$LOG_DIR/indexer_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 2 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/indexer.pid"
    fi
    
    sleep 3
    success "Indexer service ready"
}

# Start pricing services
start_pricing() {
    if [ "$USE_MOCK_DATA" = true ]; then
        return 0
    fi
    
    step "Starting pricing services..."
    
    local cmd="cd '$SCRIPT_DIR' && ./scripts/run_price_service.sh --pricer all --parallel"
    local log_file="$LOG_DIR/pricing_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 3 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/pricing.pid"
    fi
    
    sleep 2
    success "Pricing services ready"
}

# Start UI service
start_ui() {
    if [ "$SKIP_UI" = true ]; then
        return 0
    fi
    
    step "Starting React UI..."
    
    local cmd="cd '$SCRIPT_DIR/ui' && npm install && npm run dev"
    local log_file="$LOG_DIR/ui_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 4 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/ui.pid"
    fi
    
    # Wait for UI to be ready
    sleep 10
    if wait_for_service "http://localhost:3000" "React UI"; then
        success "React UI ready on port 3000"
    else
        warn "React UI may still be starting, check logs if needed"
    fi
}

# Show service summary
show_summary() {
    echo
    log "📍 Access Points:"
    if [ "$SKIP_UI" = false ]; then
        echo "   🌐 UI Dashboard:  http://localhost:3000"
    fi
    echo "   🔌 API Health:    http://localhost:8000/health"
    echo "   📊 API Docs:      http://localhost:8000/docs"
    echo
    log "📋 Session Management:"
    if [ "$USE_TMUX" = true ]; then
        echo "   🖥️  Tmux Session:  tmux attach -t $SESSION_NAME"
        echo "   📱 Session Panes:"
        echo "      • Pane 0: Main dashboard"
        echo "      • Pane 1: API service"
        echo "      • Pane 2: Indexer service"
        echo "      • Pane 3: Pricing services"
        if [ "$SKIP_UI" = false ]; then
            echo "      • Pane 4: React UI"
        fi
    else
        echo "   📁 Service PIDs:  Check $LOG_DIR/*.pid files"
    fi
    echo "   📝 Logs:         $LOG_DIR/"
    echo
    warn "Press Ctrl+C to stop all services"
}

# Cleanup function for shutdown
cleanup() {
    echo
    warn "🛑 Shutting down services..."
    
    if [ "$USE_TMUX" = true ]; then
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            tmux kill-session -t "$SESSION_NAME"
            success "Tmux session terminated"
        fi
    else
        # Kill background processes
        for pid_file in "$LOG_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                pid=$(cat "$pid_file")
                kill "$pid" 2>/dev/null || true
                rm -f "$pid_file"
            fi
        done
        
        # Kill by port as fallback
        for port in 3000 8000; do
            pids=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$pids" ]; then
                echo "$pids" | xargs kill -9 2>/dev/null || true
            fi
        done
    fi
    
    success "All services stopped"
    exit 0
}

# Main execution
main() {
    trap cleanup SIGINT SIGTERM
    
    echo "🏛️ Auction System Development Orchestrator"
    echo "=============================================="
    
    calculate_steps
    
    step "Loading environment (mode: ${APP_MODE:-dev})"
    load_environment
    
    step "Checking prerequisites..."
    check_prerequisites
    
    step "Setting up unified virtual environment..."
    setup_venv
    
    if [ "$USE_MOCK_DATA" = false ]; then
        step "Verifying database connection..."
        check_database
    fi
    
    step "Cleaning up existing processes..."
    cleanup_existing
    
    if [ "$USE_TMUX" = true ]; then
        step "Setting up tmux session: $SESSION_NAME"
        setup_tmux
    fi
    
    # Start all services
    start_api
    start_indexer
    start_pricing
    start_ui
    
    echo
    show_summary
    
    # Handle session attachment
    if [ "$USE_TMUX" = true ] && [ "$ATTACH_SESSION" = true ]; then
        log "Attaching to tmux session..."
        tmux attach -t "$SESSION_NAME"
    else
        # Keep script running
        while true; do
            sleep 10
            # Basic health check
            if ! check_port 8000; then
                error "API service appears to have stopped"
                cleanup
            fi
        done
    fi
}

# Run main function
main "$@"