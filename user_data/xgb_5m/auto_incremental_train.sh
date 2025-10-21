#!/bin/bash
# Automated Daily Incremental Training Script
# This script runs incremental training and restarts the bot with the updated model

set -e

# Configuration
LOG_DIR="/Users/yahya/Monkeybusiness/user_data/xgb_5m/logs"
LOG_FILE="$LOG_DIR/auto_incremental_$(date +%Y%m%d).log"
PROJECT_DIR="/Users/yahya/Monkeybusiness/user_data/xgb_5m"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "======================================================================"
log "Starting Automated Incremental Training"
log "======================================================================"

# Navigate to project directory
cd "$PROJECT_DIR"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log "ERROR: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if bot is running
if ! docker ps | grep -q xgb_5m_bot; then
    log "WARNING: Trading bot is not running. Will train but won't restart."
    BOT_RUNNING=false
else
    log "✓ Trading bot is running"
    BOT_RUNNING=true
fi

# Run incremental training
log "Starting incremental training (last 7 days)..."
if docker-compose run --rm xgb-trading-bot \
    python3 /app/user_data/xgb_5m/incremental_train.py --last-n-days 7 >> "$LOG_FILE" 2>&1; then
    log "✓ Incremental training completed successfully"
else
    log "ERROR: Incremental training failed. Check logs above."
    exit 1
fi

# Restart bot if it was running
if [ "$BOT_RUNNING" = true ]; then
    log "Restarting trading bot to load updated model..."
    if docker-compose restart >> "$LOG_FILE" 2>&1; then
        log "✓ Bot restarted successfully"
    else
        log "ERROR: Failed to restart bot"
        exit 1
    fi

    # Wait a bit for bot to start
    sleep 5

    # Verify bot is running
    if docker ps | grep -q xgb_5m_bot; then
        log "✓ Bot is running with updated model"
    else
        log "ERROR: Bot failed to restart properly"
        exit 1
    fi
else
    log "Skipping bot restart (bot was not running)"
fi

log "======================================================================"
log "Automated Incremental Training Completed Successfully"
log "======================================================================"
log ""

# Keep only last 30 days of logs
find "$LOG_DIR" -name "auto_incremental_*.log" -mtime +30 -delete 2>/dev/null || true

exit 0
