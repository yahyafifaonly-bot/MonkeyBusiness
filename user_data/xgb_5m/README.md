# XGBoost 5-Minute High-Frequency Crypto Trading System

A machine learning-powered cryptocurrency trading bot using XGBoost and Freqtrade for high-frequency scalping on 5-minute candles.

## Overview

This trading system combines the power of XGBoost (Extreme Gradient Boosting) machine learning with Freqtrade's robust trading framework to create an automated scalping strategy that:

- Trades on **5-minute candles** for high-frequency opportunities
- Uses **dynamic stake sizing** based on ML confidence levels
- Runs **3-hour trading sessions** with automatic shutdown and reporting
- Learns from **2+ years of historical data**
- Continuously improves through **incremental learning** from live trades

## Features

### Machine Learning
- **XGBoost Binary Classification**: Predicts profitable trade setups with high accuracy
- **40+ Technical Features**: RSI, MACD, EMA slopes, Bollinger Bands, ATR, volume indicators, time features
- **Walk-Forward Validation**: Ensures model generalization on time-series data
- **Incremental Learning**: Model continuously improves from real trading results

### Dynamic Position Sizing
Automatically adjusts stake size based on ML confidence:
- **0.62-0.70 probability** → $10 stake
- **0.70-0.78 probability** → $20 stake
- **0.78+ probability** → $50 stake

### Risk Management
- **Stop Loss**: -0.6% hard stop
- **Take Profit**: +0.4% target
- **Trailing Stop**: Activates after +0.25% profit
- **Consecutive Loss Protection**: Stops after 10 consecutive losses
- **Max Drawdown Protection**: 15% maximum allowed drawdown

### Session Management
- **3-hour trading sessions** with automatic shutdown
- **Real-time performance tracking** (trades, win rate, P&L)
- **Comprehensive session reports** saved to disk
- **Trade logging** for incremental learning

## Directory Structure

```
user_data/xgb_5m/
├── strategies/
│   └── XGBScalp5m.py          # Freqtrade strategy
├── models/
│   ├── xgb_5m.pkl             # Trained XGBoost model
│   └── xgb_5m_metadata.json   # Model performance metrics
├── data/
│   └── binance/               # Historical OHLCV data
├── sessions/
│   ├── trades.jsonl           # All trade logs
│   └── session_*/             # Individual session reports
├── logs/
│   └── *.log                  # Training and system logs
├── train_xgb_5m.py            # Initial model training script
├── incremental_train.py       # Incremental learning script
├── run_session.sh             # Session manager (run this!)
├── config_xgb_5m.json         # Freqtrade configuration
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.8+
- Freqtrade installed and configured
- 1-2 GB free disk space for historical data

### Install Dependencies

```bash
# Install XGBoost and machine learning libraries
pip install xgboost scikit-learn pandas numpy ta-lib ccxt

# If TA-Lib installation fails, install system dependencies first:
# macOS:
brew install ta-lib

# Ubuntu/Debian:
sudo apt-get install ta-lib

# Then install Python wrapper:
pip install TA-Lib
```

## Quick Start

### 1. Train Initial Model

First, train the XGBoost model on 2 years of historical data:

```bash
cd user_data/xgb_5m
python3 train_xgb_5m.py
```

This will:
- Download 2 years of 5-minute OHLCV data for BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT
- Calculate 40+ technical indicators
- Train XGBoost classifier
- Save model to `models/xgb_5m.pkl`
- Generate performance metrics

**Expected Training Time**: 10-30 minutes depending on your system

### 2. Run Trading Session

Launch a 3-hour automated trading session:

```bash
chmod +x run_session.sh
./run_session.sh
```

The session manager will:
1. Check if model exists (offer to train if not)
2. Display model performance metrics
3. Start Freqtrade with XGBoost strategy
4. Run for 3 hours with live countdown
5. Auto-stop and generate comprehensive report
6. Offer to perform incremental learning

### 3. Monitor Trading

While session is running:

- **API Dashboard**: http://localhost:8083
  - Username: `xgbtrader`
  - Password: `xgbtrader`

- **Console Output**: Real-time trade notifications and session countdown

- **Log Files**: `sessions/session_YYYYMMDD_HHMMSS/freqtrade.log`

### 4. Incremental Learning (Optional)

After session completes, improve model with new data:

```bash
# Learn from specific session
python3 incremental_train.py --session-id 20241021_143000

# Learn from all sessions
python3 incremental_train.py --all-sessions

# Learn from last 7 days
python3 incremental_train.py --last-n-days 7
```

## Configuration

### Trading Parameters

Edit `config_xgb_5m.json` to customize:

```json
{
  "max_open_trades": 8,           // Max simultaneous trades
  "stake_currency": "USDT",
  "dry_run": true,                // Set to false for live trading
  "dry_run_wallet": 1000,         // Paper trading balance

  "exchange": {
    "name": "binance",
    "pair_whitelist": [           // Trading pairs
      "BTC/USDT",
      "ETH/USDT",
      "SOL/USDT",
      "BNB/USDT"
    ]
  }
}
```

### Strategy Parameters

Edit `strategies/XGBScalp5m.py` to adjust:

```python
# Risk/Reward
minimal_roi = {"0": 0.004}      # 0.4% take profit
stoploss = -0.006                # -0.6% stop loss
trailing_stop = True
trailing_stop_positive = 0.0025  # Start trailing at +0.25%

# ML Confidence Thresholds
min_probability = 0.62           # Minimum to enter trade
prob_mid_threshold = 0.70        # Mid confidence level
prob_high_threshold = 0.78       # High confidence level

# Stake Sizes
stake_low = 10                   # Low confidence stake
stake_mid = 20                   # Mid confidence stake
stake_high = 50                  # High confidence stake

# Session Settings
session_duration_hours = 3       # Auto-stop after 3 hours
max_consecutive_losses = 10      # Stop after 10 losses
```

## How It Works

### 1. Training Phase

**Feature Engineering** (`train_xgb_5m.py`):
- Downloads 2 years of 5-minute candles
- Calculates technical indicators:
  - **Momentum**: RSI (7, 14, 21 periods), MACD, EMA slopes
  - **Volatility**: Bollinger Bands, ATR
  - **Volume**: Z-scores, moving averages, ratios
  - **Price Action**: Returns, ranges
  - **Time**: Hour/day cyclical encoding

**Labeling**:
- Label = 1 if price rises ≥ 0.3% within next 5 candles (25 minutes)
- Label = 0 otherwise

**Training**:
- Walk-forward validation (80/20 split)
- XGBoost with 500 trees, depth 7
- Optimized for precision/recall balance

### 2. Trading Phase

**Signal Generation** (`strategies/XGBScalp5m.py`):
1. Calculate same indicators on each 5-minute candle
2. Pass features to XGBoost model
3. Get probability of profitable trade
4. Enter if probability ≥ 0.62

**Position Sizing**:
- Higher ML confidence = larger position
- Maximizes profit on best setups
- Limits exposure on marginal setups

**Exit Logic**:
- ROI: +0.4% take profit
- Stop Loss: -0.6% hard stop
- Trailing: Lock profits after +0.25%
- Time: Exit after 30 minutes max hold

**Session Management**:
- Tracks all trades, win rate, P&L
- Stops after 3 hours or 10 consecutive losses
- Generates detailed performance report

### 3. Learning Phase

**Incremental Training** (`incremental_train.py`):
1. Load completed trades from `sessions/trades.jsonl`
2. Fetch market data context around each trade
3. Recalculate features for those periods
4. Continue XGBoost training with new data
5. Save updated model

This creates a **feedback loop** where the model continuously improves from real-world results.

## Performance Expectations

Based on backtesting and design goals:

| Metric | Target |
|--------|--------|
| Win Rate | 60%+ |
| Risk/Reward | 2:1 (0.4% TP / 0.6% SL) |
| Trades per Session | 15-30 (on 4 pairs) |
| Avg Trade Duration | 10-20 minutes |
| Daily P&L Target | +0.5% to +2% |

**Note**: These are targets, not guarantees. Actual performance varies with market conditions.

## Monitoring & Troubleshooting

### Check Model Performance

```bash
# View model metadata
cat models/xgb_5m_metadata.json

# Check training logs
tail -f logs/training.log
```

### Check Session Logs

```bash
# View latest session
ls -lt sessions/

# Check specific session
cat sessions/session_YYYYMMDD_HHMMSS/session_report.txt

# Monitor live session
tail -f sessions/session_YYYYMMDD_HHMMSS/freqtrade.log
```

### Common Issues

**"Model not found"**
- Run `python3 train_xgb_5m.py` to train initial model

**"No data available"**
- Check internet connection
- Verify Binance API is accessible
- Try downloading data manually with freqtrade download-data

**"No trades being placed"**
- Check ML confidence: model may not be finding high-probability setups
- Lower `min_probability` threshold in strategy (carefully!)
- Review logs for entry condition failures

**"Too many losing trades"**
- Markets may be choppy/unfavorable
- Let protective stops kick in (10 consecutive losses)
- Consider retraining model or adjusting thresholds

## Safety & Risk Warnings

### Paper Trading First
**ALWAYS start with dry_run: true** to test system before risking real capital.

### Position Sizing
- Default stakes ($10-$50) assume $1000+ account
- Adjust `stake_low/mid/high` proportionally to your capital
- Never risk more than 1-2% per trade

### Market Risk
- High-frequency scalping is sensitive to market conditions
- Works best in trending or moderately volatile markets
- May struggle in extremely choppy or low-volume conditions

### Model Risk
- ML models can overfit or become outdated
- Monitor performance and retrain regularly
- Don't blindly trust predictions - use protective stops

### Exchange Risk
- This is configured for Binance spot trading
- Ensure you understand exchange fees and requirements
- Keep API keys secure, use IP restrictions

## Advanced Usage

### Backtesting

Test strategy on historical data before live trading:

```bash
freqtrade backtesting \
  --config config_xgb_5m.json \
  --strategy XGBScalp5m \
  --timerange 20230101-20231231 \
  --datadir data
```

### Hyperparameter Optimization

Optimize strategy parameters:

```bash
freqtrade hyperopt \
  --config config_xgb_5m.json \
  --strategy XGBScalp5m \
  --hyperopt-loss SharpeHyperOptLoss \
  --spaces buy sell roi stoploss \
  -e 500
```

### Custom Pairs

Add more trading pairs in `config_xgb_5m.json`:

```json
"pair_whitelist": [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "BNB/USDT",
  "AVAX/USDT",  // Add new pairs
  "MATIC/USDT"
]
```

Then retrain model with new pairs:
```bash
python3 train_xgb_5m.py  # Will download data for new pairs
```

### Live Trading (Real Money)

When ready for live trading:

1. **Backtest thoroughly** on at least 6 months of data
2. **Paper trade** for at least 1 week successfully
3. **Start small** with minimum stake amounts
4. Update config:

```json
{
  "dry_run": false,
  "exchange": {
    "key": "your_binance_api_key",
    "secret": "your_binance_api_secret"
  }
}
```

5. Run session: `./run_session.sh`

## Maintenance

### Daily Routine
1. Review previous session reports
2. Run incremental learning: `python3 incremental_train.py --last-n-days 1`
3. Start new session: `./run_session.sh`

### Weekly Routine
1. Analyze overall performance trends
2. Check for model degradation (declining accuracy)
3. Retrain if win rate drops below 50%: `python3 train_xgb_5m.py`

### Monthly Routine
1. Full model retraining with latest data
2. Backtest on recent periods
3. Review and adjust risk parameters if needed

## Logging & Data

### Trade Log Format

`sessions/trades.jsonl` contains:
```json
{
  "timestamp": "2024-10-21T14:35:00+00:00",
  "pair": "BTC/USDT",
  "entry_price": 67500.00,
  "exit_price": 67770.00,
  "profit_pct": 0.4,
  "duration_minutes": 15,
  "ml_probability": 0.73,
  "exit_reason": "roi"
}
```

### Session Report Example

```
╔═══════════════════════════════════════════════════════════╗
║          XGBoost 5m Trading Session Report               ║
╚═══════════════════════════════════════════════════════════╝

Session ID: 20241021_143000
Started: 2024-10-21 14:30:00
Ended: 2024-10-21 17:30:00
Duration: 3 hours

═══════════════════════════════════════════════════════════

📊 TRADE STATISTICS
Total Trades: 24
Winning Trades: 16
Losing Trades: 8
Win Rate: 66.67%
Total P&L: 3.2%
Average P&L per Trade: 0.13%

📈 BY TRADING PAIR
BTC/USDT: 8 trades, 1.2% P&L
ETH/USDT: 7 trades, 1.5% P&L
SOL/USDT: 5 trades, 0.8% P&L
BNB/USDT: 4 trades, -0.3% P&L
```

## Support & Resources

### Freqtrade Documentation
- Website: https://www.freqtrade.io/
- Strategies: https://www.freqtrade.io/en/stable/strategy-customization/
- Configuration: https://www.freqtrade.io/en/stable/configuration/

### XGBoost Documentation
- GitHub: https://github.com/dmlc/xgboost
- Docs: https://xgboost.readthedocs.io/

### Community
- Freqtrade Discord: https://discord.gg/freqtrade
- GitHub Issues: File bugs/questions in your repo

## License & Disclaimer

**FOR EDUCATIONAL PURPOSES ONLY**

This trading system is provided as-is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. The authors and contributors are not responsible for any financial losses incurred while using this software.

**ALWAYS:**
- Test extensively in paper trading mode
- Never invest more than you can afford to lose
- Understand the code before running it
- Keep backups of your models and data
- Monitor your trades actively

## Contributing

Improvements welcome! Areas for contribution:
- Additional technical indicators
- Alternative ML models (LightGBM, CatBoost)
- Better incremental learning strategies
- Performance dashboards
- Automated hyperparameter tuning

## Version History

**v1.0.0** - Initial Release
- XGBoost binary classifier
- Dynamic stake sizing
- 3-hour session management
- Incremental learning support
- Comprehensive reporting

---

**Good luck and trade responsibly!**
