#!/bin/bash
# Manual VPS Deployment Script for XGBoost Trading Bot
# Run this script locally to deploy to your VPS

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  XGBoost Trading Bot - Manual VPS Deployment         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
DOCKER_IMAGE_NAME="xgb-trading-bot"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found. Please run this from user_data/xgb_5m directory${NC}"
    exit 1
fi

# Prompt for VPS details
echo -e "${YELLOW}Please enter your VPS details:${NC}"
read -p "VPS Host (IP or domain): " VPS_HOST
read -p "VPS User: " VPS_USER
read -p "SSH Key Path (e.g., ~/.ssh/id_rsa): " SSH_KEY_PATH
read -p "Deploy Path on VPS (e.g., /home/user/xgb_trading): " DEPLOY_PATH

# Expand tilde in SSH key path
SSH_KEY_PATH="${SSH_KEY_PATH/#\~/$HOME}"

# Validate SSH key exists
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found at $SSH_KEY_PATH${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Configuration:${NC}"
echo -e "${BLUE}================================================${NC}"
echo "VPS Host:    $VPS_HOST"
echo "VPS User:    $VPS_USER"
echo "SSH Key:     $SSH_KEY_PATH"
echo "Deploy Path: $DEPLOY_PATH"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Test SSH connection
echo ""
echo -e "${BLUE}[1/7] Testing SSH connection...${NC}"
if ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "echo 'Connection successful'" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ SSH connection failed${NC}"
    echo "Please check your VPS credentials and SSH key"
    exit 1
fi

# Build Docker image
echo ""
echo -e "${BLUE}[2/7] Building Docker image...${NC}"
cd "$SCRIPT_DIR"
docker build -t ${DOCKER_IMAGE_NAME}:latest . || {
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Docker image built successfully${NC}"

# Save Docker image
echo ""
echo -e "${BLUE}[3/7] Saving Docker image...${NC}"
docker save ${DOCKER_IMAGE_NAME}:latest | gzip > /tmp/xgb-bot-image.tar.gz || {
    echo -e "${RED}✗ Failed to save Docker image${NC}"
    exit 1
}
echo -e "${GREEN}✓ Docker image saved ($(du -h /tmp/xgb-bot-image.tar.gz | cut -f1))${NC}"

# Create deployment directory on VPS
echo ""
echo -e "${BLUE}[4/7] Creating deployment directory on VPS...${NC}"
ssh -i "$SSH_KEY_PATH" "$VPS_USER@$VPS_HOST" "mkdir -p $DEPLOY_PATH" || {
    echo -e "${RED}✗ Failed to create directory${NC}"
    exit 1
}
echo -e "${GREEN}✓ Directory created${NC}"

# Copy files to VPS
echo ""
echo -e "${BLUE}[5/7] Copying files to VPS...${NC}"
echo "  - Copying project files..."
scp -i "$SSH_KEY_PATH" -r "$SCRIPT_DIR"/* "$VPS_USER@$VPS_HOST:$DEPLOY_PATH/" || {
    echo -e "${RED}✗ Failed to copy files${NC}"
    exit 1
}
echo "  - Copying Docker image..."
scp -i "$SSH_KEY_PATH" /tmp/xgb-bot-image.tar.gz "$VPS_USER@$VPS_HOST:$DEPLOY_PATH/" || {
    echo -e "${RED}✗ Failed to copy Docker image${NC}"
    exit 1
}
echo -e "${GREEN}✓ Files copied successfully${NC}"

# Deploy on VPS
echo ""
echo -e "${BLUE}[6/7] Deploying on VPS...${NC}"
ssh -i "$SSH_KEY_PATH" "$VPS_USER@$VPS_HOST" bash <<ENDSSH
    set -e
    cd $DEPLOY_PATH

    echo "Loading Docker image..."
    docker load < xgb-bot-image.tar.gz
    rm xgb-bot-image.tar.gz

    echo "Stopping existing containers..."
    docker-compose down || true

    echo "Starting containers..."
    docker-compose up -d

    echo "Waiting for bot to start..."
    sleep 10

    echo "Checking bot health..."
    if docker ps | grep -q xgb_5m_bot; then
        echo "✓ Bot is running!"
        docker-compose ps
    else
        echo "✗ Bot failed to start!"
        docker-compose logs --tail=50
        exit 1
    fi
ENDSSH

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment completed successfully${NC}"
else
    echo -e "${RED}✗ Deployment failed${NC}"
    exit 1
fi

# Cleanup
echo ""
echo -e "${BLUE}[7/7] Cleaning up...${NC}"
rm -f /tmp/xgb-bot-image.tar.gz
echo -e "${GREEN}✓ Cleanup complete${NC}"

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo "Bot URL: http://$VPS_HOST:8083"
echo "Monitor URL: http://$VPS_HOST:5001"
echo ""
echo "Next steps:"
echo "  1. Check logs: ssh -i $SSH_KEY_PATH $VPS_USER@$VPS_HOST 'cd $DEPLOY_PATH && docker-compose logs -f'"
echo "  2. Train model: ssh -i $SSH_KEY_PATH $VPS_USER@$VPS_HOST 'cd $DEPLOY_PATH && make train'"
echo ""
