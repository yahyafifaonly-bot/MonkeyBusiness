#!/bin/bash

# Run backtest on VPS via SSH
# This script uploads everything to VPS and runs the backtest there

VPS_USER="root"
VPS_HOST="72.61.162.23"
VPS_DIR="/root/freqtrade_backtest"

echo "=========================================="
echo "Running Backtest on VPS"
echo "=========================================="
echo ""

echo "1. Creating backtest directory on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "mkdir -p ${VPS_DIR}"

echo ""
echo "2. Uploading backtest configuration..."
scp config_backtest.json ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/

echo ""
echo "3. Uploading Strategy1_EMA_RSI strategy..."
ssh ${VPS_USER}@${VPS_HOST} "mkdir -p ${VPS_DIR}/user_data/strategies"
scp user_data/Testing_env/strategies/Strategy1_EMA_RSI.py ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/user_data/strategies/

echo ""
echo "4. Starting backtest on VPS..."
echo "   This will take 15-30 minutes..."
echo ""

ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /root/freqtrade_backtest

echo "Downloading 3 years of 1-minute Binance data..."
echo "This may take 10-20 minutes..."

docker run --rm \
    -v "$(pwd)/user_data:/freqtrade/user_data" \
    freqtradeorg/freqtrade:stable \
    download-data \
    --exchange binance \
    --pairs BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT ADA/USDT DOGE/USDT MATIC/USDT DOT/USDT AVAX/USDT \
    --timeframes 1m \
    --days 1095 \
    --data-format-ohlcv json \
    --trading-mode spot

echo ""
echo "Data download complete!"
echo ""
echo "Running backtest..."

docker run --rm \
    -v "$(pwd)/user_data:/freqtrade/user_data" \
    -v "$(pwd)/config_backtest.json:/freqtrade/config_backtest.json" \
    freqtradeorg/freqtrade:stable \
    backtesting \
    --config /freqtrade/config_backtest.json \
    --strategy Strategy1_EMA_RSI \
    --timeframe 1m \
    --timerange 20220101- \
    --export trades \
    --breakdown day week month

echo ""
echo "Backtest complete!"
echo ""
echo "Generating summary..."

# Show backtest summary
docker run --rm \
    -v "$(pwd)/user_data:/freqtrade/user_data" \
    -v "$(pwd)/config_backtest.json:/freqtrade/config_backtest.json" \
    freqtradeorg/freqtrade:stable \
    backtesting-show

ENDSSH

echo ""
echo "=========================================="
echo "Downloading results from VPS..."
echo "=========================================="

# Create local results directory
mkdir -p backtest_results/vps_$(date +%Y%m%d_%H%M%S)
RESULT_DIR="backtest_results/vps_$(date +%Y%m%d_%H%M%S)"

# Download results
scp -r ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/user_data/backtest_results/* ${RESULT_DIR}/

echo ""
echo "=========================================="
echo "BACKTEST COMPLETE!"
echo "=========================================="
echo ""
echo "Results downloaded to: ${RESULT_DIR}"
echo ""
echo "Check the terminal output above for the summary."
echo ""
