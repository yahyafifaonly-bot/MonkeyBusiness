# XGBoost 5-Minute Trading Bot - Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib from source
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz && \
    ldconfig

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip

# Install Freqtrade and dependencies
RUN pip install --no-cache-dir \
    freqtrade[freqai] \
    xgboost \
    scikit-learn \
    pandas \
    numpy \
    ta-lib \
    ccxt \
    matplotlib \
    plotly \
    scipy

# Create necessary directories
RUN mkdir -p /app/user_data/xgb_5m/models \
    /app/user_data/xgb_5m/data \
    /app/user_data/xgb_5m/logs \
    /app/user_data/xgb_5m/sessions

# Copy the XGBoost trading system files
COPY train_xgb_5m.py /app/user_data/xgb_5m/
COPY incremental_train.py /app/user_data/xgb_5m/
COPY config_xgb_5m.json /app/user_data/xgb_5m/
COPY strategies/ /app/user_data/xgb_5m/strategies/

# Set permissions
RUN chmod +x /app/user_data/xgb_5m/train_xgb_5m.py \
    /app/user_data/xgb_5m/incremental_train.py

# Expose API port
EXPOSE 8083

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FREQTRADE_USER_DATA_DIR=/app/user_data

# Default command (can be overridden)
CMD ["freqtrade", "trade", \
     "--config", "/app/user_data/xgb_5m/config_xgb_5m.json", \
     "--strategy", "XGBScalp5m", \
     "--datadir", "/app/user_data/xgb_5m/data", \
     "--user-data-dir", "/app/user_data"]
