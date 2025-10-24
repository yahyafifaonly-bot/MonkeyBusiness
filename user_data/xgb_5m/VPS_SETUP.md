# VPS Setup Guide - XGBoost Trading Bot + Dashboard

## Problem: Dashboard Not Working on VPS

**The deployment is FAILING** because of SSH permission issues.

You need to:
1. Fix GitHub Secrets for SSH access
2. Deploy manually to VPS
3. Start dashboard service

---

## Quick Fix: Manual Deployment (Works Immediately)

### 1. SSH to Your VPS

```bash
ssh your_user@your_vps_ip
```

### 2. Clone/Pull Latest Code

```bash
# If first time
cd ~
git clone https://github.com/yahyafifaonly-bot/MonkeyBusiness.git
cd MonkeyBusiness/user_data/xgb_5m

# If already exists
cd ~/MonkeyBusiness
git pull origin develop
cd user_data/xgb_5m
```

### 3. Install Dependencies

```bash
# Install Python packages
pip install freqtrade[freqai] xgboost scikit-learn flask flask-cors

# Or if you have requirements.txt
pip install -r requirements.txt
```

### 4. Create Config File (with your API keys)

```bash
cat > config_xgb_5m.json << 'EOF'
{
    "max_open_trades": 8,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.99,
    "dry_run": false,
    "exchange": {
        "name": "binance",
        "key": "YOUR_BINANCE_API_KEY",
        "secret": "YOUR_BINANCE_API_SECRET",
        "pair_whitelist": [
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "BNB/USDT"
        ]
    },
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8083,
        "username": "xgbtrader",
        "password": "CHANGE_THIS_PASSWORD"
    }
}
EOF

# Edit with your real keys
nano config_xgb_5m.json
```

### 5. Train Initial Model

```bash
python train_xgb_5m.py
```

Watch the training progress in logs!

### 6. Start Everything

```bash
# Simple one-command start
./start_all.sh

# Or start manually:
# Start trading bot
nohup freqtrade trade --config config_xgb_5m.json --strategy XGBScalp5m > logs/bot.log 2>&1 &

# Start dashboard
nohup python monitor.py > logs/dashboard.log 2>&1 &
```

### 7. Open Firewall Ports

```bash
# If using ufw
sudo ufw allow 8083  # Trading bot API
sudo ufw allow 5001  # Dashboard
sudo ufw reload

# If using firewalld
sudo firewall-cmd --permanent --add-port=8083/tcp
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

### 8. Access Dashboard

```
http://YOUR_VPS_IP:5001
```

**Dashboard should now show:**
- Win Rate
- Trading signals
- Live training logs
- Feature importance
- All metrics

---

## Fix GitHub Actions Deployment (For Automatic Deployment)

The deployment fails because GitHub can't SSH to your VPS.

### Step 1: Generate SSH Key on Your Local Machine

```bash
ssh-keygen -t ed25519 -f ~/.ssh/vps_deploy_key -N ""
```

### Step 2: Copy Public Key to VPS

```bash
ssh-copy-id -i ~/.ssh/vps_deploy_key.pub your_user@your_vps_ip

# Or manually:
cat ~/.ssh/vps_deploy_key.pub
# Then SSH to VPS and add to ~/.ssh/authorized_keys
```

### Step 3: Add Private Key to GitHub Secrets

```bash
# Display private key
cat ~/.ssh/vps_deploy_key
```

1. Go to: https://github.com/yahyafifaonly-bot/MonkeyBusiness/settings/secrets/actions
2. Click "New repository secret"
3. Name: `SSH_KEY_PRIVATE`
4. Value: Paste the entire private key (including BEGIN and END lines)
5. Click "Add secret"

### Step 4: Add Other Required Secrets

Add these secrets to GitHub:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `SSH_KEY_PRIVATE` | Your SSH private key | From step above |
| `VPS_HOST` | Your VPS IP address | e.g., 123.45.67.89 |
| `VPS_USER` | Your VPS username | e.g., ubuntu, root |
| `EXCHANGE_API_KEY` | Binance API Key | Your trading API key |
| `EXCHANGE_API_SECRET` | Binance API Secret | Your trading secret |

### Step 5: Update Deployment Workflow

The workflow needs to start the dashboard. Let me update it...

### Step 6: Push to GitHub

Once secrets are configured, every push to `develop` will:
1. Build Docker image
2. Deploy to VPS
3. Start trading bot
4. Start dashboard on port 5001
5. Set up auto-training

---

## Verify Everything is Running

### On VPS:

```bash
# Check processes
ps aux | grep -E 'freqtrade|monitor.py'

# Check if ports are listening
netstat -tlnp | grep -E '8083|5001'

# Check logs
tail -f logs/bot.log
tail -f logs/dashboard.log
tail -f logs/training.log

# Check if services respond
curl http://localhost:8083/api/v1/ping
curl http://localhost:5001
```

### From Your Computer:

```bash
# Check bot API
curl http://YOUR_VPS_IP:8083/api/v1/ping

# Check dashboard
curl http://YOUR_VPS_IP:5001

# Or open in browser:
# http://YOUR_VPS_IP:5001
```

---

## Make Services Auto-Start on Reboot

### Option 1: Using systemd (Recommended)

Create service file:

```bash
sudo nano /etc/systemd/system/xgb-trading.service
```

```ini
[Unit]
Description=XGBoost Trading Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/MonkeyBusiness/user_data/xgb_5m
ExecStart=/home/YOUR_USER/MonkeyBusiness/user_data/xgb_5m/start_all.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable xgb-trading
sudo systemctl start xgb-trading
sudo systemctl status xgb-trading
```

### Option 2: Using crontab

```bash
crontab -e

# Add this line:
@reboot cd /home/YOUR_USER/MonkeyBusiness/user_data/xgb_5m && ./start_all.sh
```

---

## Troubleshooting

### Dashboard not accessible?

```bash
# Check if monitor.py is running
ps aux | grep monitor.py

# Check if port 5001 is open
netstat -tlnp | grep 5001

# Check firewall
sudo ufw status | grep 5001

# Check logs
tail -50 logs/dashboard.log

# Restart dashboard
pkill -f monitor.py
nohup python monitor.py > logs/dashboard.log 2>&1 &
```

### Trading bot not running?

```bash
# Check if freqtrade is running
ps aux | grep freqtrade

# Check logs
tail -50 logs/bot.log

# Restart bot
pkill -f freqtrade
./start_all.sh
```

### GitHub Actions still failing?

1. Check secrets are configured correctly
2. Test SSH manually: `ssh -i ~/.ssh/vps_deploy_key your_user@your_vps_ip`
3. Check VPS firewall allows SSH from GitHub IPs
4. View deployment logs: `gh run view <run_id> --log-failed`

---

## Summary

**Local Development:**
```bash
cd user_data/xgb_5m
./start_all.sh
# Dashboard: http://localhost:5001
# Bot API: http://localhost:8083
```

**VPS Production:**
```bash
ssh your_user@your_vps_ip
cd ~/MonkeyBusiness/user_data/xgb_5m
git pull origin develop
./start_all.sh
# Dashboard: http://YOUR_VPS_IP:5001
# Bot API: http://YOUR_VPS_IP:8083
```

**Both Local and VPS:**
- Same code
- Same commands
- Same port numbers (8083, 5001)
- Same scripts work everywhere

**Dashboard shows (on both):**
- Win Rate
- Total Signals
- Winners/Losers
- Live Training Logs
- Feature Importance
- All Performance Metrics
