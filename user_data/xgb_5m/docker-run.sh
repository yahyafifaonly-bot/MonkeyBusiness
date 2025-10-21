#!/bin/bash
# Start XGBoost Trading Bot using Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       XGBoost 5-Minute Trading Bot (Docker)              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if model exists
if [ ! -f "$SCRIPT_DIR/models/xgb_5m.pkl" ]; then
    echo -e "${RED}[ERROR]${NC} Trained model not found!"
    echo -e "${YELLOW}[INFO]${NC} You need to train the model first."
    echo ""
    read -p "Do you want to train the model now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$SCRIPT_DIR/docker-train.sh"
    else
        echo -e "${RED}[ERROR]${NC} Cannot run without a trained model. Exiting."
        exit 1
    fi
fi

echo -e "${BLUE}[INFO]${NC} Model found: models/xgb_5m.pkl"
echo ""

# Display model info
if [ -f "$SCRIPT_DIR/models/xgb_5m_metadata.json" ]; then
    echo -e "${BLUE}[INFO]${NC} Model Information:"
    python3 -c "
import json
try:
    with open('$SCRIPT_DIR/models/xgb_5m_metadata.json', 'r') as f:
        metadata = json.load(f)
        print(f\"  - Trained: {metadata.get('timestamp', 'Unknown')}\")
        print(f\"  - Accuracy: {metadata.get('accuracy', 'N/A'):.2%}\")
        print(f\"  - Precision: {metadata.get('precision', 'N/A'):.2%}\")
        print(f\"  - Recall: {metadata.get('recall', 'N/A'):.2%}\")
except:
    pass
" 2>/dev/null || echo "  - Could not read metadata"
    echo ""
fi

echo -e "${BLUE}[INFO]${NC} Trading Configuration:"
echo "  - Timeframe: 5 minutes"
echo "  - Pairs: BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT"
echo "  - API: http://localhost:8083"
echo "  - Mode: Dry-run (Paper Trading)"
echo ""

echo -e "${YELLOW}[NOTE]${NC} The bot will run continuously. Press Ctrl+C to stop."
echo ""

read -p "Start trading bot? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}[INFO]${NC} Cancelled by user."
    exit 0
fi

echo ""
echo -e "${BLUE}[INFO]${NC} Building Docker image..."
cd "$SCRIPT_DIR"
docker-compose build

echo ""
echo -e "${GREEN}[SUCCESS]${NC} Starting trading bot..."
echo -e "${BLUE}[INFO]${NC} Access API dashboard at: ${GREEN}http://localhost:8083${NC}"
echo -e "${BLUE}[INFO]${NC} Username: xgbtrader | Password: xgbtrader"
echo -e "${BLUE}[INFO]${NC} Press Ctrl+C to stop the bot"
echo ""

# Start the bot
docker-compose up

# Cleanup message
echo ""
echo -e "${BLUE}[INFO]${NC} Trading bot stopped."
echo ""
