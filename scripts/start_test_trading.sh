#!/bin/bash
# Start Test Environment (Paper Trading)
# Uses trained model from ML environment

echo "📝 Starting Test Environment (Paper Trading)..."
echo "==============================================="

# Change to project directory
cd "$(dirname "$0")/.." || exit

# Check if ML model exists
if [ ! -d "user_data/ml_env/models" ]; then
    echo "❌ Error: No ML models found!"
    echo "Please run ./scripts/start_ml_training.sh first"
    exit 1
fi

# Copy latest model from ML to Test
echo "📦 Copying latest ML model to test environment..."
cp -r user_data/ml_env/models/* user_data/test_env/models/ 2>/dev/null || true

# Download latest data
echo "📊 Downloading latest data..."
freqtrade download-data \
    --exchange binance \
    --pairs BTC/USDT \
    --timeframes 5m 15m 1h \
    --days 7 \
    --datadir user_data/test_env/data

# Start dry-run trading
echo "🚀 Starting paper trading bot..."
echo "Dashboard: http://localhost:8081"
echo "Stop with: Ctrl+C"
echo ""

freqtrade trade \
    --config user_data/test_env/config_test.json \
    --strategy ScalpingLearner \
    --user-data-dir user_data/test_env \
    --datadir user_data/test_env/data
