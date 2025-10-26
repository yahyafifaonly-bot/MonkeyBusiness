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
import re
from datetime import datetime
from pathlib import Path

# Configuration
CONFIG = "config_backtest.json"
STRATEGY = "EMAPlaybookStrategy"
RESULTS_DIR = "playbook_results"
USER_DATA = "user_data"

VARIANTS = [f"v{i}" for i in range(1, 11)]

os.makedirs(RESULTS_DIR, exist_ok=True)


def is_docker_available():
    """Check if Docker is available"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def is_freqtrade_command_available():
    """Check if freqtrade command is available"""
    try:
        result = subprocess.run(["freqtrade", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def run_variant(variant: str):
    """Run backtest for a single variant"""
    print(f"\n{'='*60}")
    print(f"Running backtest for {variant}")
    print(f"{'='*60}")

    # Freqtrade exports to user_data/backtest_results/
    export_dir = os.path.join(USER_DATA, "backtest_results")

    # Determine if we should use Docker or direct command
    use_docker = False
    if not is_freqtrade_command_available():
        if is_docker_available():
            use_docker = True
            print("Using Docker to run freqtrade...")
        else:
            print("ERROR: Neither freqtrade command nor Docker is available!")
            return False

    if use_docker:
        # Docker command (like in GitHub Actions workflow)
        pwd = os.getcwd()
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{pwd}/user_data:/freqtrade/user_data",
            "-v", f"{pwd}/{CONFIG}:/freqtrade/{CONFIG}",
            "freqtradeorg/freqtrade:stable",
            "backtesting",
            "--config", f"/freqtrade/{CONFIG}",
            "--strategy", STRATEGY,
            "--strategy-params", json.dumps({"variant": variant}),
            "--export", "trades",
        ]
    else:
        # Direct freqtrade command
        cmd = [
            "freqtrade", "backtesting",
            "--config", CONFIG,
            "--strategy", STRATEGY,
            "--strategy-params", json.dumps({"variant": variant}),
            "--export", "trades",
        ]

    print("Command:", " ".join(cmd))
    print()

    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        # Always print output for debugging
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check if backtest succeeded by looking for results
        if result.returncode == 0 or "BACKTESTING REPORT" in result.stdout:
            # Move the exported file to our results dir
            # Freqtrade names it like: backtest-result-YYYY-MM-DD_HH-MM-SS.json
            if os.path.exists(export_dir):
                # Find the most recent export file
                files = sorted(Path(export_dir).glob("*.json"), key=os.path.getmtime, reverse=True)
                if files:
                    latest = files[0]
                    dest = os.path.join(RESULTS_DIR, f"trades_{variant}.json")
                    # Copy instead of move to preserve original
                    import shutil
                    shutil.copy(str(latest), dest)
                    print(f"✓ Saved results to {dest}")

            # Extract summary from stdout
            summary = extract_summary_from_output(result.stdout, variant)
            if summary:
                summary_file = os.path.join(RESULTS_DIR, f"summary_{variant}.txt")
                with open(summary_file, "w") as f:
                    f.write(summary)

            return True
        else:
            print(f"✗ Backtest failed for {variant}")
            return False

    except Exception as e:
        print(f"ERROR running {variant}: {e}")
        return False


def extract_summary_from_output(output: str, variant: str) -> str:
    """Extract the summary table from freqtrade output"""
    lines = output.split('\n')
    summary_lines = []
    in_summary = False

    for line in lines:
        if 'BACKTESTING REPORT' in line or 'STRATEGY SUMMARY' in line:
            in_summary = True
        if in_summary:
            summary_lines.append(line)
            if '========================' in line and len(summary_lines) > 5:
                break

    return '\n'.join(summary_lines) if summary_lines else ""


def parse_metrics(variant: str):
    """Parse backtest results from trades export"""
    trades_file = os.path.join(RESULTS_DIR, f"trades_{variant}.json")

    if not os.path.exists(trades_file):
        print(f"Warning: {trades_file} not found")
        return None

    try:
        with open(trades_file, "r") as f:
            data = json.load(f)

        # Handle different export formats
        if isinstance(data, list):
            trades = data
        elif isinstance(data, dict):
            # Newer format has metadata
            trades = data.get("trades", [])
        else:
            print(f"Unknown format in {trades_file}")
            return None

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
        # Handle different profit field names
        profit_pct = t.get("profit_ratio", t.get("profit_percent", 0.0))
        if isinstance(profit_pct, str):
            profit_pct = float(profit_pct.replace("%", ""))
        else:
            profit_pct = profit_pct * 100  # Convert ratio to percentage

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

    # Check if freqtrade or Docker is available
    if is_freqtrade_command_available():
        try:
            result = subprocess.run(["freqtrade", "--version"], capture_output=True, text=True)
            print(f"Using freqtrade command")
            print(f"Freqtrade version: {result.stdout.strip()}\n")
        except Exception:
            pass
    elif is_docker_available():
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            print(f"Using Docker to run freqtrade")
            print(f"Docker version: {result.stdout.strip()}\n")
        except Exception:
            pass
    else:
        print(f"ERROR: Neither freqtrade command nor Docker is available!")
        print("Please install freqtrade or Docker to run backtests")
        sys.exit(1)

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
    csv_file = os.path.join(RESULTS_DIR, "playbook_summary.csv")
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'='*60}")
    print(f"Summary saved to: {csv_file}")
    print(f"{'='*60}\n")

    # Print top 3 variants
    print("TOP 3 VARIANTS BY EXPECTANCY:")
    print(f"{'-'*60}")
    for i, row in enumerate(rows[:3], 1):
        print(f"{i}. {row['Variant']}: {row['Expectancy%']}% expectancy, "
              f"{row['WinRate%']}% win rate, {row['Trades']} trades, "
              f"{row['TotalProfit%']}% total profit")

    print(f"\n{'='*60}")
    print("Backtest complete!")
    print(f"View detailed results in: {RESULTS_DIR}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
