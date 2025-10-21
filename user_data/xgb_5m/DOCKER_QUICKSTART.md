# Docker Quick Start Guide

Run the XGBoost 5-Minute Trading Bot in Docker for easy deployment and consistent environment.

## Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (usually comes with Docker Desktop)
- 2GB free disk space
- Internet connection for data download

## Quick Start (3 Steps)

### 1. Train the Model

```bash
cd user_data/xgb_5m
chmod +x docker-train.sh
./docker-train.sh
```

This will:
- Build the Docker image with all dependencies
- Download 2 years of historical data from Binance
- Train XGBoost model (takes 10-30 minutes)
- Save model to `models/xgb_5m.pkl`

### 2. Start Trading

```bash
chmod +x docker-run.sh
./docker-run.sh
```

This will:
- Start the trading bot in a Docker container
- Run continuously with 5-minute candles
- Expose API on http://localhost:8083
- Show live trade notifications

### 3. Access Dashboard

Open in your browser:
```
http://localhost:8083
```

Login credentials:
- **Username:** xgbtrader
- **Password:** xgbtrader

## Manual Docker Commands

### Build the Image

```bash
cd user_data/xgb_5m
docker-compose build
```

### Train Model

```bash
docker-compose run --rm xgb-trading-bot \
    python3 /app/user_data/xgb_5m/train_xgb_5m.py
```

### Start Trading (Foreground)

```bash
docker-compose up
```

### Start Trading (Background/Detached)

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Stop the Bot

```bash
docker-compose down
```

### Incremental Learning

```bash
docker-compose run --rm xgb-trading-bot \
    python3 /app/user_data/xgb_5m/incremental_train.py --last-n-days 7
```

### Backtest

```bash
docker-compose run --rm xgb-trading-bot \
    freqtrade backtesting \
    --config /app/user_data/xgb_5m/config_xgb_5m.json \
    --strategy XGBScalp5m \
    --timerange 20230101-20231231 \
    --datadir /app/user_data/xgb_5m/data
```

## Data Persistence

The following directories are mounted as Docker volumes and persist across container restarts:

- `./models` - Trained XGBoost models
- `./data` - Historical market data
- `./sessions` - Trading session logs and reports
- `./logs` - Training and system logs
- `./strategies` - Strategy files (for easy updates)
- `./config_xgb_5m.json` - Configuration file

You can update strategies and config without rebuilding the Docker image.

## Common Operations

### Update Strategy

1. Edit `strategies/XGBScalp5m.py` on your host machine
2. Restart the container:
   ```bash
   docker-compose restart
   ```

### Update Configuration

1. Edit `config_xgb_5m.json` on your host machine
2. Restart the container:
   ```bash
   docker-compose restart
   ```

### Check Container Status

```bash
docker-compose ps
```

### Enter Running Container

```bash
docker-compose exec xgb-trading-bot /bin/bash
```

### Clean Up Everything

```bash
# Stop and remove containers
docker-compose down

# Remove all data (WARNING: This deletes models, logs, etc.)
rm -rf models/* data/* sessions/* logs/*
```

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs
```

### Model Not Found

Train the model first:
```bash
./docker-train.sh
```

### Port 8083 Already in Use

Change port in `docker-compose.yml`:
```yaml
ports:
  - "8084:8083"  # Change 8084 to any available port
```

### Out of Disk Space

Clean up Docker:
```bash
docker system prune -a
```

### Permission Denied

Make scripts executable:
```bash
chmod +x docker-train.sh docker-run.sh
```

## Environment Variables

You can customize behavior with environment variables in `docker-compose.yml`:

```yaml
environment:
  - PYTHONUNBUFFERED=1  # See Python output immediately
  - FREQTRADE_USER_DATA_DIR=/app/user_data
  # Add your custom variables here
```

## Production Deployment

### For Live Trading (Real Money)

1. **Update config for live trading:**
   ```json
   {
     "dry_run": false,
     "exchange": {
       "key": "your_api_key",
       "secret": "your_api_secret"
     }
   }
   ```

2. **Use environment variables for secrets:**
   ```bash
   # Create .env file (DO NOT commit to git)
   echo "BINANCE_API_KEY=your_key" > .env
   echo "BINANCE_API_SECRET=your_secret" >> .env
   ```

   Update `docker-compose.yml`:
   ```yaml
   environment:
     - BINANCE_API_KEY=${BINANCE_API_KEY}
     - BINANCE_API_SECRET=${BINANCE_API_SECRET}
   ```

3. **Run in detached mode:**
   ```bash
   docker-compose up -d
   ```

4. **Monitor with logs:**
   ```bash
   docker-compose logs -f
   ```

### Auto-Restart on Failure

Already configured in `docker-compose.yml`:
```yaml
restart: unless-stopped
```

The bot will automatically restart if it crashes.

### Run on Server/VPS

1. **Install Docker on server**
2. **Copy project to server:**
   ```bash
   scp -r user_data/xgb_5m user@server:/path/to/
   ```

3. **SSH to server and run:**
   ```bash
   cd /path/to/xgb_5m
   ./docker-train.sh
   docker-compose up -d
   ```

4. **Access remotely:**
   Update `config_xgb_5m.json`:
   ```json
   {
     "api_server": {
       "listen_ip_address": "0.0.0.0",  // Allow external access
       "username": "your_secure_username",
       "password": "your_secure_password"
     }
   }
   ```

   Access at: `http://your-server-ip:8083`

## Health Monitoring

Docker Compose includes health checks:

```bash
# View health status
docker-compose ps

# Healthy output:
# xgb_5m_bot  /bin/sh -c freqtrade ...  Up (healthy)
```

Health check pings the API every 30 seconds. If it fails 3 times, the container is marked unhealthy (but continues running).

## Resource Limits

To limit CPU and memory usage, add to `docker-compose.yml`:

```yaml
services:
  xgb-trading-bot:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2.0'      # Max 2 CPU cores
          memory: 2G       # Max 2GB RAM
        reservations:
          cpus: '0.5'      # Minimum 0.5 cores
          memory: 512M     # Minimum 512MB RAM
```

## Security Best Practices

1. **Never commit API keys** to git
2. **Use environment variables** for secrets
3. **Change default passwords** in config
4. **Use firewall** to restrict API access
5. **Keep Docker images updated:**
   ```bash
   docker-compose pull
   docker-compose build --no-cache
   ```

## Backup

### Backup Models and Data

```bash
tar -czf xgb_backup_$(date +%Y%m%d).tar.gz models/ sessions/ logs/
```

### Restore from Backup

```bash
tar -xzf xgb_backup_20241021.tar.gz
```

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Check README.md for detailed documentation
3. Verify Docker version: `docker --version`
4. Rebuild image: `docker-compose build --no-cache`

---

**Happy Trading! Remember to start with dry-run mode and thoroughly test before using real money.**
