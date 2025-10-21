#!/bin/bash
# Start ML Learning Environment
# Downloads data, trains model, runs backtests

echo "🤖 Starting ML Learning Environment..."
echo "======================================"

# Change to project directory
cd "$(dirname "$0")/.." || exit

# Download latest data
echo "📊 Downloading latest data..."
freqtrade download-data \
    --exchange binance \
    --pairs BTC/USDT \
    --timeframes 5m 15m 1h \
    --days 90 \
    --datadir user_data/ml_env/data

# Run backtesting with FreqAI
echo "🧠 Running backtest with ML training..."
freqtrade backtesting \
    --config user_data/ml_env/config_ml.json \
    --strategy ScalpingLearner \
    --timerange=20220101- \
    --freqaimodel CatboostClassifier \
    --datadir user_data/ml_env/data \
    --user-data-dir user_data/ml_env

echo ""
echo "✅ ML Training complete!"
echo "Check user_data/ml_env/models/ for trained models"
echo "Check backtest results for win rate"
