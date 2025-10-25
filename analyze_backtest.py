#!/usr/bin/env python3
"""
Backtest Results Analyzer
Generates detailed performance reports from FreqTrade backtest results
"""

import json
import sys
from datetime import datetime
from pathlib import Path

def analyze_backtest_results(result_file):
    """Analyze backtest results and generate detailed report"""

    with open(result_file, 'r') as f:
        data = json.load(f)

    # Get strategy results
    strategy_name = list(data['strategy'].keys())[0]
    results = data['strategy'][strategy_name]

    # Extract metrics
    total_trades = results['total_trades']
    wins = results.get('wins', 0)
    losses = results.get('losses', 0)
    draws = results.get('draws', 0)

    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    loss_rate = (losses / total_trades * 100) if total_trades > 0 else 0

    profit_total = results.get('profit_total', 0)
    profit_total_abs = results.get('profit_total_abs', 0)

    starting_balance = results.get('starting_balance', 1000)
    final_balance = results.get('final_balance', starting_balance)

    max_drawdown = results.get('max_drawdown', 0)
    max_drawdown_abs = results.get('max_drawdown_abs', 0)

    avg_profit = results.get('profit_mean', 0)
    median_profit = results.get('profit_median', 0)

    best_pair = results.get('best_pair', {})
    worst_pair = results.get('worst_pair', {})

    # Time metrics
    holding_avg = results.get('holding_avg', '')

    # Generate report
    report = f"""
{'='*80}
STRATEGY BACKTEST RESULTS
{'='*80}

Strategy: {strategy_name}
Timeframe: 1 minute
Test Period: {results.get('backtest_start', 'N/A')} to {results.get('backtest_end', 'N/A')}

{'='*80}
TRADE STATISTICS
{'='*80}

Total Trades:           {total_trades:,}
Winning Trades:         {wins:,} ({win_rate:.2f}%)
Losing Trades:          {losses:,} ({loss_rate:.2f}%)
Drawn Trades:           {draws:,}

Win/Loss Ratio:         {(wins/losses if losses > 0 else wins):.2f}

{'='*80}
PROFIT & LOSS
{'='*80}

Starting Balance:       ${starting_balance:,.2f} USDT
Final Balance:          ${final_balance:,.2f} USDT
Total Profit:           {profit_total:.2f}% (${profit_total_abs:,.2f} USDT)

Average Profit/Trade:   {avg_profit:.2f}%
Median Profit/Trade:    {median_profit:.2f}%

Best Trade:             {results.get('max_profit', 0):.2f}%
Worst Trade:            {results.get('max_loss', 0):.2f}%

{'='*80}
RISK METRICS
{'='*80}

Max Drawdown:           {max_drawdown:.2f}% (${abs(max_drawdown_abs):,.2f} USDT)
Avg. Holding Time:      {holding_avg}

Sharpe Ratio:           {results.get('sharpe', 0):.2f}
Sortino Ratio:          {results.get('sortino', 0):.2f}
Calmar Ratio:           {results.get('calmar', 0):.2f}

{'='*80}
PAIR PERFORMANCE
{'='*80}

Best Performing Pair:   {best_pair.get('key', 'N/A')}
  - Trades: {best_pair.get('trades', 0)}
  - Profit: {best_pair.get('profit_mean_pct', 0):.2f}%
  - Total: {best_pair.get('profit_sum_pct', 0):.2f}%

Worst Performing Pair:  {worst_pair.get('key', 'N/A')}
  - Trades: {worst_pair.get('trades', 0)}
  - Profit: {worst_pair.get('profit_mean_pct', 0):.2f}%
  - Total: {worst_pair.get('profit_sum_pct', 0):.2f}%

{'='*80}
TRADING FREQUENCY
{'='*80}

Trades per Day:         {results.get('trades_per_day', 0):.2f}
Total Trading Days:     {results.get('backtest_days', 0)}

{'='*80}
STAKE AMOUNT
{'='*80}

Stake per Trade:        $100 USDT
Max Open Trades:        3
Total Capital Used:     $300 USDT (max)

{'='*80}
RECOMMENDATION
{'='*80}
"""

    # Add recommendation
    if win_rate >= 60 and profit_total > 20:
        report += "\n✅ EXCELLENT: High win rate and strong profit. Strategy looks promising!\n"
    elif win_rate >= 50 and profit_total > 10:
        report += "\n✓ GOOD: Positive win rate and profit. Consider further optimization.\n"
    elif win_rate >= 45 and profit_total > 0:
        report += "\n⚠ ACCEPTABLE: Profitable but could be improved. Monitor carefully.\n"
    else:
        report += "\n❌ NEEDS WORK: Low win rate or negative profit. Strategy needs adjustment.\n"

    report += f"\n{'='*80}\n"

    return report

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_backtest.py <backtest-result.json>")
        sys.exit(1)

    result_file = sys.argv[1]

    if not Path(result_file).exists():
        print(f"Error: File not found: {result_file}")
        sys.exit(1)

    try:
        report = analyze_backtest_results(result_file)
        print(report)

        # Save report to file
        output_file = str(Path(result_file).parent / 'backtest_report.txt')
        with open(output_file, 'w') as f:
            f.write(report)

        print(f"\nReport saved to: {output_file}")

    except Exception as e:
        print(f"Error analyzing results: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
