# ML Trading Bot - Quick Start Guide

## Overview
This is a self-learning ML trading bot built with FreqTrade and FreqAI. The bot automatically learns from historical data, tests strategies, and adapts to market conditions.

**Goal**: Achieve 60%+ win rate with 2:1 Risk/Reward ratio using high-frequency scalping (50-100 trades/day)

---

## 3 Environment Architecture

### 1. ML Environment (Learning)
- **Purpose**: Train and optimize ML models
- **Mode**: Dry-run (safe)
- **Port**: 8080
- **Config**: `user_data/ml_env/config_ml.json`
- **Retraining**: Every 1 hour
- **Data**: 90 days historical + live updates

### 2. Test Environment (Paper Trading)
- **Purpose**: Validate strategies with fake money
- **Mode**: Dry-run (safe)
- **Port**: 8081
- **Config**: `user_data/test_env/config_test.json`
- **Uses**: Pre-trained models from ML env

### 3. Production Environment (Live Trading)
- **Purpose**: Real trading with real money
- **Mode**: Live (DANGEROUS)
- **Port**: 8082
- **Config**: `user_data/production_env/config_production.json`
- **Retraining**: Every 24 hours

---

## Quick Start Commands

### Step 1: Train ML Model (First Time)
```bash
./scripts/start_ml_training.sh
```

**What it does:**
- Downloads latest 90 days of BTC/USDT data (5m, 15m, 1h timeframes)
- Trains Catboost ML model on historical data (2022-2025)
- Runs backtest to verify strategy performance
- Saves trained model to `user_data/ml_env/models/`

**Wait for:** "ML Training complete!" message

**Check results:** Look for win rate and profit metrics in the output

---

### Step 2: Test with Paper Trading
```bash
./scripts/start_test_trading.sh
```

**What it does:**
- Copies trained ML model to test environment
- Downloads latest 7 days of data
- Starts paper trading bot (fake money)
- Opens dashboard at http://localhost:8081

**Monitor:** Watch trades in real-time without risking money

**Stop with:** Ctrl+C

---

### Step 3: Production (REAL MONEY - Use with Caution)
```bash
./scripts/start_production.sh
```

**IMPORTANT SAFETY CHECKS:**
- Only use after successful paper trading results
- Verify win rate ≥60% in backtests
- Set up API keys in `user_data/production_env/config_production.json`
- Start with small stake amounts ($2 default)

**What it does:**
- Requires explicit "yes" confirmation
- Copies trained ML model to production
- Starts LIVE trading bot with real money
- Opens dashboard at http://localhost:8082

---

## Strategy Details: ScalpingLearner

### Risk Management
- **Stop Loss**: 0.5% per trade
- **Take Profit**: 1.0% per trade
- **Risk/Reward**: 2:1 ratio
- **Position Size**: $2 per trade (default)
- **Max Trades**: 5 concurrent (production), 10 (ML/test)

### Session Management
- **Duration**: 3 hours max per session
- **Auto-stop**: After 3 hours for review
- **Reset**: Restart script to begin new session

### Failure Protection
- **10 Consecutive Losses**: Bot automatically stops
- **Failure Report**: Logged to FreqTrade logs
- **Review Required**: Analyze failures before restarting

### Entry Conditions
1. RSI < 40 (oversold)
2. Volume > 1.2x average
3. Price above 10-period EMA
4. 5-period EMA > 10-period EMA
5. Bollinger Band position < 40% (lower band)
6. **ML Confidence**: Model predicts >0.5% upward movement

### Exit Conditions
1. RSI > 70 (overbought)
2. Price below 5-period EMA
3. Bollinger Band position > 80% (upper band)
4. ML prediction turns negative
5. **Time Exit**: Max hold time 30 minutes
6. **Take Profit**: 1% gain
7. **Stop Loss**: 0.5% loss

---

## Monitoring & Dashboards

### ML Environment Dashboard
```
http://localhost:8080
```
- View training progress
- Check backtest results
- Monitor model accuracy

### Test Environment Dashboard
```
http://localhost:8081
```
- Live paper trading
- Performance metrics
- Trade history

### Production Dashboard
```
http://localhost:8082
```
- Real trades
- P&L tracking
- Risk metrics

**Default Credentials:**
- Username: `freqtrader`
- Password: `freqtrader`

---

## File Structure

```
Monkeybusiness/
├── scripts/
│   ├── start_ml_training.sh       # Train ML model
│   ├── start_test_trading.sh      # Paper trading
│   └── start_production.sh        # Live trading
│
├── user_data/
│   ├── ml_env/                    # ML Learning Environment
│   │   ├── config_ml.json
│   │   ├── data/                  # Historical data
│   │   ├── models/                # Trained ML models
│   │   └── strategies/
│   │       └── ScalpingLearner.py
│   │
│   ├── test_env/                  # Paper Trading Environment
│   │   ├── config_test.json
│   │   ├── data/
│   │   ├── models/
│   │   └── strategies/
│   │
│   └── production_env/            # Live Trading Environment
│       ├── config_production.json
│       ├── data/
│       ├── models/
│       └── strategies/
```

---

## Configuration Files

### ML Environment: `user_data/ml_env/config_ml.json`
- `"dry_run": true` - Safe mode
- `"max_open_trades": 10`
- `"freqai.live_retrain_hours": 1` - Retrain hourly

### Test Environment: `user_data/test_env/config_test.json`
- `"dry_run": true` - Safe mode
- `"max_open_trades": 10`
- `"freqai.live_retrain_hours": 0` - No retraining

### Production: `user_data/production_env/config_production.json`
- `"dry_run": false` - LIVE TRADING
- `"max_open_trades": 5` - Reduced for safety
- `"freqai.live_retrain_hours": 24` - Daily retraining

**IMPORTANT:** Update API keys before production:
```json
"exchange": {
    "name": "binance",
    "key": "YOUR_API_KEY_HERE",
    "secret": "YOUR_API_SECRET_HERE"
}
```

---

## Checking Results

### Backtest Results
After ML training, check the output for:
```
Total Profit: XX.XX%
Win Rate: XX.XX%
Total Trades: XXX
Average Profit: XX.XX%
```

**Target**: Win rate ≥60%

### View Detailed Logs
```bash
tail -f user_data/ml_env/logs/freqtrade.log
```

### Check Model Directory
```bash
ls -lh user_data/ml_env/models/
```

---

## Learning Process

### How the Bot Learns

1. **Feature Engineering**: Extracts 50+ technical indicators from price data
   - RSI, MACD, Bollinger Bands, EMAs, Volume, Momentum, etc.

2. **ML Model Training**: Catboost classifier learns patterns
   - Predicts future price movements
   - Adapts to market conditions
   - Improves over time with more data

3. **Backtesting**: Tests strategy on historical data
   - Simulates trades from 2022-2025
   - Calculates win rate, profit, drawdown
   - Validates model accuracy

4. **Continuous Retraining**:
   - **ML Env**: Retrains every 1 hour with latest data
   - **Production**: Retrains every 24 hours
   - Adapts to changing market conditions

---

## Troubleshooting

### No ML Models Found
```bash
# Re-run ML training
./scripts/start_ml_training.sh
```

### Low Win Rate (<60%)
1. Check backtest results
2. Run hyperparameter optimization:
   ```bash
   freqtrade hyperopt \
       --config user_data/ml_env/config_ml.json \
       --strategy ScalpingLearner \
       --hyperopt-loss SharpeHyperOptLoss \
       --epochs 100
   ```

### Bot Stopped Due to 10 Consecutive Losses
1. Check FreqTrade logs: `user_data/ml_env/logs/freqtrade.log`
2. Analyze market conditions during losses
3. Re-train model with latest data
4. Consider adjusting strategy parameters

### Data Download Issues
```bash
# Manually download data
freqtrade download-data \
    --exchange binance \
    --pairs BTC/USDT \
    --timeframes 5m 15m 1h \
    --days 90 \
    --datadir user_data/ml_env/data
```

---

## Safety Warnings

### NEVER Skip Paper Trading
- Always test in Test Environment first
- Verify win rate ≥60% before going live
- Run for at least 1 week in paper trading

### Start Small in Production
- Default stake: $2 per trade
- Max open trades: 5
- Total risk: ~$10 maximum at any time

### Monitor Closely
- Check dashboard daily
- Review trade history
- Watch for unusual behavior

### Use Stop Losses
- Hard-coded 0.5% stop loss per trade
- 10 consecutive loss protection
- 3-hour session limit

---

## Next Steps

1. **Wait for ML training to complete** (currently running)
2. **Check backtest results** - Verify win rate ≥60%
3. **Test in paper trading** - Run for 1-7 days
4. **Analyze performance** - Review trades, P&L, win rate
5. **Optimize if needed** - Run hyperopt to improve parameters
6. **Set up API keys** - Configure Binance API (read + trade permissions only)
7. **Start production** - Only after successful paper trading

---

## Support & Logs

### Log Locations
- ML Environment: `user_data/ml_env/logs/freqtrade.log`
- Test Environment: `user_data/test_env/logs/freqtrade.log`
- Production: `user_data/production_env/logs/freqtrade.log`

### View Live Logs
```bash
# ML Environment
tail -f user_data/ml_env/logs/freqtrade.log

# Test Environment
tail -f user_data/test_env/logs/freqtrade.log

# Production
tail -f user_data/production_env/logs/freqtrade.log
```

### FreqTrade Documentation
- Official Docs: https://www.freqtrade.io/en/stable/
- FreqAI Guide: https://www.freqtrade.io/en/stable/freqai/
- Strategies: https://www.freqtrade.io/en/stable/strategy-customization/

---

## Current Status

- ✅ FreqTrade installed (v2025.10-dev)
- ✅ Historical data downloaded (403,244 5m candles from 2021-2025)
- ✅ 3 environments configured (ML/Test/Production)
- ✅ ScalpingLearner strategy deployed
- ⏳ ML training in progress...

**Next**: Wait for ML training to complete, then test in paper trading environment.
