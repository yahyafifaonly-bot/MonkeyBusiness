#!/bin/bash
# Train XGBoost model using Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     XGBoost Model Training (Docker)                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}[INFO]${NC} Building Docker image..."
cd "$SCRIPT_DIR"
docker-compose build

echo ""
echo -e "${BLUE}[INFO]${NC} Starting training in Docker container..."
echo -e "${YELLOW}[NOTE]${NC} This will take 10-30 minutes depending on your system."
echo ""

# Run training
docker-compose run --rm xgb-trading-bot \
    python3 /app/user_data/xgb_5m/train_xgb_5m.py

echo ""
echo -e "${GREEN}[SUCCESS]${NC} Training completed!"
echo -e "${BLUE}[INFO]${NC} Model saved to: $SCRIPT_DIR/models/xgb_5m.pkl"
echo ""
