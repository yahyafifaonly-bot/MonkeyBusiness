#!/bin/bash
################################################################################
# Check Status of All 5 Strategies
# Works on BOTH Local and VPS
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "5 EMA Strategies Status"
echo "================================================"

# Function to check if port is listening
check_port() {
    if lsof -i:$1 > /dev/null 2>&1 || netstat -an | grep -q ":$1.*LISTEN" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check strategy status
check_strategy() {
    local num=$1
    local port=$((8084 + num))
    local name="Strategy $num"

    printf "%-30s " "$name (port $port):"

    # Check if process is running
    if pgrep -f "config_strategy${num}.json" > /dev/null; then
        pid=$(pgrep -f "config_strategy${num}.json")

        # Check if port is listening
        if check_port $port; then
            echo "✓ Running (PID: $pid)"
        else
            echo "⚠ Running but port $port not responding (PID: $pid)"
        fi
    else
        echo "✗ Not running"
    fi
}

# Check all strategies
for i in 1 2 3 4 5; do
    check_strategy $i
done

# Check dashboard
printf "%-30s " "Dashboard (port 5001):"
if pgrep -f "monitor.py" > /dev/null; then
    pid=$(pgrep -f "monitor.py")
    if check_port 5001; then
        echo "✓ Running (PID: $pid)"
    else
        echo "⚠ Running but port not responding (PID: $pid)"
    fi
else
    echo "✗ Not running"
fi

echo ""
echo "================================================"
echo "URLs (replace localhost with VPS IP if on VPS)"
echo "================================================"
echo ""
for i in 1 2 3 4 5; do
    port=$((8084 + i))
    echo "  Strategy $i:  http://localhost:$port"
done
echo "  Dashboard:  http://localhost:5001"
echo ""
