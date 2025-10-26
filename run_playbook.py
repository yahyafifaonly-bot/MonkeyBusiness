#!/usr/bin/env python3
# run_playbook.py
"""
Backtest runner to try all 10 variants of EMAPlaybookStrategy and aggregate metrics.
Save in your Freqtrade project root (same level as user_data/).

Usage:
    python run_playbook.py
"""

import json
import subprocess
import sys
import os
import csv
from datetime import datetime

# Adjust these
CONFIG = "config_backtest.json"
STRATEGY = "EMAPlaybookStrategy"
RESULTS_DIR = "playbook_results"
EXPORT_TRADES = os.path.join(RESULTS_DIR, "trades_{variant}.json")
EXPORT_SUMMARY = os.path.join(RESULTS_DIR, "summary_{variant}.json")
FINAL_CSV = os.path.join(RESULTS_DIR, "playbook_summary.csv")

VARIANTS = [f"v{i}" for i in range(1, 11)]

os.makedirs(RESULTS_DIR, exist_ok=True)


def run_variant(variant: str):
    """Run backtest for a single variant"""
    print(f"\n{'='*60}")
    print(f"Running backtest for {variant}")
    print(f"{'='*60}")

    trades_file = EXPORT_TRADES.format(variant=variant)

    cmd = [
        "freqtrade", "backtesting",
        "--config", CONFIG,
        "--strategy", STRATEGY,
        "--strategy-params", json.dumps({"variant": variant}),
        "--export", "trades",
        "--export-filename", trades_file,
    ]

    print("Command:", " ".join(cmd))
    print()

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR running {variant}:")
        print(e.stdout)
        print(e.stderr)
        return False


def parse_metrics(variant: str):
    """Parse backtest results from trades export"""
    trades_file = EXPORT_TRADES.format(variant=variant)

    if not os.path.exists(trades_file):
        print(f"Warning: {trades_file} not found")
        return None

    try:
        with open(trades_file, "r") as f:
            trades = json.load(f)
    except Exception as e:
        print(f"Error reading {trades_file}: {e}")
        return None

    if not trades:
        return {
            "Variant": variant,
            "Trades": 0,
            "WinRate%": 0,
            "Expectancy%": 0,
            "TotalProfit%": 0,
            "AvgWin%": 0,
            "AvgLoss%": 0,
            "ProfitFactor": 0,
            "MaxDrawdown%": 0,
            "WorstStreak": 0,
        }

    # Calculate metrics
    total_trades = len(trades)
    wins = 0
    losses = 0
    total_profit = 0
    win_profits = []
    loss_profits = []
    losing_streak = 0
    worst_losing_streak = 0
    max_dd = 0
    cumulative = 0
    peak = 0

    for t in trades:
        profit_pct = t.get("profit_ratio", 0.0) * 100  # Convert to percentage
        total_profit += profit_pct

        # Track drawdown
        cumulative += profit_pct
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

        if profit_pct > 0:
            wins += 1
            win_profits.append(profit_pct)
            losing_streak = 0
        else:
            losses += 1
            loss_profits.append(abs(profit_pct))
            losing_streak += 1
            worst_losing_streak = max(worst_losing_streak, losing_streak)

    # Calculate statistics
    winrate = (wins / total_trades * 100.0) if total_trades else 0.0
    avg_win = (sum(win_profits) / wins) if wins else 0.0
    avg_loss = (sum(loss_profits) / losses) if losses else 0.0

    # Expectancy = (WinRate × AvgWin) - (LossRate × AvgLoss)
    lose_rate = (losses / total_trades * 100.0) if total_trades else 0.0
    expectancy = (winrate / 100.0) * avg_win - (lose_rate / 100.0) * avg_loss

    # Profit factor = Total Wins / Total Losses
    total_wins = sum(win_profits)
    total_losses = sum(loss_profits)
    profit_factor = (total_wins / total_losses) if total_losses > 0 else 0.0

    return {
        "Variant": variant,
        "Trades": total_trades,
        "WinRate%": round(winrate, 2),
        "Expectancy%": round(expectancy, 3),
        "TotalProfit%": round(total_profit, 2),
        "AvgWin%": round(avg_win, 3),
        "AvgLoss%": round(avg_loss, 3),
        "ProfitFactor": round(profit_factor, 3),
        "MaxDrawdown%": round(max_dd, 2),
        "WorstStreak": worst_losing_streak,
    }


def main():
    """Run all variants and create summary"""
    print(f"\n{'='*60}")
    print("EMA Playbook Strategy - Multi-Variant Backtest")
    print(f"{'='*60}\n")
    print(f"Testing {len(VARIANTS)} variants: {', '.join(VARIANTS)}")
    print(f"Results will be saved to: {RESULTS_DIR}")
    print()

    # Run all variants
    successful_variants = []
    for v in VARIANTS:
        if run_variant(v):
            successful_variants.append(v)
        print()

    if not successful_variants:
        print("ERROR: No variants ran successfully!")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Aggregating results...")
    print(f"{'='*60}\n")

    # Aggregate metrics
    rows = []
    for v in successful_variants:
        m = parse_metrics(v)
        if m:
            rows.append(m)
            print(f"{v}: {m['Trades']} trades, {m['WinRate%']}% win rate, "
                  f"{m['Expectancy%']}% expectancy, {m['TotalProfit%']}% profit")

    if not rows:
        print("ERROR: Could not parse any results!")
        sys.exit(1)

    # Sort by Expectancy descending
    rows.sort(key=lambda r: r["Expectancy%"], reverse=True)

    # Write CSV
    fieldnames = list(rows[0].keys())
    with open(FINAL_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'='*60}")
    print(f"Summary saved to: {FINAL_CSV}")
    print(f"{'='*60}\n")

    # Print top 3 variants
    print("TOP 3 VARIANTS BY EXPECTANCY:")
    print(f"{'-'*60}")
    for i, row in enumerate(rows[:3], 1):
        print(f"{i}. {row['Variant']}: {row['Expectancy%']}% expectancy, "
              f"{row['WinRate%']}% win rate, {row['Trades']} trades")

    print(f"\n{'='*60}")
    print("Backtest complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
