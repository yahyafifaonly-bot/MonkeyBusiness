#!/bin/bash
# Setup script for automated daily incremental training

SCRIPT_PATH="/Users/yahya/Monkeybusiness/user_data/xgb_5m/auto_incremental_train.sh"
CRON_COMMENT="# XGBoost Auto Incremental Training"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  XGBoost Auto Training Setup                         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    ALREADY_SETUP=true
else
    ALREADY_SETUP=false
fi

# Show current status
if [ "$ALREADY_SETUP" = true ]; then
    CURRENT_SCHEDULE=$(crontab -l 2>/dev/null | grep "$SCRIPT_PATH" | awk '{print $1, $2, $3, $4, $5}')
    echo -e "${GREEN}✓ Auto training is currently ENABLED${NC}"
    echo -e "  Schedule: ${YELLOW}$CURRENT_SCHEDULE${NC}"
    echo ""
else
    echo -e "${YELLOW}○ Auto training is currently DISABLED${NC}"
    echo ""
fi

# Menu
echo "What would you like to do?"
echo ""
echo "  1) Enable daily auto training (recommended time: 6 PM)"
echo "  2) Enable daily auto training (custom time)"
echo "  3) Disable auto training"
echo "  4) View current schedule"
echo "  5) Test run now"
echo "  6) Exit"
echo ""
read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo ""
        echo -e "${BLUE}[INFO]${NC} Setting up auto training at 6:00 PM daily..."

        # Remove old entry if exists
        (crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH") | crontab -

        # Add new entry - 6 PM every day
        (crontab -l 2>/dev/null; echo "$CRON_COMMENT"; echo "0 18 * * * $SCRIPT_PATH") | crontab -

        echo -e "${GREEN}✓ Success!${NC} Auto training will run daily at 6:00 PM"
        echo ""
        echo "The system will:"
        echo "  • Download latest market data"
        echo "  • Retrain the model with last 7 days"
        echo "  • Restart the bot with updated model"
        echo "  • Log everything to: logs/auto_incremental_YYYYMMDD.log"
        ;;

    2)
        echo ""
        echo "Enter your preferred time:"
        read -p "  Hour (0-23): " hour
        read -p "  Minute (0-59): " minute

        if ! [[ "$hour" =~ ^[0-9]+$ ]] || [ "$hour" -lt 0 ] || [ "$hour" -gt 23 ]; then
            echo -e "${RED}Error: Invalid hour${NC}"
            exit 1
        fi

        if ! [[ "$minute" =~ ^[0-9]+$ ]] || [ "$minute" -lt 0 ] || [ "$minute" -gt 59 ]; then
            echo -e "${RED}Error: Invalid minute${NC}"
            exit 1
        fi

        # Remove old entry if exists
        (crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH") | crontab -

        # Add new entry
        (crontab -l 2>/dev/null; echo "$CRON_COMMENT"; echo "$minute $hour * * * $SCRIPT_PATH") | crontab -

        echo ""
        echo -e "${GREEN}✓ Success!${NC} Auto training will run daily at $(printf "%02d:%02d" $hour $minute)"
        ;;

    3)
        echo ""
        echo -e "${YELLOW}[REMOVE]${NC} Disabling auto training..."

        # Remove cron job
        (crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" | grep -v "$CRON_COMMENT") | crontab -

        echo -e "${GREEN}✓ Success!${NC} Auto training disabled"
        echo ""
        echo "You can still run incremental training manually:"
        echo "  make incremental-train"
        ;;

    4)
        echo ""
        echo -e "${BLUE}Current Cron Schedule:${NC}"
        echo ""
        if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
            crontab -l 2>/dev/null | grep -A1 "$CRON_COMMENT"
        else
            echo "  (No auto training scheduled)"
        fi
        echo ""
        ;;

    5)
        echo ""
        echo -e "${BLUE}[TEST]${NC} Running incremental training now..."
        echo ""

        if [ -f "$SCRIPT_PATH" ]; then
            $SCRIPT_PATH
        else
            echo -e "${RED}Error: Script not found at $SCRIPT_PATH${NC}"
            exit 1
        fi
        ;;

    6)
        echo ""
        echo "Exiting..."
        exit 0
        ;;

    *)
        echo ""
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Useful Commands                                      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  View logs:        tail -f logs/auto_incremental_*.log"
echo "  Manual training:  make incremental-train"
echo "  Check schedule:   crontab -l"
echo "  Reconfigure:      ./setup_auto_training.sh"
echo ""
