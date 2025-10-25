from flask import Flask, render_template, jsonify
import os
import re
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

LOGS_DIR = "/freqtrade_backtest/backtest_logs"

def parse_backtest_log(log_path):
    """Parse a backtest log file and extract key metrics."""
    try:
        with open(log_path, 'r') as f:
            content = f.read()

        data = {
            'filename': os.path.basename(log_path),
            'timestamp': None,
            'strategy': None,
            'trades': None,
            'avg_profit': None,
            'total_profit_usdt': None,
            'total_profit_pct': None,
            'avg_duration': None,
            'win': None,
            'draw': None,
            'loss': None,
            'win_pct': None,
            'drawdown': None,
            'timerange': None,
            'max_open_trades': None,
        }

        # Extract timestamp and strategy from filename
        # Format: backtest_StrategyName_YYYYMMDD_HHMMSS.log or backtest_YYYYMMDD_HHMMSS.log
        ts_match = re.search(r'backtest_(?:(.+?)_)?(\d{8}_\d{6})\.log', data['filename'])
        if ts_match:
            # Extract strategy name from filename if present
            if ts_match.group(1):
                filename_strategy = ts_match.group(1)
                if not data['strategy']:
                    data['strategy'] = filename_strategy

            # Extract timestamp
            ts_str = ts_match.group(2)
            data['timestamp'] = datetime.strptime(ts_str, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M:%S')

        # Extract timerange and max open trades
        timerange_match = re.search(r'Backtested ([\d\-\s:]+) -> ([\d\-\s:]+)', content)
        if timerange_match:
            data['timerange'] = f"{timerange_match.group(1)} -> {timerange_match.group(2)}"

        max_trades_match = re.search(r'Max open trades\s*:\s*(\d+)', content)
        if max_trades_match:
            data['max_open_trades'] = max_trades_match.group(1)

        # Parse STRATEGY SUMMARY table
        # Example: │ Strategy1_EMA_RSI │   2927 │        -0.21 │        -605.840 │       -60.58 │      0:08:00 │  386     0  2541  13.2 │ 605.84 USDT  60.58% │
        summary_pattern = r'│\s*(\S+)\s*│\s*(\d+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([-\d.]+)\s*│\s*([:\d]+)\s*│\s*(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s*│\s*([\d.]+)\s+USDT\s+([\d.]+)%\s*│'
        match = re.search(summary_pattern, content)

        if match:
            data['strategy'] = match.group(1)
            data['trades'] = match.group(2)
            data['avg_profit'] = match.group(3)
            data['total_profit_usdt'] = match.group(4)
            data['total_profit_pct'] = match.group(5)
            data['avg_duration'] = match.group(6)
            data['win'] = match.group(7)
            data['draw'] = match.group(8)
            data['loss'] = match.group(9)
            data['win_pct'] = match.group(10)
            data['drawdown'] = f"{match.group(11)} USDT ({match.group(12)}%)"

        return data
    except Exception as e:
        print(f"Error parsing {log_path}: {e}")
        return None

def get_all_backtests():
    """Get all backtest log files and parse them."""
    if not os.path.exists(LOGS_DIR):
        return []

    backtests = []
    log_files = sorted(Path(LOGS_DIR).glob('backtest_*.log'), reverse=True)

    for log_file in log_files:
        data = parse_backtest_log(str(log_file))
        if data:
            backtests.append(data)

    return backtests

@app.route('/')
def index():
    """Main dashboard page."""
    backtests = get_all_backtests()
    return render_template('index.html', backtests=backtests)

@app.route('/api/backtests')
def api_backtests():
    """API endpoint for backtest data."""
    backtests = get_all_backtests()
    return jsonify(backtests)

@app.route('/api/backtest/<filename>')
def api_backtest_detail(filename):
    """Get full content of a specific backtest log."""
    log_path = os.path.join(LOGS_DIR, filename)
    if not os.path.exists(log_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        with open(log_path, 'r') as f:
            content = f.read()
        return jsonify({'filename': filename, 'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8091, debug=True)
