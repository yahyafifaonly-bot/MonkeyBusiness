#!/bin/bash

# Complete Backtesting Pipeline for Strategy1_EMA_RSI
# This script:
# 1. Downloads 3 years of 1-minute Binance data
# 2. Runs backtest
# 3. Generates detailed analysis reports
# 4. Creates updatable log files

echo "=========================================="
echo "COMPLETE BACKTESTING PIPELINE"
echo "Strategy1_EMA_RSI (Relaxed Version)"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Download 3 years of 1-minute data from Binance"
echo "  2. Run comprehensive backtest"
echo "  3. Generate detailed performance reports"
echo "  4. Show win rate, trade count, and all metrics"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "Step 1/3: Downloading historical data..."
echo "=========================================="
chmod +x download_backtest_data.sh
./download_backtest_data.sh

if [ $? -ne 0 ]; then
    echo "Error downloading data. Exiting."
    exit 1
fi

echo ""
echo "Step 2/3: Running backtest..."
echo "=========================================="
chmod +x run_backtest.sh
./run_backtest.sh

if [ $? -ne 0 ]; then
    echo "Error running backtest. Exiting."
    exit 1
fi

echo ""
echo "Step 3/3: Analyzing results..."
echo "=========================================="

# Find the most recent backtest result
LATEST_RESULT=$(find backtest_results -name "backtest-result.json" -type f -print0 | xargs -0 ls -t | head -1)

if [ -z "$LATEST_RESULT" ]; then
    echo "No backtest results found!"
    exit 1
fi

echo "Analyzing: $LATEST_RESULT"
echo ""

chmod +x analyze_backtest.py
python3 analyze_backtest.py "$LATEST_RESULT"

echo ""
echo "=========================================="
echo "BACKTEST COMPLETE!"
echo "=========================================="
echo ""
echo "All results saved in: $(dirname $LATEST_RESULT)"
echo ""
echo "Files created:"
echo "  - backtest-result.json (raw data)"
echo "  - backtest_report.txt (readable report)"
echo ""
echo "You can re-analyze anytime with:"
echo "  python3 analyze_backtest.py $LATEST_RESULT"
echo ""
