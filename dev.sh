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

# Create logs directory
mkdir -p "$LOG_DIR"

show_help() {
    cat <<EOF
🏛️ Auction System Development Orchestrator

Usage: ./dev.sh [OPTIONS]

OPTIONS:
  --no-ui         Skip starting the React UI
  --attach        Attach to tmux session after starting services
  --no-tmux       Use background processes instead of tmux
  --help, -h      Show this help message

SERVICES MANAGED:
  📦 PostgreSQL   Database (via Docker if needed)
  🖥️  API Server   FastAPI backend on port 8000
  📊 Indexer      Custom Web3.py blockchain indexer
  ⚛️  React UI     Vite dev server on port 3000
  💰 Price Services All pricing services (ypm, odos, cowswap)

EXAMPLES:
  ./dev.sh                    # Start all services with tmux
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

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
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
    
    log "Waiting for $name to start..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            success "$name is ready"
            return 0
        fi
        
        if [ $attempt -eq 1 ]; then
            log "Attempting to connect to $name..."
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
    export DATABASE_URL="${DEV_DATABASE_URL:-postgresql://wavey@localhost:5432/auction_dev}"
    export NETWORKS_ENABLED="${DEV_NETWORKS_ENABLED:-local}"
    export CORS_ORIGINS="${DEV_CORS_ORIGINS:-http://localhost:3000}"
    
    success "Environment loaded (mode: $APP_MODE)"
    log "Database: $DATABASE_URL"
    log "Networks: $NETWORKS_ENABLED"
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
    
    success "Prerequisites check passed"
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
    success "Cleanup completed"
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
    
    success "Tmux session created with multiple panes"
}

# Start API service
start_api() {
    log "Starting API service..."
    
    local cmd="cd '$SCRIPT_DIR/monitoring/api' && python3 -m venv venv && source venv/bin/activate && pip install -q -r requirements.txt && python3 app.py"
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
        success "API service started on port 8000"
    else
        error "Failed to start API service"
        exit 1
    fi
}

# Start indexer service
start_indexer() {
    log "Starting indexer service..."
    
    local cmd="cd '$SCRIPT_DIR/indexer' && python3 -m venv venv && source venv/bin/activate && pip install -q -r requirements.txt && python3 indexer.py --network \${DEV_INDEXER_NETWORKS:-ethereum,local}"
    local log_file="$LOG_DIR/indexer_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 2 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/indexer.pid"
    fi
    
    sleep 3
    success "Indexer service started"
}

# Start pricing services
start_pricing() {
    log "Starting pricing services..."
    
    local cmd="cd '$SCRIPT_DIR' && ./scripts/run_price_service.sh --pricer all --parallel"
    local log_file="$LOG_DIR/pricing_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 3 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/pricing.pid"
    fi
    
    sleep 2
    success "Pricing services started"
}

# Start UI service
start_ui() {
    if [ "$SKIP_UI" = true ]; then
        log "Skipping UI service (--no-ui flag)"
        return 0
    fi
    
    log "Starting React UI..."
    
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
        success "React UI started on port 3000"
    else
        warn "React UI may still be starting, check logs if needed"
    fi
}

# Show service summary
show_summary() {
    echo
    success "🎉 All services started successfully!"
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
    
    load_environment
    check_prerequisites
    check_database
    cleanup_existing
    
    if [ "$USE_TMUX" = true ]; then
        setup_tmux
    fi
    
    # Start all services
    start_api
    start_indexer
    start_pricing
    start_ui
    
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