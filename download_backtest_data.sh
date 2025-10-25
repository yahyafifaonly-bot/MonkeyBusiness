#!/bin/bash

# Script to download 1-minute candle data from Binance for backtesting
# Downloads last 3 years of data for specified pairs

echo "=========================================="
echo "Downloading 1-minute Binance Data"
echo "Last 3 Years for Backtesting"
echo "=========================================="
echo ""

# Calculate dates
END_DATE=$(date +%Y%m%d)
START_DATE=$(date -v-3y +%Y%m%d 2>/dev/null || date -d '3 years ago' +%Y%m%d)

echo "Date Range: $START_DATE to $END_DATE"
echo ""

# Trading pairs to download
PAIRS="BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT ADA/USDT DOGE/USDT MATIC/USDT DOT/USDT AVAX/USDT"

echo "Downloading data for pairs: $PAIRS"
echo ""

# Download data using FreqTrade
docker run --rm \
    -v "$(pwd)/user_data:/freqtrade/user_data" \
    freqtradeorg/freqtrade:stable \
    download-data \
    --exchange binance \
    --pairs $PAIRS \
    --timeframes 1m \
    --days 1095 \
    --data-format-ohlcv json \
    --trading-mode spot

echo ""
echo "=========================================="
echo "Data Download Complete!"
echo "=========================================="
echo ""
echo "Data saved to: user_data/data/binance/"
echo ""
echo "Next steps:"
echo "1. Run the backtesting script: ./run_backtest.sh"
echo ""
