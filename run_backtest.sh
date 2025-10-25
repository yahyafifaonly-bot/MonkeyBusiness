#!/bin/bash

# Comprehensive Backtesting Script for Strategy1_EMA_RSI (Relaxed)
# Generates detailed reports with win rate, trade count, and performance metrics

echo "=========================================="
echo "Strategy1_EMA_RSI Backtesting"
echo "Timeframe: 1 minute"
echo "Period: Last 3 years"
echo "=========================================="
echo ""

# Create reports directory
mkdir -p backtest_results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="backtest_results/strategy1_${TIMESTAMP}"
mkdir -p "$REPORT_DIR"

echo "Running backtest..."
echo "Results will be saved to: $REPORT_DIR"
echo ""

# Run backtest with FreqTrade
docker run --rm \
    -v "$(pwd)/user_data:/freqtrade/user_data" \
    -v "$(pwd)/config_backtest.json:/freqtrade/config_backtest.json" \
    -v "$(pwd)/$REPORT_DIR:/freqtrade/backtest_results" \
    freqtradeorg/freqtrade:stable \
    backtesting \
    --config /freqtrade/config_backtest.json \
    --strategy Strategy1_EMA_RSI \
    --timeframe 1m \
    --timerange 20220101- \
    --export trades \
    --export-filename /freqtrade/backtest_results/backtest-result.json \
    --breakdown day week month \
    --cache none

echo ""
echo "=========================================="
echo "Generating Detailed Reports"
echo "=========================================="
echo ""

# Generate plot (if data available)
echo "Generating performance plot..."
docker run --rm \
    -v "$(pwd)/user_data:/freqtrade/user_data" \
    -v "$(pwd)/config_backtest.json:/freqtrade/config_backtest.json" \
    -v "$(pwd)/$REPORT_DIR:/freqtrade/backtest_results" \
    freqtradeorg/freqtrade:stable \
    plot-dataframe \
    --config /freqtrade/config_backtest.json \
    --strategy Strategy1_EMA_RSI \
    --timeframe 1m \
    --timerange 20240101-20240201 \
    --export-filename /freqtrade/backtest_results/backtest-result.json \
    --indicators1 ema_9 ema_20 \
    --indicators2 rsi \
    --plot-limit 500 \
    2>/dev/null || echo "Plot generation skipped (optional)"

echo ""
echo "=========================================="
echo "Backtest Complete!"
echo "=========================================="
echo ""
echo "Results saved to: $REPORT_DIR/"
echo ""
echo "Files generated:"
echo "  - backtest-result.json (detailed trade data)"
echo "  - Breakdown reports (day/week/month)"
echo ""
echo "To view results, check the files in: $REPORT_DIR/"
echo ""
