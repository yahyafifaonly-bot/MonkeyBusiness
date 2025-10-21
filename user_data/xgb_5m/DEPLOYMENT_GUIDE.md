# XGBoost Trading Bot - VPS Deployment Guide

This guide explains how to deploy your XGBoost ML Trading Bot to a VPS server using GitHub Actions.

## Prerequisites

### 1. VPS Server Setup

Your VPS should have:
- Ubuntu 20.04+ or Debian 11+
- Docker and Docker Compose installed
- At least 2GB RAM
- 10GB free disk space
- SSH access enabled

### 2. Install Docker on VPS

```bash
# SSH into your VPS
ssh your_user@your_vps_ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes to take effect
exit
```

### 3. GitHub Secrets Configuration

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

#### Exchange Credentials
- `EXCHANGE_API_KEY` - Your Binance API key
- `EXCHANGE_API_SECRET` - Your Binance API secret

#### VPS Access
- `VPS_HOST` - Your VPS IP address (e.g., 123.456.789.0)
- `VPS_USER` - SSH username (e.g., ubuntu)
- `SSH_KEY_PRIVATE` - Your SSH private key
- `SSH_KEY_PUBLIC` - Your SSH public key

#### Email/Notification (Optional)
- `SMTP_SERVER` - SMTP server address
- `SMTP_PORT` - SMTP port (usually 587)
- `SMTP_USERNAME` - SMTP username
- `SMTP_PASSWORD` - SMTP password
- `NOTIFICATION_EMAIL` - Sender email
- `RECIPIENT_EMAILS` - Comma-separated recipient emails
- `MAILJET_API_KEY` - Mailjet API key (if using Mailjet)
- `MAILJET_SECRET` - Mailjet secret key

#### Database (if using)
- `MONGO_PASSWORD` - MongoDB password
- `REDIS_PASSWORD` - Redis password

## Generating SSH Keys

If you don't have SSH keys, generate them:

```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions-deploy"

# This creates:
# ~/.ssh/id_ed25519 (private key) - Add to SSH_KEY_PRIVATE secret
# ~/.ssh/id_ed25519.pub (public key) - Add to SSH_KEY_PUBLIC secret

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/id_ed25519.pub your_user@your_vps_ip
```

Add the keys to GitHub Secrets:
```bash
# Copy private key
cat ~/.ssh/id_ed25519

# Copy public key
cat ~/.ssh/id_ed25519.pub
```

## Deployment Process

### Automatic Deployment

1. **Push to main/production branch:**
   ```bash
   git add .
   git commit -m "Update trading bot"
   git push origin main
   ```

2. **GitHub Actions will automatically:**
   - Build Docker image
   - Copy files to VPS
   - Update configuration with secrets
   - Start the trading bot
   - Setup automated daily training

### Manual Deployment

1. Go to GitHub → Actions → "Deploy XGBoost Trading Bot to VPS"
2. Click "Run workflow"
3. Select branch (main/production)
4. Click "Run workflow"

## First Time Deployment

After first deployment, SSH into your VPS to train the model:

```bash
ssh your_user@your_vps_ip
cd ~/xgb_trading

# Train the model with 2 years of data
make train

# This will take 10-30 minutes
# Once complete, restart the bot
make restart
```

## Accessing Your Bot

After deployment:

- **Trading UI:** `http://your_vps_ip:8083`
  - Username: `xgbtrader`
  - Password: Check `config_xgb_5m.json` on VPS (auto-generated)

- **Learning Dashboard:** `http://your_vps_ip:5001`
  - No login required

## Monitoring

### Check Bot Status

```bash
ssh your_user@your_vps_ip
cd ~/xgb_trading

# Check if running
docker-compose ps

# View logs
docker-compose logs -f

# View recent trades
docker-compose logs | grep "Trade"
```

### Check Auto Training

```bash
# View cron schedule
crontab -l

# View training logs
tail -f ~/xgb_trading/logs/auto_incremental_*.log
```

## Security Best Practices

1. **Change Default Credentials**
   - After first login, change the API password
   - Use strong passwords

2. **Firewall Setup**
   ```bash
   # Allow SSH and bot ports
   sudo ufw allow 22
   sudo ufw allow 8083
   sudo ufw allow 5001
   sudo ufw enable
   ```

3. **Use HTTPS**
   - Set up nginx reverse proxy with SSL
   - Use Let's Encrypt for free certificates

4. **Monitor API Keys**
   - Never commit API keys to git
   - Rotate keys periodically
   - Use API key restrictions on Binance

5. **Regular Updates**
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade

   # Update Docker images
   docker-compose pull
   docker-compose up -d
   ```

## Troubleshooting

### Bot won't start

```bash
# Check logs
docker-compose logs

# Common issues:
# 1. No model trained - run: make train
# 2. Wrong API keys - check GitHub secrets
# 3. Port already in use - check: netstat -tulpn | grep 8083
```

### Can't access dashboard

```bash
# Check if containers are running
docker-compose ps

# Check firewall
sudo ufw status

# Test locally first
curl http://localhost:8083/api/v1/ping
```

### Deployment fails

1. Check GitHub Actions logs
2. Verify SSH keys are correct
3. Ensure VPS has Docker installed
4. Check VPS disk space: `df -h`

## Manual Commands on VPS

```bash
cd ~/xgb_trading

# Start bot
make run-detached

# Stop bot
make stop

# Restart bot
make restart

# View logs
make logs-live

# Train model
make train

# Incremental training
make incremental-train

# Check status
make status
```

## Rollback

If deployment fails:

```bash
ssh your_user@your_vps_ip
cd ~/xgb_trading

# Stop current version
docker-compose down

# Pull previous version from git
git checkout HEAD~1

# Rebuild and start
docker-compose build
docker-compose up -d
```

## Support

For issues:
1. Check logs on VPS: `docker-compose logs`
2. Check GitHub Actions logs
3. Review this guide
4. Check Freqtrade documentation: https://www.freqtrade.io/

---

**Remember:** Always test in dry-run mode before using real money!
