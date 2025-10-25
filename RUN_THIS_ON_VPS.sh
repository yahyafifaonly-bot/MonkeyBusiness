#!/bin/bash

echo "================================================"
echo "DIRECT BACKTEST TEST - Run this on your VPS"
echo "================================================"
echo ""

cd ~/freqtrade_backtest

# Test with Strategy1
STRATEGY="Strategy1_EMA_RSI"
LOG_FILE="backtest_logs/MANUAL_TEST_$(date +%Y%m%d_%H%M%S).log"

echo "Testing backtest for: $STRATEGY"
echo "Log file: $LOG_FILE"
echo ""

# Make sure log directory exists
mkdir -p backtest_logs

echo "Step 1: Checking files..."
echo ""

# Check strategy exists
if [ ! -f "user_data/strategies/${STRATEGY}.py" ]; then
  echo "ERROR: Strategy file missing!"
  echo "Looking for: user_data/strategies/${STRATEGY}.py"
  echo ""
  echo "Available strategies:"
  ls -la user_data/strategies/
  exit 1
fi
echo "✓ Strategy file found"

# Check config exists
if [ ! -f "config_backtest.json" ]; then
  echo "ERROR: Config missing!"
  exit 1
fi
echo "✓ Config file found"

# Check data exists
if [ ! -d "user_data/data/binance" ]; then
  echo "ERROR: Data directory missing!"
  exit 1
fi
echo "✓ Data directory found"
echo ""

# Show available data
echo "Available data files:"
ls -lh user_data/data/binance/*.json | head -5
echo ""

echo "Step 2: Running backtest..."
echo "Command: docker run freqtradeorg/freqtrade:stable backtesting --strategy $STRATEGY"
echo ""
echo "================================================"
echo ""

# Run backtest - capture EVERYTHING
set -x  # Show commands being executed

docker run --rm \
  -v "$(pwd)/user_data:/freqtrade/user_data" \
  -v "$(pwd)/config_backtest.json:/freqtrade/config_backtest.json" \
  freqtradeorg/freqtrade:stable \
  backtesting \
  --config /freqtrade/config_backtest.json \
  --strategy "$STRATEGY" \
  --timerange 20250826- 2>&1 | tee "$LOG_FILE"

EXIT_CODE=$?
set +x

echo ""
echo "================================================"
echo "Backtest finished with exit code: $EXIT_CODE"
echo "================================================"
echo ""

if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ BACKTEST FAILED!"
  echo ""
  echo "Check the output above for errors"
else
  echo "✅ BACKTEST COMPLETED"
  echo ""
  echo "Log file: ~/freqtrade_backtest/$LOG_FILE"
  echo ""
  echo "Log file size:"
  ls -lh "$LOG_FILE"
  echo ""
  echo "First 20 lines of log:"
  head -20 "$LOG_FILE"
  echo ""
  echo "Last 50 lines of log:"
  tail -50 "$LOG_FILE"
fi

echo ""
echo "================================================"
echo "TEST COMPLETE"
echo "================================================"
