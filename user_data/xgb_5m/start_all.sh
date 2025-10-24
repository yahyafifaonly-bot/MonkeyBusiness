#!/bin/bash
################################################################################
# Start XGBoost Trading Bot + Dashboard
# Works on BOTH Local and VPS
# Run this after deployment to start everything
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "Starting XGBoost Trading System"
echo "================================================"

# Check if we're in Docker or bare metal
if [ -f "docker-compose.yml" ]; then
    echo "Starting via Docker Compose..."
    docker-compose up -d

    echo "✓ Docker containers started"
    docker-compose ps
else
    echo "Starting services directly..."

    # Start trading bot in background (if not in Docker)
    if ! pgrep -f "freqtrade trade" > /dev/null; then
        echo "Starting trading bot..."
        nohup freqtrade trade \
            --config config_xgb_5m.json \
            --strategy XGBScalp5m \
            --strategy-path strategies/ \
            --datadir data/ \
            --user-data-dir . \
            > logs/bot.log 2>&1 &
        echo "✓ Trading bot started (PID: $!)"
    else
        echo "✓ Trading bot already running"
    fi
fi

# Start dashboard (ALWAYS port 5001)
if ! pgrep -f "monitor.py" > /dev/null; then
    echo "Starting Learning Dashboard on port 5001..."
    nohup python3 monitor.py > logs/dashboard.log 2>&1 &
    echo "✓ Dashboard started (PID: $!)"
    sleep 2
else
    echo "✓ Dashboard already running on port 5001"
fi

echo ""
echo "================================================"
echo "✓ All Services Started"
echo "================================================"
echo ""
echo "Access URLs:"
echo "  Trading Bot API:    http://localhost:8083"
echo "  Learning Dashboard: http://localhost:5001"
echo ""
echo "On VPS, replace localhost with your VPS IP:"
echo "  Trading Bot API:    http://YOUR_VPS_IP:8083"
echo "  Learning Dashboard: http://YOUR_VPS_IP:5001"
echo ""
echo "Check status:"
echo "  docker-compose ps     (if using Docker)"
echo "  ps aux | grep -E 'freqtrade|monitor.py'"
echo ""
echo "View logs:"
echo "  tail -f logs/bot.log"
echo "  tail -f logs/dashboard.log"
echo "  tail -f logs/training.log"
echo ""
