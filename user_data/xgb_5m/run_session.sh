#!/bin/bash
# XGBoost 5-Minute Scalping Trading Session Manager
# This script manages a complete 3-hour trading session

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config_xgb_5m.json"
STRATEGY_NAME="XGBScalp5m"
MODEL_FILE="$SCRIPT_DIR/models/xgb_5m.pkl"
SESSION_DURATION_HOURS=3
API_PORT=8083

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       XGBoost 5-Minute High-Frequency Trading Bot        ║${NC}"
echo -e "${GREEN}║              3-Hour Automated Session Manager             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if model exists
if [ ! -f "$MODEL_FILE" ]; then
    print_warning "Trained model not found at: $MODEL_FILE"
    print_info "You need to train the model first!"
    echo ""
    read -p "Do you want to train the model now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Starting model training..."
        python3 "$SCRIPT_DIR/train_xgb_5m.py"
        print_success "Model training completed!"
    else
        print_error "Cannot run trading session without a trained model. Exiting."
        exit 1
    fi
fi

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Config file not found at: $CONFIG_FILE"
    exit 1
fi

print_success "Model found: $MODEL_FILE"
print_success "Config found: $CONFIG_FILE"
echo ""

# Display model info
if [ -f "$SCRIPT_DIR/models/model_metadata.json" ]; then
    print_info "Model Information:"
    python3 -c "
import json
with open('$SCRIPT_DIR/models/model_metadata.json', 'r') as f:
    metadata = json.load(f)
    print(f\"  - Trained: {metadata.get('timestamp', 'Unknown')}\")
    print(f\"  - Accuracy: {metadata.get('accuracy', 'N/A'):.2%}\")
    print(f\"  - Precision: {metadata.get('precision', 'N/A'):.2%}\")
    print(f\"  - Recall: {metadata.get('recall', 'N/A'):.2%}\")
    print(f\"  - Total Samples: {metadata.get('total_samples', 'N/A')}\")
" 2>/dev/null || print_warning "Could not read model metadata"
    echo ""
fi

# Session info
print_info "Session Configuration:"
echo "  - Duration: $SESSION_DURATION_HOURS hours"
echo "  - Timeframe: 5 minutes"
echo "  - Strategy: $STRATEGY_NAME"
echo "  - API Port: $API_PORT"
echo "  - Trading Pairs: BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT"
echo "  - Dynamic Stake Sizing:"
echo "    • 0.62-0.70 probability → \$10"
echo "    • 0.70-0.78 probability → \$20"
echo "    • 0.78+ probability → \$50"
echo ""

# Confirm start
read -p "Start trading session? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Session cancelled by user."
    exit 0
fi

echo ""
print_info "Starting trading session..."
print_info "Session will run for $SESSION_DURATION_HOURS hours and then automatically stop."
echo ""

# Create session directory
SESSION_ID=$(date +%Y%m%d_%H%M%S)
SESSION_DIR="$SCRIPT_DIR/sessions/session_$SESSION_ID"
mkdir -p "$SESSION_DIR"

print_info "Session ID: $SESSION_ID"
print_info "Session logs will be saved to: $SESSION_DIR"
echo ""

# Start Freqtrade
print_info "Launching Freqtrade..."
freqtrade trade \
    --config "$CONFIG_FILE" \
    --strategy "$STRATEGY_NAME" \
    --datadir "$SCRIPT_DIR/data" \
    --user-data-dir "$SCRIPT_DIR/.." \
    --logfile "$SESSION_DIR/freqtrade.log" \
    2>&1 | tee "$SESSION_DIR/console.log" &

FREQTRADE_PID=$!
echo $FREQTRADE_PID > "$SESSION_DIR/freqtrade.pid"

print_success "Freqtrade started (PID: $FREQTRADE_PID)"
print_info "Monitoring session..."
echo ""

# Monitor session
START_TIME=$(date +%s)
END_TIME=$((START_TIME + SESSION_DURATION_HOURS * 3600))

# Display countdown
while true; do
    CURRENT_TIME=$(date +%s)
    REMAINING_SECONDS=$((END_TIME - CURRENT_TIME))

    if [ $REMAINING_SECONDS -le 0 ]; then
        break
    fi

    HOURS=$((REMAINING_SECONDS / 3600))
    MINUTES=$(((REMAINING_SECONDS % 3600) / 60))
    SECONDS=$((REMAINING_SECONDS % 60))

    # Check if process is still running
    if ! kill -0 $FREQTRADE_PID 2>/dev/null; then
        print_warning "Freqtrade process stopped unexpectedly!"
        break
    fi

    printf "\r${YELLOW}[SESSION]${NC} Time remaining: %02d:%02d:%02d | API: http://localhost:$API_PORT | PID: $FREQTRADE_PID" $HOURS $MINUTES $SECONDS
    sleep 10
done

echo ""
echo ""

# Stop Freqtrade
print_info "Session duration completed. Stopping Freqtrade..."

if kill -0 $FREQTRADE_PID 2>/dev/null; then
    kill -SIGTERM $FREQTRADE_PID 2>/dev/null || true

    # Wait for graceful shutdown
    for i in {1..30}; do
        if ! kill -0 $FREQTRADE_PID 2>/dev/null; then
            break
        fi
        sleep 1
    done

    # Force kill if still running
    if kill -0 $FREQTRADE_PID 2>/dev/null; then
        print_warning "Forcing shutdown..."
        kill -9 $FREQTRADE_PID 2>/dev/null || true
    fi
fi

print_success "Freqtrade stopped."
echo ""

# Display session report
print_info "Generating session report..."
REPORT_FILE="$SESSION_DIR/session_report.txt"

{
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║          XGBoost 5m Trading Session Report               ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Session ID: $SESSION_ID"
    echo "Started: $(date -r $START_TIME '+%Y-%m-%d %H:%M:%S')"
    echo "Ended: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Duration: $SESSION_DURATION_HOURS hours"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo ""
} > "$REPORT_FILE"

# Extract performance from logs if available
if [ -f "$SESSION_DIR/freqtrade.log" ]; then
    # Try to find performance summary in logs
    grep -i "performance\|trades\|profit\|win rate" "$SESSION_DIR/freqtrade.log" >> "$REPORT_FILE" 2>/dev/null || echo "No performance data found in logs" >> "$REPORT_FILE"
fi

# Try to get stats from trade log
if [ -f "$SCRIPT_DIR/sessions/trades.jsonl" ]; then
    print_info "Analyzing trades..."
    python3 - << EOF >> "$REPORT_FILE" 2>/dev/null || echo "Could not analyze trades"
import json
from datetime import datetime, timedelta

session_start = datetime.fromtimestamp($START_TIME)
session_trades = []

try:
    with open('$SCRIPT_DIR/sessions/trades.jsonl', 'r') as f:
        for line in f:
            if line.strip():
                trade = json.loads(line)
                trade_time = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
                if trade_time >= session_start:
                    session_trades.append(trade)

    if session_trades:
        total_trades = len(session_trades)
        winning_trades = [t for t in session_trades if t['profit_pct'] > 0]
        losing_trades = [t for t in session_trades if t['profit_pct'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        total_profit = sum(t['profit_pct'] for t in session_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0

        print("\n📊 TRADE STATISTICS")
        print(f"Total Trades: {total_trades}")
        print(f"Winning Trades: {len(winning_trades)}")
        print(f"Losing Trades: {len(losing_trades)}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Total P&L: {total_profit:.3f}%")
        print(f"Average P&L per Trade: {avg_profit:.3f}%")

        if winning_trades:
            avg_win = sum(t['profit_pct'] for t in winning_trades) / len(winning_trades)
            print(f"Average Win: {avg_win:.3f}%")

        if losing_trades:
            avg_loss = sum(t['profit_pct'] for t in losing_trades) / len(losing_trades)
            print(f"Average Loss: {avg_loss:.3f}%")

        # Pair breakdown
        print("\n📈 BY TRADING PAIR")
        pair_stats = {}
        for trade in session_trades:
            pair = trade['pair']
            if pair not in pair_stats:
                pair_stats[pair] = {'count': 0, 'profit': 0}
            pair_stats[pair]['count'] += 1
            pair_stats[pair]['profit'] += trade['profit_pct']

        for pair, stats in sorted(pair_stats.items(), key=lambda x: x[1]['profit'], reverse=True):
            print(f"  {pair}: {stats['count']} trades, {stats['profit']:.3f}% P&L")
    else:
        print("\nNo trades found for this session.")

except Exception as e:
    print(f"\nError analyzing trades: {e}")
EOF
fi

# Display report
cat "$REPORT_FILE"
echo ""

print_success "Session report saved to: $REPORT_FILE"
echo ""

# Ask about incremental learning
print_info "Session completed!"
echo ""
read -p "Do you want to perform incremental learning with session data? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Starting incremental learning..."
    python3 "$SCRIPT_DIR/incremental_train.py" --session-id "$SESSION_ID"
    print_success "Incremental learning completed!"
else
    print_info "Skipping incremental learning. You can run it later with:"
    echo "  python3 $SCRIPT_DIR/incremental_train.py --session-id $SESSION_ID"
fi

echo ""
print_success "All done! Session $SESSION_ID completed successfully."
print_info "To start a new session, run this script again."
echo ""
