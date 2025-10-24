#!/bin/bash
################################################################################
# VPS Manual Deployment Script
# Copy this entire script and run it on your VPS
################################################################################

set -e

echo "================================================"
echo "Deploying 5 EMA Trading Strategies to VPS"
echo "================================================"

# Configuration
REPO_URL="https://github.com/yahyafifaonly-bot/MonkeyBusiness.git"
PROJECT_DIR="$HOME/MonkeyBusiness"
WORK_DIR="$PROJECT_DIR/user_data/xgb_5m"

# Step 1: Clone or update repository
echo ""
echo "[1/4] Setting up repository..."
if [ -d "$PROJECT_DIR" ]; then
    echo "Repository exists, updating..."
    cd "$PROJECT_DIR"
    git fetch origin
    git checkout develop
    git pull origin develop
else
    echo "Cloning repository..."
    cd "$HOME"
    git clone "$REPO_URL"
    cd "$PROJECT_DIR"
    git checkout develop
fi

echo "✓ Repository ready"

# Step 2: Navigate to project directory
echo ""
echo "[2/4] Navigating to project directory..."
cd "$WORK_DIR"
pwd

# Step 3: Make scripts executable
echo ""
echo "[3/4] Setting up scripts..."
chmod +x start_5_strategies.sh stop_5_strategies.sh status_5_strategies.sh
echo "✓ Scripts ready"

# Step 4: Stop any existing bots and start all 5 strategies
echo ""
echo "[4/4] Starting all 5 strategies..."

# Stop existing
if [ -f "./stop_5_strategies.sh" ]; then
    ./stop_5_strategies.sh
    sleep 2
fi

# Start all 5
./start_5_strategies.sh

echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "Check status with:"
echo "  cd $WORK_DIR && ./status_5_strategies.sh"
echo ""
echo "Access your bots at:"
echo "  Strategy 1: http://$(curl -s ifconfig.me):8085"
echo "  Strategy 2: http://$(curl -s ifconfig.me):8086"
echo "  Strategy 3: http://$(curl -s ifconfig.me):8087"
echo "  Strategy 4: http://$(curl -s ifconfig.me):8088"
echo "  Strategy 5: http://$(curl -s ifconfig.me):8089"
echo "  Dashboard:  http://$(curl -s ifconfig.me):5001"
echo ""
