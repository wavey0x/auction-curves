#!/bin/bash
# Wrapper to run ypricemagic price service with proper venv and flags
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --pricer <name>        Price service to run: ypm|odos|cowswap|all (default: ymp)
  --network <name>       Brownie network to connect (for ypm only, default: electro)
  --retry-failed         Prioritize previously failed requests first (ypm only)
  --poll-interval <sec>  Poll interval in seconds (default: 5 for ypm, 10 for others)
  --recency-blocks <n>   How recent takes must be in blocks (odos/cowswap only, default: 40)
  --once                 Run a single cycle and exit (useful for testing)
  --parallel             Run all pricers in parallel (when --pricer all)
  --debug                Enable debug logging
  --log <path>           Log file path (default: ./logs/price_service_YYYYMMDD_HHMMSS.log)
  -h, --help             Show this help message

Examples:
  $(basename "$0") --pricer ypm --network mainnet
  $(basename "$0") --pricer odos --poll-interval 10
  $(basename "$0") --pricer cowswap --once
  $(basename "$0") --pricer all --parallel
EOF
}

# Defaults
PRICER="ypm"
NETWORK="electro"
RETRY_FAILED=false
POLL_INTERVAL=""  # Will be set based on pricer
RECENCY_BLOCKS=40
ONCE=false
PARALLEL=false
DEBUG=false
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/price_service_$(date +%Y%m%d_%H%M%S).log"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pricer)
      PRICER="$2"; shift 2;;
    --network)
      NETWORK="$2"; shift 2;;
    --retry-failed)
      RETRY_FAILED=true; shift;;
    --poll-interval)
      POLL_INTERVAL="$2"; shift 2;;
    --recency-blocks)
      RECENCY_BLOCKS="$2"; shift 2;;
    --once)
      ONCE=true; shift;;
    --parallel)
      PARALLEL=true; shift;;
    --debug)
      DEBUG=true; shift;;
    --log)
      LOG_FILE="$2"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown option: $1" >&2
      usage; exit 1;;
  esac
done

# Load env
if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | grep -v '^$' | xargs)
  echo "✅ Loaded environment variables from .env"
else
  echo "❌ No .env file found. Please create one based on .env.example"; exit 1
fi

# Prepare venv
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
python -m pip -q install --upgrade pip

# Ensure dependencies inside venv
python - <<'PY'
import importlib, sys, subprocess
required = [
  ('y', 'ypricemagic>=1.1.0'),
  ('brownie', 'eth-brownie>=1.20.0'),
  ('psycopg2', 'psycopg2-binary>=2.9.0'),
]
to_install = []
for mod, pkg in required:
    try:
        importlib.import_module(mod)
    except Exception:
        to_install.append(pkg)
if to_install:
    # Quiet install, suppress output unless error
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', *to_install], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('READY')
PY

echo "✅ venv ready (deps present)"

# Set default poll interval based on pricer if not specified
if [ -z "$POLL_INTERVAL" ]; then
  case "$PRICER" in
    ypm)
      POLL_INTERVAL=5;;
    odos|cowswap)
      POLL_INTERVAL=10;;
    all)
      POLL_INTERVAL=10;;
    *)
      POLL_INTERVAL=5;;
  esac
fi

# Validate pricer choice
case "$PRICER" in
  ypm|odos|cowswap|all)
    ;;
  *)
    echo "❌ Invalid pricer: $PRICER. Must be one of: ypm, odos, cowswap, all"
    exit 1;;
esac

echo "🚀 Starting Price Service(s)"
echo "📁 Project root: $PROJECT_ROOT"
echo "📝 Log file: $LOG_FILE"
echo "🔧 Pricer: $PRICER"

# Trap cleanup
cleanup() { echo "\n🛑 Stopping price service(s)..."; exit 0; }
trap cleanup SIGINT SIGTERM

# Run service(s) based on pricer choice
case "$PRICER" in
  ypm)
    echo "🌐 Network: $NETWORK"
    PY_ARGS=("scripts/price_service_ypm.py" "--network" "$NETWORK" "--poll-interval" "$POLL_INTERVAL")
    if [ "$RETRY_FAILED" = true ]; then PY_ARGS+=("--retry-failed"); fi
    if [ "$ONCE" = true ]; then PY_ARGS+=("--once"); fi
    python "${PY_ARGS[@]}" 2>&1 | tee "$LOG_FILE"
    ;;
  odos)
    echo "🌐 Chains: Mainnet, Polygon, Arbitrum, Optimism, Base"
    PY_ARGS=("scripts/price_service_odos.py" "--poll-interval" "$POLL_INTERVAL" "--recency-blocks" "$RECENCY_BLOCKS")
    if [ "$ONCE" = true ]; then PY_ARGS+=("--once"); fi
    if [ "$DEBUG" = true ]; then PY_ARGS+=("--debug"); fi
    python "${PY_ARGS[@]}" 2>&1 | tee "$LOG_FILE"
    ;;
  cowswap)
    echo "🌐 Chains: Mainnet only"
    PY_ARGS=("scripts/price_service_cowswap.py" "--poll-interval" "$POLL_INTERVAL" "--recency-blocks" "$RECENCY_BLOCKS")
    if [ "$ONCE" = true ]; then PY_ARGS+=("--once"); fi
    if [ "$DEBUG" = true ]; then PY_ARGS+=("--debug"); fi
    python "${PY_ARGS[@]}" 2>&1 | tee "$LOG_FILE"
    ;;
  all)
    if [ "$PARALLEL" = true ]; then
      echo "🌐 Running all pricers in parallel"
      echo "📝 Individual logs: $LOG_DIR/price_service_*_$(date +%Y%m%d_%H%M%S).log"
      
      # Run all pricers in background with separate log files
      YMP_LOG="$LOG_DIR/price_service_ymp_$(date +%Y%m%d_%H%M%S).log"
      ODOS_LOG="$LOG_DIR/price_service_odos_$(date +%Y%m%d_%H%M%S).log"
      COWSWAP_LOG="$LOG_DIR/price_service_cowswap_$(date +%Y%m%d_%H%M%S).log"
      
      YMP_ARGS=("scripts/price_service_ypm.py" "--network" "$NETWORK" "--poll-interval" "$POLL_INTERVAL")
      if [ "$RETRY_FAILED" = true ]; then YMP_ARGS+=("--retry-failed"); fi
      if [ "$ONCE" = true ]; then YMP_ARGS+=("--once"); fi
      
      ODOS_ARGS=("scripts/price_service_odos.py" "--poll-interval" "$POLL_INTERVAL" "--recency-blocks" "$RECENCY_BLOCKS")
      if [ "$ONCE" = true ]; then ODOS_ARGS+=("--once"); fi
      
      COWSWAP_ARGS=("scripts/price_service_cowswap.py" "--poll-interval" "$POLL_INTERVAL" "--recency-blocks" "$RECENCY_BLOCKS")
      if [ "$ONCE" = true ]; then COWSWAP_ARGS+=("--once"); fi
      
      # Start all services in background
      python "${YMP_ARGS[@]}" 2>&1 | tee "$YMP_LOG" &
      YMP_PID=$!
      
      python "${ODOS_ARGS[@]}" 2>&1 | tee "$ODOS_LOG" &
      ODOS_PID=$!
      
      python "${COWSWAP_ARGS[@]}" 2>&1 | tee "$COWSWAP_LOG" &
      COWSWAP_PID=$!
      
      # Wait for all processes
      echo "Started YPM (PID: $YMP_PID), Odos (PID: $ODOS_PID), CowSwap (PID: $COWSWAP_PID)"
      echo "Use 'tail -f $YMP_LOG' (or odos/cowswap) to follow individual logs"
      
      wait $YMP_PID $ODOS_PID $COWSWAP_PID
    else
      echo "🌐 Running all pricers sequentially (use --parallel for parallel execution)"
      
      # Run ypm first
      echo "\n--- Starting YPM ---"
      YMP_ARGS=("scripts/price_service_ypm.py" "--network" "$NETWORK" "--poll-interval" "$POLL_INTERVAL")
      if [ "$RETRY_FAILED" = true ]; then YMP_ARGS+=("--retry-failed"); fi
      if [ "$ONCE" = true ]; then YMP_ARGS+=("--once"); fi
      python "${YMP_ARGS[@]}" &
      YMP_PID=$!
      
      # Run odos second
      echo "\n--- Starting Odos ---"
      ODOS_ARGS=("scripts/price_service_odos.py" "--poll-interval" "$POLL_INTERVAL" "--recency-blocks" "$RECENCY_BLOCKS")
      if [ "$ONCE" = true ]; then ODOS_ARGS+=("--once"); fi
      python "${ODOS_ARGS[@]}" &
      ODOS_PID=$!
      
      # Run cowswap third
      echo "\n--- Starting CowSwap ---"
      COWSWAP_ARGS=("scripts/price_service_cowswap.py" "--poll-interval" "$POLL_INTERVAL" "--recency-blocks" "$RECENCY_BLOCKS")
      if [ "$ONCE" = true ]; then COWSWAP_ARGS+=("--once"); fi
      python "${COWSWAP_ARGS[@]}" &
      COWSWAP_PID=$!
      
      # Wait for all
      wait $YMP_PID $ODOS_PID $COWSWAP_PID
    fi
    ;;
esac
