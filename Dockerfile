FROM freqtradeorg/freqtrade:stable

# Install additional dependencies if needed
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER ftuser

# Install FreqAI dependencies including datasieve
RUN pip install --no-cache-dir datasieve scikit-learn scipy catboost lightgbm xgboost

# Copy strategy and configuration files
COPY --chown=ftuser:ftuser user_data /freqtrade/user_data

# Expose the API port
EXPOSE 8081

# Default command (can be overridden in docker-compose)
CMD ["trade", "--config", "user_data/test_env/config_test.json", "--strategy", "ScalpingLearner", "--user-data-dir", "user_data/test_env", "--datadir", "user_data/test_env/data"]
