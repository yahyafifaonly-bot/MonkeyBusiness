#!/bin/bash
################################################################################
# Start All 5 EMA Strategies
# Works on BOTH Local and VPS
#
# Ports:
#   8085 - Strategy 1: EMA + RSI Pullback
#   8086 - Strategy 2: MACD Ignition
#   8087 - Strategy 3: Stochastic + RSI
#   8088 - Strategy 4: VWAP Confluence
#   8089 - Strategy 5: Breakout Hugging EMA
#   5001 - Dashboard (always)
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "Starting 5 EMA-Based Trading Strategies"
echo "================================================"

# Create logs directory
mkdir -p logs

# Function to start a strategy
start_strategy() {
    local num=$1
    local port=$((8084 + num))
    local strategy="Strategy${num}_$(get_strategy_name $num)"
    local config="config_strategy${num}.json"
    local logfile="logs/strategy${num}.log"

    echo ""
    echo "Starting Strategy $num: $strategy"
    echo "  Port: $port"
    echo "  Config: $config"
    echo "  Log: $logfile"

    # Check if config exists
    if [ ! -f "$config" ]; then
        echo "  ✗ Config file not found: $config"
        return 1
    fi

    # Check if already running
    if pgrep -f "config_strategy${num}.json" > /dev/null; then
        echo "  ⚠ Already running (PID: $(pgrep -f config_strategy${num}.json))"
        return 0
    fi

    # Start the bot
    nohup freqtrade trade \
        --config "$config" \
        --strategy "$strategy" \
        --strategy-path strategies/ \
        --datadir data/ \
        --user-data-dir . \
        > "$logfile" 2>&1 &

    local pid=$!
    sleep 2

    # Verify it started
    if ps -p $pid > /dev/null 2>&1; then
        echo "  ✓ Started (PID: $pid)"
    else
        echo "  ✗ Failed to start - check $logfile"
    fi
}

# Get strategy name
get_strategy_name() {
    case $1 in
        1) echo "EMA_RSI" ;;
        2) echo "MACD_EMA" ;;
        3) echo "Stoch_RSI" ;;
        4) echo "VWAP_EMA" ;;
        5) echo "Breakout_EMA" ;;
        *) echo "Unknown" ;;
    esac
}

# Start all 5 strategies
for i in 1 2 3 4 5; do
    start_strategy $i
done

# Start dashboard (port 5001)
echo ""
echo "Starting Learning Dashboard..."
if ! pgrep -f "monitor.py" > /dev/null; then
    nohup python3 monitor.py > logs/dashboard.log 2>&1 &
    echo "  ✓ Dashboard started on port 5001"
else
    echo "  ⚠ Dashboard already running"
fi

sleep 3

echo ""
echo "================================================"
echo "All Services Started"
echo "================================================"
echo ""
echo "Trading Bots:"
echo "  Strategy 1 (EMA + RSI):       http://localhost:8085"
echo "  Strategy 2 (MACD Ignition):   http://localhost:8086"
echo "  Strategy 3 (Stochastic):      http://localhost:8087"
echo "  Strategy 4 (VWAP):            http://localhost:8088"
echo "  Strategy 5 (Breakout):        http://localhost:8089"
echo ""
echo "Dashboard:"
echo "  Learning Dashboard:           http://localhost:5001"
echo ""
echo "On VPS, replace 'localhost' with your VPS IP"
echo ""
echo "Commands:"
echo "  View status:  ./status_5_strategies.sh"
echo "  Stop all:     ./stop_5_strategies.sh"
echo "  View logs:    tail -f logs/strategy1.log"
echo ""
