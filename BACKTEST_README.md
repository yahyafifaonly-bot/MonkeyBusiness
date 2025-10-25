# Strategy1_EMA_RSI Backtesting Guide

Complete backtesting system for testing the relaxed Strategy1_EMA_RSI with 3 years of 1-minute Binance data.

## Quick Start

Run everything with one command:

```bash
./complete_backtest.sh
```

This will:
1. Download 3 years of 1-minute data from Binance
2. Run comprehensive backtest
3. Generate detailed reports with all metrics

## What You'll Get

### Metrics Included:
- **Total number of trades**
- **Win rate & loss ratio**
- **Profit/Loss per trade**
- **Total profit percentage**
- **Max drawdown**
- **Sharpe ratio, Sortino ratio, Calmar ratio**
- **Best and worst trades**
- **Average holding time**
- **Trades per day**
- **Stake amount ($100 USDT per trade)**
- **Best/worst performing pairs**

### Output Files:

All results saved in `backtest_results/strategy1_TIMESTAMP/`:

1. **backtest-result.json** - Raw backtest data with all trade details
2. **backtest_report.txt** - Human-readable performance report
3. **Breakdown reports** - Day/week/month analysis

## Manual Steps

If you want to run each step individually:

### 1. Download Data (only needed once)

```bash
./download_backtest_data.sh
```

Downloads 1-minute candles for:
- BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT
- XRP/USDT, ADA/USDT, DOGE/USDT, MATIC/USDT
- DOT/USDT, AVAX/USDT

### 2. Run Backtest

```bash
./run_backtest.sh
```

Runs backtest on all pairs with Strategy1_EMA_RSI (relaxed version).

### 3. Analyze Results

```bash
python3 analyze_backtest.py backtest_results/strategy1_*/backtest-result.json
```

Generates detailed performance report.

## Trading Pairs

The backtest runs on 10 major USDT pairs:
- BTC/USDT
- ETH/USDT
- SOL/USDT
- BNB/USDT
- XRP/USDT
- ADA/USDT
- DOGE/USDT
- MATIC/USDT
- DOT/USDT
- AVAX/USDT

## Backtest Configuration

Settings in `config_backtest.json`:
- **Timeframe**: 1 minute
- **Stake amount**: $100 USDT per trade
- **Max open trades**: 3
- **Total capital**: $300 USDT maximum
- **Test period**: Last 3 years (1095 days)

## Strategy Being Tested

**Strategy1_EMA_RSI (Relaxed Version)**

Entry Conditions:
- Price > 9 EMA > 20 EMA (uptrend)
- RSI > 40 (relaxed from 50)
- Price within 1% of 9 EMA (relaxed from 0.2%)
- 2 consecutive green candles (relaxed from 3)
- No 3 consecutive red candles below EMA
- EMA trending up

Exit Conditions:
- RSI < 40
- Price crosses below 9 EMA
- ROI targets hit (3%, 2.5%, 2%)
- Stop loss hit (-1.5%)

## Understanding the Report

### Win Rate
- **>60%**: Excellent
- **50-60%**: Good
- **45-50%**: Acceptable
- **<45%**: Needs improvement

### Profit
- Look for consistent profitability
- Compare to buy & hold
- Check max drawdown (should be <30%)

### Trade Frequency
- More trades = more data points
- Too many trades may mean over-trading
- Too few trades may mean too strict filters

## Next Steps After Backtest

1. **Review the report** in `backtest_report.txt`
2. **Check trade details** in `backtest-result.json`
3. **Adjust strategy** if needed (entry/exit conditions)
4. **Run again** to compare results
5. **Forward test** in dry-run mode before going live

## Troubleshooting

### Data download fails
- Check internet connection
- Binance may have rate limits, wait and try again

### Backtest fails
- Make sure data was downloaded first
- Check that Strategy1_EMA_RSI.py exists in user_data/strategies/

### No trades in backtest
- Strategy conditions may be too strict
- Check if data loaded correctly
- Try different pairs or timeframes

## Important Notes

⚠️ **Past performance does not guarantee future results**
⚠️ **Always test in dry-run mode first**
⚠️ **Start with small amounts when going live**
⚠️ **Monitor your bots regularly**

## Files Created

```
Monkeybusiness/
├── config_backtest.json           # Backtest configuration
├── download_backtest_data.sh      # Data download script
├── run_backtest.sh                # Backtest execution
├── analyze_backtest.py            # Results analyzer
├── complete_backtest.sh           # All-in-one script
├── BACKTEST_README.md             # This file
└── backtest_results/              # Results directory
    └── strategy1_TIMESTAMP/
        ├── backtest-result.json   # Raw results
        └── backtest_report.txt    # Readable report
```
