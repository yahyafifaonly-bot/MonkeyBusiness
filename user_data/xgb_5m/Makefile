.PHONY: help build train run stop restart logs logs-live shell clean status health backtest incremental-train download-data test

# Colors for output
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
RED    := \033[0;31m
NC     := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help message
	@echo ""
	@echo "$(GREEN)╔═══════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║     XGBoost 5-Minute Trading Bot - Makefile Commands     ║$(NC)"
	@echo "$(GREEN)╚═══════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(BLUE)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Setup & Build

build: ## Build Docker image
	@echo "$(BLUE)[INFO]$(NC) Building Docker image..."
	@docker-compose build
	@echo "$(GREEN)[SUCCESS]$(NC) Docker image built successfully!"

pull: ## Pull latest base images
	@echo "$(BLUE)[INFO]$(NC) Pulling latest base images..."
	@docker-compose pull

##@ Training

train: ## Train XGBoost model (downloads 2 years of data)
	@echo "$(BLUE)[INFO]$(NC) Starting model training..."
	@echo "$(YELLOW)[NOTE]$(NC) This will take 10-30 minutes depending on your system."
	@docker-compose run --rm xgb-trading-bot \
		python3 /app/user_data/xgb_5m/train_xgb_5m.py
	@echo "$(GREEN)[SUCCESS]$(NC) Model training completed!"

train-quick: ## Train model with less data (faster, for testing)
	@echo "$(BLUE)[INFO]$(NC) Starting quick training (90 days of data)..."
	@docker-compose run --rm xgb-trading-bot \
		python3 /app/user_data/xgb_5m/train_xgb_5m.py --days 90
	@echo "$(GREEN)[SUCCESS]$(NC) Quick training completed!"

incremental-train: ## Perform incremental learning from last 7 days
	@echo "$(BLUE)[INFO]$(NC) Performing incremental learning..."
	@docker-compose run --rm xgb-trading-bot \
		python3 /app/user_data/xgb_5m/incremental_train.py --last-n-days 7
	@echo "$(GREEN)[SUCCESS]$(NC) Incremental learning completed!"

incremental-train-all: ## Incremental learning from all sessions
	@echo "$(BLUE)[INFO]$(NC) Performing incremental learning from all sessions..."
	@docker-compose run --rm xgb-trading-bot \
		python3 /app/user_data/xgb_5m/incremental_train.py --all-sessions
	@echo "$(GREEN)[SUCCESS]$(NC) Incremental learning completed!"

##@ Trading Bot

run: ## Start trading bot (foreground)
	@echo "$(GREEN)[START]$(NC) Starting trading bot..."
	@echo "$(BLUE)[INFO]$(NC) Press Ctrl+C to stop"
	@echo "$(BLUE)[INFO]$(NC) API: http://localhost:8083"
	@echo "$(BLUE)[INFO]$(NC) Username: xgbtrader | Password: xgbtrader"
	@docker-compose up

run-detached: ## Start trading bot (background)
	@echo "$(GREEN)[START]$(NC) Starting trading bot in background..."
	@docker-compose up -d
	@echo "$(GREEN)[SUCCESS]$(NC) Bot started!"
	@echo "$(BLUE)[INFO]$(NC) API: http://localhost:8083"
	@echo "$(BLUE)[INFO]$(NC) Use 'make logs' to view output"

stop: ## Stop trading bot
	@echo "$(YELLOW)[STOP]$(NC) Stopping trading bot..."
	@docker-compose down
	@echo "$(GREEN)[SUCCESS]$(NC) Bot stopped!"

restart: stop run-detached ## Restart trading bot

##@ Monitoring

logs: ## View bot logs
	@docker-compose logs --tail=100

logs-live: ## Follow bot logs in real-time
	@echo "$(BLUE)[INFO]$(NC) Following logs... Press Ctrl+C to stop"
	@docker-compose logs -f

status: ## Check bot status
	@echo "$(BLUE)[INFO]$(NC) Checking bot status..."
	@docker-compose ps

health: ## Check bot health
	@echo "$(BLUE)[INFO]$(NC) Checking bot health..."
	@docker-compose ps | grep -q "healthy" && echo "$(GREEN)[HEALTHY]$(NC) Bot is running and healthy" || echo "$(RED)[UNHEALTHY]$(NC) Bot may have issues"

shell: ## Open shell in running container
	@echo "$(BLUE)[INFO]$(NC) Opening shell in container..."
	@docker-compose exec xgb-trading-bot /bin/bash

shell-run: ## Run a new container with shell
	@echo "$(BLUE)[INFO]$(NC) Starting new container with shell..."
	@docker-compose run --rm xgb-trading-bot /bin/bash

##@ Data Management

download-data: ## Download latest market data
	@echo "$(BLUE)[INFO]$(NC) Downloading latest market data..."
	@docker-compose run --rm xgb-trading-bot \
		freqtrade download-data \
		--exchange binance \
		--pairs BTC/USDT ETH/USDT SOL/USDT BNB/USDT \
		--timeframes 5m \
		--days 7 \
		--datadir /app/user_data/xgb_5m/data
	@echo "$(GREEN)[SUCCESS]$(NC) Data downloaded!"

download-data-full: ## Download full 2 years of data
	@echo "$(BLUE)[INFO]$(NC) Downloading 2 years of market data..."
	@docker-compose run --rm xgb-trading-bot \
		freqtrade download-data \
		--exchange binance \
		--pairs BTC/USDT ETH/USDT SOL/USDT BNB/USDT \
		--timeframes 5m \
		--days 730 \
		--datadir /app/user_data/xgb_5m/data
	@echo "$(GREEN)[SUCCESS]$(NC) Full data downloaded!"

##@ Testing & Analysis

backtest: ## Run backtest on historical data
	@echo "$(BLUE)[INFO]$(NC) Running backtest..."
	@docker-compose run --rm xgb-trading-bot \
		freqtrade backtesting \
		--config /app/user_data/xgb_5m/config_xgb_5m.json \
		--strategy XGBScalp5m \
		--timerange 20230101-20231231 \
		--datadir /app/user_data/xgb_5m/data
	@echo "$(GREEN)[SUCCESS]$(NC) Backtest completed!"

backtest-plot: ## Run backtest and generate plot
	@echo "$(BLUE)[INFO]$(NC) Running backtest with plotting..."
	@docker-compose run --rm xgb-trading-bot \
		freqtrade backtesting \
		--config /app/user_data/xgb_5m/config_xgb_5m.json \
		--strategy XGBScalp5m \
		--timerange 20230101-20231231 \
		--datadir /app/user_data/xgb_5m/data \
		--export trades
	@echo "$(GREEN)[SUCCESS]$(NC) Backtest completed! Check user_data/xgb_5m/backtest_results/"

test: ## Run quick validation test
	@echo "$(BLUE)[INFO]$(NC) Running validation tests..."
	@docker-compose run --rm xgb-trading-bot \
		freqtrade test-pairlist \
		--config /app/user_data/xgb_5m/config_xgb_5m.json
	@echo "$(GREEN)[SUCCESS]$(NC) Validation passed!"

##@ Cleanup

clean: ## Stop bot and remove containers
	@echo "$(YELLOW)[CLEAN]$(NC) Stopping bot and removing containers..."
	@docker-compose down
	@echo "$(GREEN)[SUCCESS]$(NC) Containers removed!"

clean-all: ## Stop bot, remove containers and images
	@echo "$(RED)[CLEAN ALL]$(NC) Removing containers, images, and volumes..."
	@docker-compose down --rmi all --volumes
	@echo "$(GREEN)[SUCCESS]$(NC) Everything cleaned!"

clean-data: ## Remove downloaded market data (WARNING: will need to re-download)
	@echo "$(RED)[WARNING]$(NC) This will delete all downloaded market data!"
	@read -p "Are you sure? (y/N): " confirm && [ $$confirm = y ] || exit 1
	@rm -rf data/*
	@echo "$(GREEN)[SUCCESS]$(NC) Market data cleaned!"

clean-models: ## Remove trained models (WARNING: will need to retrain)
	@echo "$(RED)[WARNING]$(NC) This will delete all trained models!"
	@read -p "Are you sure? (y/N): " confirm && [ $$confirm = y ] || exit 1
	@rm -rf models/*
	@echo "$(GREEN)[SUCCESS]$(NC) Models cleaned!"

clean-sessions: ## Remove session logs and reports
	@echo "$(YELLOW)[CLEAN]$(NC) Removing session data..."
	@rm -rf sessions/*
	@echo "$(GREEN)[SUCCESS]$(NC) Session data cleaned!"

##@ Information

model-info: ## Display trained model information
	@echo "$(BLUE)[INFO]$(NC) Model Information:"
	@if [ -f models/xgb_5m_metadata.json ]; then \
		cat models/xgb_5m_metadata.json | python3 -m json.tool; \
	else \
		echo "$(RED)[ERROR]$(NC) No model found. Run 'make train' first."; \
	fi

config-show: ## Show current configuration
	@echo "$(BLUE)[INFO]$(NC) Current Configuration:"
	@cat config_xgb_5m.json | python3 -m json.tool

sessions-list: ## List all trading sessions
	@echo "$(BLUE)[INFO]$(NC) Trading Sessions:"
	@ls -lh sessions/ | tail -n +2 || echo "$(YELLOW)[INFO]$(NC) No sessions found yet"

api-test: ## Test API connection
	@echo "$(BLUE)[INFO]$(NC) Testing API connection..."
	@curl -s http://localhost:8083/api/v1/ping && echo "\n$(GREEN)[SUCCESS]$(NC) API is accessible!" || echo "$(RED)[ERROR]$(NC) API is not accessible"

##@ Quick Workflows

first-run: build train run ## Complete first-time setup: build, train, and run
	@echo "$(GREEN)[SUCCESS]$(NC) Complete setup finished!"

daily: incremental-train run-detached ## Daily workflow: incremental training and start bot
	@echo "$(GREEN)[SUCCESS]$(NC) Daily routine completed!"

quick-start: ## Quick start with existing model
	@if [ ! -f models/xgb_5m.pkl ]; then \
		echo "$(RED)[ERROR]$(NC) No model found. Run 'make train' first."; \
		exit 1; \
	fi
	@$(MAKE) run-detached
	@echo "$(GREEN)[SUCCESS]$(NC) Bot started with existing model!"

##@ Docker Management

docker-prune: ## Clean up unused Docker resources
	@echo "$(YELLOW)[PRUNE]$(NC) Cleaning up Docker resources..."
	@docker system prune -f
	@echo "$(GREEN)[SUCCESS]$(NC) Docker resources cleaned!"

docker-stats: ## Show Docker resource usage
	@echo "$(BLUE)[INFO]$(NC) Docker Resource Usage:"
	@docker stats --no-stream xgb_5m_bot 2>/dev/null || echo "$(YELLOW)[INFO]$(NC) Bot is not running"

images: ## List Docker images
	@echo "$(BLUE)[INFO]$(NC) Docker Images:"
	@docker images | grep xgb

volumes: ## List Docker volumes
	@echo "$(BLUE)[INFO]$(NC) Docker Volumes:"
	@docker volume ls | grep xgb

##@ Development

dev-shell: ## Start development shell with live code mounting
	@echo "$(BLUE)[INFO]$(NC) Starting development shell..."
	@docker-compose run --rm xgb-trading-bot /bin/bash

strategy-test: ## Test strategy syntax
	@echo "$(BLUE)[INFO]$(NC) Testing strategy syntax..."
	@docker-compose run --rm xgb-trading-bot \
		python3 -m py_compile /app/user_data/xgb_5m/strategies/XGBScalp5m.py
	@echo "$(GREEN)[SUCCESS]$(NC) Strategy syntax is valid!"

rebuild: clean-all build ## Clean everything and rebuild from scratch
	@echo "$(GREEN)[SUCCESS]$(NC) Complete rebuild finished!"
