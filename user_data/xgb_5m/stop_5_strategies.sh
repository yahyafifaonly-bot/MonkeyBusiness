#!/bin/bash
################################################################################
# Stop All 5 Strategies
# Works on BOTH Local and VPS
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "Stopping All 5 Strategies"
echo "================================================"

# Stop each strategy
for i in 1 2 3 4 5; do
    echo "Stopping Strategy $i..."

    # Find and kill the process
    pid=$(pgrep -f "config_strategy${i}.json")

    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null
        echo "  ✓ Stopped (PID: $pid)"
    else
        echo "  ⚠ Not running"
    fi
done

# Stop dashboard
echo "Stopping Dashboard..."
pid=$(pgrep -f "monitor.py")
if [ -n "$pid" ]; then
    kill $pid 2>/dev/null
    echo "  ✓ Dashboard stopped"
else
    echo "  ⚠ Dashboard not running"
fi

echo ""
echo "All services stopped"
echo ""
