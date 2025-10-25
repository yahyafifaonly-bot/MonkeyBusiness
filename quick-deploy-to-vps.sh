#!/bin/bash

# Quick deployment script to get FreqTrade bots running on VPS
# This manually copies all necessary files to the VPS

VPS_USER="root"
VPS_HOST="72.61.162.23"

echo "=========================================="
echo "Quick Deploy to VPS"
echo "=========================================="
echo ""

echo "1. Copying docker-compose files to VPS..."
scp docker-compose-testing.yml ${VPS_USER}@${VPS_HOST}:~/freqtrade/
scp docker-compose-production.yml ${VPS_USER}@${VPS_HOST}:~/freqtrade/

echo ""
echo "2. Copying Testing_env configs to VPS..."
scp -r user_data/Testing_env/* ${VPS_USER}@${VPS_HOST}:~/freqtrade/Testing_env/

echo ""
echo "3. Copying Production_env configs to VPS..."
scp -r user_data/Production_env/* ${VPS_USER}@${VPS_HOST}:~/freqtrade/Production_env/

echo ""
echo "4. Starting containers on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/freqtrade

echo "Stopping any existing containers..."
docker compose -f docker-compose-testing.yml down 2>/dev/null || true

echo "Starting all 5 strategy containers..."
docker compose -f docker-compose-testing.yml up -d

echo ""
echo "Waiting for containers to start..."
sleep 5

echo ""
echo "Container status:"
docker ps | grep freqtrade_testing

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Access your bots at:"
echo "  http://72.61.162.23:8081 - Strategy1 (login: strategy1/strategy1)"
echo "  http://72.61.162.23:8082 - Strategy2 (login: strategy2/strategy2)"
echo "  http://72.61.162.23:8083 - Strategy3 (login: strategy3/strategy3)"
echo "  http://72.61.162.23:8084 - Strategy4 (login: strategy4/strategy4)"
echo "  http://72.61.162.23:8085 - Strategy5 (login: strategy5/strategy5)"
ENDSSH

echo ""
echo "Done! Try accessing the bots in your browser now."
