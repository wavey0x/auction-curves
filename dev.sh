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
SERVICES=("postgres" "redis" "api" "indexer" "relay" "telegram" "ui" "prices")

# Default options
ATTACH_SESSION=false
SKIP_UI=false
USE_TMUX=true
USE_MOCK_DATA=false
DEBUG_MODE=false

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
  --debug         Enable debug mode with detailed error logging
  --help, -h      Show this help message

SERVICES MANAGED:
  📦 PostgreSQL   Database (via Docker if needed)
  🔗 Redis        Message streaming and caching (via Docker if needed)
  🖥️  API Server   FastAPI backend on port 8000
  📊 Indexer      Custom Web3.py blockchain indexer
  📤 Relay        Outbox to Redis Streams relay service
  📱 Telegram     Bot for real-time auction alerts
  ⚛️  React UI     Vite dev server on port 3000
  💰 Price Services All pricing services (ymp, odos, enso)

EXAMPLES:
  ./dev.sh                    # Start all services with tmux
  ./dev.sh --mock             # Start with mock data (no database)
  ./dev.sh --no-ui            # Start without React UI
  ./dev.sh --attach           # Start and attach to session
  ./dev.sh --no-tmux          # Use background processes
  ./dev.sh --debug            # Enable detailed error output

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
        --debug)
            DEBUG_MODE=true
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
    # Base steps: env, prereq, venv, db, redis, cleanup, tmux, api, indexer, relay, telegram, pricing
    TOTAL_STEPS=12
    if [ "$SKIP_UI" = false ]; then
        TOTAL_STEPS=$((TOTAL_STEPS + 1))  # UI service
    fi
    if [ "$USE_MOCK_DATA" = true ]; then
        TOTAL_STEPS=$((TOTAL_STEPS - 5))  # No indexer, relay, telegram, pricing, redis in mock mode
    fi
}

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    local bar_length=20
    local filled=$((CURRENT_STEP * bar_length / TOTAL_STEPS))
    local empty=$((bar_length - filled))
    local bar="$(printf '%*s' $filled '' | tr ' ' '█')$(printf '%*s' $empty '' | tr ' ' '░')"
    echo -e "${BLUE}[$(date +'%H:%M:%S')] [$bar] $1${NC}"
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

debug() {
    if [ "$DEBUG_MODE" = true ]; then
        echo -e "${BLUE}[$(date +'%H:%M:%S')] 🔍 DEBUG: $1${NC}"
    fi
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
    
    debug "Waiting for $name at $url"
    
    while [ $attempt -le $max_attempts ]; do
        local response=$(curl -s "$url" 2>&1)
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            debug "$name responded successfully: $response"
            return 0
        fi
        
        if [ "$DEBUG_MODE" = true ]; then
            debug "Attempt $attempt/$max_attempts failed for $name: $response"
        fi
        
        sleep 2
        ((attempt++))
    done
    
    error "$name failed to start after $max_attempts attempts"
    if [ "$DEBUG_MODE" = true ]; then
        debug "Final response from $url: $response"
    fi
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
    debug "Testing for key dependencies: web3, psycopg2, fastapi, pydantic_settings"
    if ! python3 -c "import web3, psycopg2, fastapi, pydantic_settings" 2>/dev/null; then
        log "Installing Python dependencies..."
        
        if [ "$DEBUG_MODE" = true ]; then
            pip install --upgrade pip
        else
            pip install -q --upgrade pip
        fi
        
        # Try the working requirements file first, fallback to main requirements
        if [ -f "$SCRIPT_DIR/requirements-working.txt" ]; then
            debug "Installing from requirements-working.txt"
            if [ "$DEBUG_MODE" = true ]; then
                pip install -r "$SCRIPT_DIR/requirements-working.txt"
            else
                pip install -q -r "$SCRIPT_DIR/requirements-working.txt"
            fi
        else
            debug "Requirements file not found, installing core dependencies manually"
            # Install core dependencies manually to avoid conflicts
            if [ "$DEBUG_MODE" = true ]; then
                pip install web3 psycopg2-binary pyyaml fastapi uvicorn asyncpg sqlalchemy httpx pydantic-settings
            else
                pip install -q web3 psycopg2-binary pyyaml fastapi uvicorn asyncpg sqlalchemy httpx pydantic-settings
            fi
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

    # Ensure redis client is available for health checks
    if ! python3 -c "import redis" 2>/dev/null; then
        log "Installing Redis Python client for health checks..."
        if [ "$DEBUG_MODE" = true ]; then
            pip install redis[hiredis]
        else
            pip install -q redis[hiredis]
        fi
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
    debug "Attempting connection to: $DATABASE_URL"
    
    local db_test_output
    db_test_output=$(psql "$DATABASE_URL" -c "SELECT 1;" 2>&1)
    local db_exit_code=$?
    
    if [ $db_exit_code -ne 0 ]; then
        if [ "$DEBUG_MODE" = true ]; then
            debug "Database connection failed with: $db_test_output"
        fi
        
        warn "Cannot connect to database, trying to start Docker container..."
        
        if command_exists docker-compose; then
            debug "Starting PostgreSQL and Redis containers..."
            docker-compose up -d postgres redis
            sleep 5
            
            db_test_output=$(psql "$DATABASE_URL" -c "SELECT 1;" 2>&1)
            db_exit_code=$?
            
            if [ $db_exit_code -ne 0 ]; then
                error "Still cannot connect to database"
                if [ "$DEBUG_MODE" = true ]; then
                    debug "Second connection attempt failed with: $db_test_output"
                fi
                echo "Please ensure PostgreSQL is running with correct credentials"
                echo "Expected connection: $DATABASE_URL"
                exit 1
            fi
        else
            error "PostgreSQL not accessible and Docker Compose not available"
            if [ "$DEBUG_MODE" = true ]; then
                debug "docker-compose command not found"
            fi
            exit 1
        fi
    fi
    
    success "Database connection verified"
}

# Setup Redis connection
setup_redis() {
    if [ "$USE_MOCK_DATA" = true ]; then
        debug "Skipping Redis setup (mock mode)"
        return
    fi
    
    step "Setting up Redis connection..."
    
    local redis_url="${REDIS_URL:-redis://localhost:6379}"

    # Simple timeout wrapper (since macOS lacks coreutils timeout)
    run_with_timeout() {
        local timeout_sec=$1; shift
        local tmp_out
        tmp_out=$(mktemp 2>/dev/null || echo "/tmp/redis_ping_$$.out")
        "$@" > "$tmp_out" 2>&1 &
        local pid=$!
        local elapsed=0
        while kill -0 "$pid" 2>/dev/null; do
            if [ $elapsed -ge $timeout_sec ]; then
                kill -9 "$pid" 2>/dev/null || true
                echo "__TIMEOUT__" && cat "$tmp_out"
                rm -f "$tmp_out" 2>/dev/null || true
                return 124
            fi
            sleep 1
            elapsed=$((elapsed+1))
        done
        wait "$pid"
        local rc=$?
        cat "$tmp_out"
        rm -f "$tmp_out" 2>/dev/null || true
        return $rc
    }

    # Prefer a fast Python ping (more portable than redis-cli -u across versions)
    local python_ping_ok=false
    if command_exists python3; then
        local py_output
        py_output=$(run_with_timeout 6 python3 - <<PY
import os, sys
try:
    import redis
except Exception:
    sys.exit(2)
url=os.getenv('REDIS_URL','${redis_url}')
try:
    r = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    ok = r.ping()
    print('PONG' if ok else 'NO')
    sys.exit(0 if ok else 1)
except Exception as e:
    print('ERR', e)
    sys.exit(1)
PY
)
        local py_rc=$?
        if [ $py_rc -eq 124 ]; then
            debug "Python Redis ping timed out"
        elif [ $py_rc -eq 0 ] && echo "$py_output" | grep -q "PONG"; then
            python_ping_ok=true
            debug "Redis connection successful (python ping)"
        else
            debug "Python Redis ping output: $py_output"
            # If auth-enabled URL failed, try no-auth ping to bootstrap ACLs
            if { [ -n "${REDIS_URL:-}" ] && echo "${REDIS_URL}" | grep -q "@"; } || \
               { [ -n "${REDIS_PUBLISHER_PASS:-}" ] || [ -n "${REDIS_CONSUMER_PASS:-}" ]; }; then
                local noauth_url
                if [ -n "${REDIS_URL:-}" ]; then
                    noauth_url="${REDIS_URL}"
                else
                    noauth_url="${redis_url}"
                fi
                # strip credentials: redis://user:pass@host -> redis://host
                noauth_url=$(printf "%s" "$noauth_url" | sed -E 's#(redis[s]?://)[^@]+@#\1#')
                debug "Auth ping failed; trying unauth ping to $noauth_url"
                py_output=$(REDIS_URL="$noauth_url" run_with_timeout 6 python3 - <<PY
import os, sys
import redis
url=os.getenv('REDIS_URL')
try:
    r = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    ok = r.ping()
    print('PONG' if ok else 'NO')
    sys.exit(0 if ok else 1)
except Exception as e:
    print('ERR', e)
    sys.exit(1)
PY
)
                py_rc=$?
                if [ $py_rc -eq 124 ]; then
                    debug "Unauth Python ping timed out"
                elif [ $py_rc -eq 0 ] && echo "$py_output" | grep -q "PONG"; then
                    python_ping_ok=true
                    debug "Redis unauth ping successful (will run ACL setup next)"
                    # Override redis_url to unauth for subsequent checks
                    redis_url="$noauth_url"
                else
                    debug "Unauth ping failed: $py_output"
                fi
            fi
        fi
    fi

    # Fallback to redis-cli if python ping not available
    if [ "$python_ping_ok" != true ]; then
        if command_exists redis-cli; then
            redis_test_output=$(run_with_timeout 6 redis-cli -u "$redis_url" ping)
            redis_exit_code=$?
        else
            redis_test_output="redis-cli not installed"
            redis_exit_code=127
        fi
    else
        redis_exit_code=0
        redis_test_output="PONG"
    fi
    
    if [ $redis_exit_code -eq 0 ] && [ "$redis_test_output" = "PONG" ]; then
        debug "Redis connection successful"
    else
        if [ "$DEBUG_MODE" = true ]; then
            debug "Redis connection failed with: $redis_test_output"
        fi
        
        warn "Cannot connect to Redis, trying to start Docker container..."

        # Verify Docker engine is available before attempting to start containers
        if ! command_exists docker; then
            error "Docker not available (no 'docker' command). Cannot auto-start Redis."
            echo "Set REDIS_URL to an accessible instance or start Docker Desktop."
            exit 1
        fi
        if ! docker info >/dev/null 2>&1; then
            error "Docker engine is not running. Please start Docker Desktop and retry."
            exit 1
        fi

        # Prefer starting existing container if present to avoid name conflicts
        local redis_container="auction_redis"
        local existing_cid
        existing_cid=$(docker ps -a --filter "name=^/${redis_container}$" -q 2>/dev/null || true)
        if [ -n "$existing_cid" ]; then
            debug "Found existing Redis container: $redis_container ($existing_cid)"
            local is_running
            is_running=$(docker inspect -f '{{.State.Running}}' "$redis_container" 2>/dev/null || echo "false")
            if [ "$is_running" != "true" ]; then
                debug "Starting existing Redis container..."
                docker start "$redis_container" >/dev/null 2>&1 || true
                sleep 2
            else
                debug "Redis container already running"
            fi
        elif command_exists docker-compose; then
            debug "Starting Redis container via docker-compose..."
            docker-compose up -d redis
            sleep 3
        
            if [ "$python_ping_ok" = true ]; then
                # Re-run python ping
                py_output=$(REDIS_URL="$redis_url" run_with_timeout 6 python3 - <<PY
import os, sys
import redis
url=os.getenv('REDIS_URL')
try:
    r = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    ok = r.ping()
    print('PONG' if ok else 'NO')
    sys.exit(0 if ok else 1)
except Exception as e:
    print('ERR', e)
    sys.exit(1)
PY
)
                redis_exit_code=$?
                redis_test_output="$py_output"
            else
                redis_test_output=$(run_with_timeout 6 redis-cli -u "$redis_url" ping)
                redis_exit_code=$?
            fi
            
            if [ $redis_exit_code -ne 0 ] || [ "$redis_test_output" != "PONG" ]; then
                error "Still cannot connect to Redis"
                if [ "$DEBUG_MODE" = true ]; then
                    debug "Second Redis connection attempt failed with: $redis_test_output"
                fi
                echo "Please ensure Redis is running with correct configuration"
                echo "Expected connection: $redis_url"
                exit 1
            fi
        else
            # Try direct docker if docker-compose fails
            warn "docker-compose not available, trying direct Docker..."
            if command_exists docker; then
                debug "Starting Redis with direct Docker..."
                if [ -n "$existing_cid" ]; then
                    debug "Existing container detected; attempting to start"
                    docker start "$redis_container" >/dev/null 2>&1 || true
                else
                    docker run -d --name "$redis_container" -p 6379:6379 redis:7-alpine 2>/dev/null || true
                fi
                sleep 3
                
                if [ "$python_ping_ok" = true ]; then
                    py_output=$(REDIS_URL="$redis_url" run_with_timeout 6 python3 - <<PY
import os, sys
import redis
url=os.getenv('REDIS_URL')
try:
    r = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    ok = r.ping()
    print('PONG' if ok else 'NO')
    sys.exit(0 if ok else 1)
except Exception as e:
    print('ERR', e)
    sys.exit(1)
PY
)
                    redis_exit_code=$?
                    redis_test_output="$py_output"
                else
                    redis_test_output=$(run_with_timeout 6 redis-cli -u "$redis_url" ping)
                    redis_exit_code=$?
                fi
                
                if [ $redis_exit_code -ne 0 ] || [ "$redis_test_output" != "PONG" ]; then
                    error "Redis not accessible via Docker"
                    echo "Please ensure Redis is running with correct configuration"
                    echo "Expected connection: $redis_url"
                    exit 1
                fi
            else
                error "Neither docker-compose nor docker commands available"
                exit 1
            fi
        fi
    fi
    
    success "Redis connection verified"

    # Optionally configure ACL users if passwords are provided
    if [ -n "${REDIS_PUBLISHER_PASS:-}" ] && [ -n "${REDIS_CONSUMER_PASS:-}" ]; then
        step "Configuring Redis ACL users..."
        if command_exists python3; then
            # Use venv python if present
            if [ -d "$SCRIPT_DIR/venv" ]; then
                source "$SCRIPT_DIR/venv/bin/activate"
            fi
            python3 "$SCRIPT_DIR/scripts/setup_redis_acl.py" || warn "Redis ACL setup encountered an issue; continuing"
        else
            warn "Python not available to run ACL setup; skipping"
        fi
    fi
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
    pkill -f "python.*relay_outbox_to_redis.py" 2>/dev/null || true
    pkill -f "python.*telegram_bot.py" 2>/dev/null || true
    pkill -f "python.*telegram_consumer.py" 2>/dev/null || true
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
    
    # Split window into panes for services (0: API, 1: Indexer, 2: Relay, 3: Telegram, 4: Pricing)
    tmux split-window -t "$SESSION_NAME:main" -v    # Pane 1
    tmux split-window -t "$SESSION_NAME:main" -h    # Pane 2
    tmux select-pane -t "$SESSION_NAME:main" -U
    tmux split-window -t "$SESSION_NAME:main" -h    # Pane 3
    tmux select-pane -t "$SESSION_NAME:main" -D
    tmux select-pane -t "$SESSION_NAME:main" -L
    tmux split-window -t "$SESSION_NAME:main" -v    # Pane 4
    
    if [ "$SKIP_UI" = false ]; then
        # Add UI pane if needed
        tmux select-pane -t "$SESSION_NAME:main" -D
        tmux select-pane -t "$SESSION_NAME:main" -R
        tmux split-window -t "$SESSION_NAME:main" -v    # Pane 5 (Pricing)
        tmux split-window -t "$SESSION_NAME:main" -v    # Pane 6 (UI)
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
    
    debug "Starting API with command: $cmd"
    debug "API logs will be written to: $log_file"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 1 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/api.pid"
        debug "API started with PID: $(cat "$LOG_DIR/api.pid")"
    fi
    
    # Wait for API to be ready with better error handling
    sleep 5
    if wait_for_service "http://localhost:8000/health" "API"; then
        success "API service ready on port 8000"
    else
        error "Failed to start API service"
        
        # Show detailed error information in debug mode
        if [ "$DEBUG_MODE" = true ]; then
            debug "Checking API log file for errors..."
            if [ -f "$log_file" ]; then
                debug "Last 20 lines of API log:"
                tail -20 "$log_file" | while read line; do
                    debug "API LOG: $line"
                done
            fi
            
            # Check if Python process is still running
            if [ -f "$LOG_DIR/api.pid" ]; then
                local api_pid=$(cat "$LOG_DIR/api.pid")
                if ! kill -0 "$api_pid" 2>/dev/null; then
                    debug "API process $api_pid has exited"
                else
                    debug "API process $api_pid is still running"
                fi
            fi
        fi
        
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

# Start relay service
start_relay() {
    if [ "$USE_MOCK_DATA" = true ]; then
        return 0
    fi
    
    step "Starting outbox relay service..."
    
    local cmd="source '$SCRIPT_DIR/venv/bin/activate' && cd '$SCRIPT_DIR' && python3 scripts/relay_outbox_to_redis.py"
    local log_file="$LOG_DIR/relay_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 3 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/relay.pid"
    fi
    
    sleep 2
    success "Relay service ready"
}

start_telegram() {
    if [ "$USE_MOCK_DATA" = true ]; then
        return 0
    fi
    
    step "Starting Telegram bot..."
    
    # Check if Telegram bot token is configured (group IDs resolved via YAML fallbacks)
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
        warn "Telegram bot token not configured, skipping Telegram consumer startup"
        return 0
    fi

    local cmd="source '$SCRIPT_DIR/venv/bin/activate' && cd '$SCRIPT_DIR' && python3 scripts/consumers/telegram_consumer.py"
    local log_file="$LOG_DIR/telegram_$(date +%Y%m%d_%H%M%S).log"
    
    if [ "$USE_TMUX" = true ]; then
        tmux send-keys -t "$SESSION_NAME:main" -t 4 "$cmd" Enter
    else
        bash -c "$cmd" > "$log_file" 2>&1 &
        echo $! > "$LOG_DIR/telegram.pid"
    fi
    
    sleep 2
    success "Telegram bot ready"
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
        tmux send-keys -t "$SESSION_NAME:main" -t 5 "$cmd" Enter
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
        tmux send-keys -t "$SESSION_NAME:main" -t 6 "$cmd" Enter
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
        echo "      • Pane 3: Relay service"
        echo "      • Pane 4: Telegram bot"
        echo "      • Pane 5: Pricing services"
        if [ "$SKIP_UI" = false ]; then
            echo "      • Pane 6: React UI"
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
    
    if [ "$DEBUG_MODE" = true ]; then
        log "🔍 DEBUG MODE ENABLED - Detailed logging active"
    fi
    
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
        
        step "Verifying Redis connection..."
        setup_redis
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
    start_relay
    start_telegram
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
