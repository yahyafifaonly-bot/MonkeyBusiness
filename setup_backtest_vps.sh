#!/bin/bash

# One-time setup for backtest environment on VPS

VPS_USER="root"
VPS_HOST="72.61.162.23"

echo "=========================================="
echo "Setting up Backtest Environment on VPS"
echo "=========================================="
echo ""

ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
# Create backtest directory structure
mkdir -p ~/freqtrade_backtest/user_data/strategies
chmod -R 755 ~/freqtrade_backtest

echo "✅ Backtest directory created: ~/freqtrade_backtest"
echo "✅ Permissions set"

# Check it exists
ls -la ~/freqtrade_backtest/

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Backtest environment is ready."
echo "Future deployments will automatically run backtests."
ENDSSH

echo ""
echo "Done! You can now trigger deployments and backtests will work."
