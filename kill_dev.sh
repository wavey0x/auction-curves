#!/bin/bash

# Standalone cleanup script for auction development services
# Usage: ./kill_dev.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SESSION_NAME="auction_dev"

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

echo "🛑 Stopping Auction Development Services"
echo "========================================"

# Kill tmux session if it exists
if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    success "Killed tmux session: $SESSION_NAME"
else
    log "No tmux session found"
fi

# Kill processes by port
for port in 3000 8000; do
    pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        success "Killed processes on port $port"
    else
        log "No processes found on port $port"
    fi
done

# Kill specific processes
services=("python.*indexer.py" "python.*app.py" "npm run dev" "vite" "run_price_service")

for service in "${services[@]}"; do
    if pgrep -f "$service" >/dev/null 2>&1; then
        pkill -f "$service" 2>/dev/null || true
        success "Killed processes matching: $service"
    else
        log "No processes found matching: $service"
    fi
done

# Kill any remaining pricing service processes
if pgrep -f "price_service.*\.py" >/dev/null 2>&1; then
    pkill -f "price_service.*\.py" 2>/dev/null || true
    success "Killed remaining pricing service processes"
fi

# Clean up any PID files if using background processes
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

if [ -d "$LOG_DIR" ]; then
    for pid_file in "$LOG_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file" 2>/dev/null || true)
            if [ -n "$pid" ]; then
                kill "$pid" 2>/dev/null || true
                success "Killed process from PID file: $(basename "$pid_file")"
            fi
            rm -f "$pid_file"
        fi
    done
fi

# Wait a moment for cleanup to complete
sleep 2

echo
success "🎉 All auction development services stopped"
echo
log "You can now:"
echo "   • Run ./dev.sh to restart services"
echo "   • Check remaining processes: ps aux | grep -E '(indexer|auction|vite|npm)'"