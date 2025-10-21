#!/bin/bash

# Docker Management Script for FreqTrade Trading Bot
# Usage: ./docker-start.sh [test|ml|production|stop|logs|status]

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}FreqTrade Docker Manager${NC}"
echo "======================================"

case "${1:-test}" in
    test|paper)
        echo -e "${GREEN}Starting Paper Trading Bot...${NC}"
        docker-compose up -d freqtrade-test
        echo ""
        echo -e "${GREEN}Paper Trading Bot Started!${NC}"
        echo "Dashboard: http://localhost:8081"
        echo "Username: freqtrader"
        echo "Password: freqtrader"
        echo ""
        echo "View logs: docker-compose logs -f freqtrade-test"
        ;;

    ml|training)
        echo -e "${YELLOW}Starting ML Training Bot...${NC}"
        docker-compose --profile ml up -d freqtrade-ml
        echo ""
        echo -e "${GREEN}ML Training Bot Started!${NC}"
        echo "Dashboard: http://localhost:8080"
        ;;

    production|live)
        echo -e "${RED}WARNING: Starting LIVE TRADING BOT with REAL MONEY!${NC}"
        read -p "Are you absolutely sure? Type 'YES' to confirm: " confirm
        if [ "$confirm" != "YES" ]; then
            echo "Cancelled."
            exit 1
        fi
        docker-compose --profile production up -d freqtrade-production
        echo ""
        echo -e "${GREEN}Production Bot Started!${NC}"
        echo "Dashboard: http://localhost:8082"
        ;;

    stop)
        echo -e "${YELLOW}Stopping all bots...${NC}"
        docker-compose down
        echo -e "${GREEN}All bots stopped.${NC}"
        ;;

    restart)
        echo -e "${YELLOW}Restarting Paper Trading Bot...${NC}"
        docker-compose restart freqtrade-test
        echo -e "${GREEN}Bot restarted.${NC}"
        ;;

    logs)
        echo -e "${GREEN}Showing logs (Ctrl+C to exit)...${NC}"
        docker-compose logs -f freqtrade-test
        ;;

    status)
        echo -e "${GREEN}Container Status:${NC}"
        docker-compose ps
        ;;

    build)
        echo -e "${YELLOW}Building Docker image...${NC}"
        docker-compose build
        echo -e "${GREEN}Build complete!${NC}"
        ;;

    shell)
        echo -e "${GREEN}Opening shell in container...${NC}"
        docker-compose exec freqtrade-test /bin/bash
        ;;

    *)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  test, paper      - Start paper trading bot (default)"
        echo "  ml, training     - Start ML training bot"
        echo "  production, live - Start live trading bot (DANGEROUS!)"
        echo "  stop             - Stop all bots"
        echo "  restart          - Restart paper trading bot"
        echo "  logs             - View logs"
        echo "  status           - Show container status"
        echo "  build            - Rebuild Docker image"
        echo "  shell            - Open shell in container"
        exit 1
        ;;
esac
