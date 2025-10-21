#!/bin/bash
# Start Production Environment (LIVE TRADING)
# ⚠️  WARNING: This uses REAL money! ⚠️

echo "⚠️  PRODUCTION MODE - LIVE TRADING ⚠️"
echo "====================================="
echo ""
echo "THIS WILL USE REAL MONEY!"
echo "Make sure you have:"
echo "1. ✅ Tested thoroughly in test environment"
echo "2. ✅ Set up your API keys in config_production.json"
echo "3. ✅ Win rate ≥60% in backtests"
echo "4. ✅ Successful paper trading results"
echo ""
read -p "Are you ABSOLUTELY sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled. Good decision - test more first!"
    exit 0
fi

# Change to project directory
cd "$(dirname "$0")/.." || exit

# Check if ML model exists
if [ ! -d "user_data/ml_env/models" ]; then
    echo "❌ Error: No ML models found!"
    echo "Please run ./scripts/start_ml_training.sh first"
    exit 1
fi

# Copy latest model
echo "📦 Copying latest ML model to production..."
cp -r user_data/ml_env/models/* user_data/production_env/models/ 2>/dev/null || true

# Download latest data
echo "📊 Downloading latest data..."
freqtrade download-data \
    --exchange binance \
    --pairs BTC/USDT \
    --timeframes 5m 15m 1h \
    --days 7 \
    --datadir user_data/production_env/data

# Start live trading
echo "🚀 Starting LIVE trading bot..."
echo "Dashboard: http://localhost:8082"
echo "Stop with: Ctrl+C"
echo ""

freqtrade trade \
    --config user_data/production_env/config_production.json \
    --strategy ScalpingLearner \
    --user-data-dir user_data/production_env \
    --datadir user_data/production_env/data
