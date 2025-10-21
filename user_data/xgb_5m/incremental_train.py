#!/usr/bin/env python3
"""
Incremental Training Script for XGBoost 5m Scalping Strategy

This script performs incremental learning by:
1. Loading the existing trained model
2. Reading new trade data from completed sessions
3. Fetching corresponding market data for those trades
4. Retraining the model with the new data
5. Saving the updated model

Usage:
    python3 incremental_train.py --session-id 20241021_143000
    python3 incremental_train.py --all-sessions
    python3 incremental_train.py --last-n-days 7
"""

import os
import sys
import json
import argparse
import pickle
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import xgboost as xgb
import ccxt
import talib.abstract as ta
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('user_data/xgb_5m/logs/incremental_train.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IncrementalTrainer:
    """Incremental learning for XGBoost model"""

    def __init__(self, model_path: str, data_dir: str, sessions_dir: str):
        self.model_path = model_path
        self.data_dir = data_dir
        self.sessions_dir = sessions_dir
        self.model = None
        self.exchange = None
        self.feature_columns = None

        # Trading pairs
        self.pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']

        # Ensure directories exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(sessions_dir, exist_ok=True)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

    def load_model(self):
        """Load existing XGBoost model"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}. Train initial model first.")

        logger.info(f"Loading existing model from {self.model_path}")
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.feature_columns = model_data['feature_columns']

        logger.info(f"Model loaded successfully. Features: {len(self.feature_columns)}")

        # Load metadata if available
        metadata_path = self.model_path.replace('.pkl', '_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            logger.info(f"Previous model accuracy: {metadata.get('accuracy', 'N/A')}")

    def init_exchange(self):
        """Initialize CCXT exchange"""
        logger.info("Initializing Binance exchange")
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def load_trade_log(self, session_id: str = None, all_sessions: bool = False,
                      last_n_days: int = None) -> List[Dict]:
        """Load trades from session log files"""
        trades = []
        trade_log_path = os.path.join(self.sessions_dir, 'trades.jsonl')

        if not os.path.exists(trade_log_path):
            logger.warning(f"No trade log found at {trade_log_path}")
            return trades

        logger.info(f"Loading trades from {trade_log_path}")

        with open(trade_log_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        trade = json.loads(line)
                        trades.append(trade)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping invalid JSON line: {line[:50]}")

        # Filter by criteria
        if session_id:
            # Filter by session timestamp (assuming trades have timestamp)
            logger.info(f"Filtering trades for session {session_id}")
            # Session ID format: YYYYMMDD_HHMMSS
            session_time = datetime.strptime(session_id, '%Y%m%d_%H%M%S')
            trades = [t for t in trades if self._trade_in_session(t, session_time)]

        elif last_n_days:
            logger.info(f"Filtering trades from last {last_n_days} days")
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=last_n_days)
            trades = [t for t in trades if self._trade_after_time(t, cutoff_time)]

        logger.info(f"Loaded {len(trades)} trades for incremental learning")
        return trades

    def _trade_in_session(self, trade: Dict, session_time: datetime) -> bool:
        """Check if trade belongs to a specific session"""
        try:
            trade_time = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
            # Trades within 3 hours after session start
            return session_time <= trade_time.replace(tzinfo=None) <= session_time + timedelta(hours=3)
        except:
            return False

    def _trade_after_time(self, trade: Dict, cutoff_time: datetime) -> bool:
        """Check if trade is after cutoff time"""
        try:
            trade_time = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
            return trade_time >= cutoff_time
        except:
            return False

    def fetch_trade_context_data(self, trades: List[Dict]) -> pd.DataFrame:
        """
        Fetch OHLCV data around trade times to reconstruct features
        For each trade, fetch 100 candles before entry to calculate indicators
        """
        all_data = []

        for trade in trades:
            try:
                pair = trade['pair']
                timestamp = trade['timestamp']
                trade_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                # Fetch 100 candles before trade (5min * 100 = ~8 hours of context)
                since = int((trade_time - timedelta(hours=10)).timestamp() * 1000)
                limit = 120  # Extra buffer

                logger.info(f"Fetching context data for {pair} at {trade_time}")

                ohlcv = self.exchange.fetch_ohlcv(pair, '5m', since=since, limit=limit)

                if len(ohlcv) < 50:
                    logger.warning(f"Insufficient data for {pair} at {trade_time}")
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['pair'] = pair

                # Add trade outcome
                df['trade_profit'] = trade['profit_pct']
                df['is_winning_trade'] = 1 if trade['profit_pct'] > 0 else 0

                all_data.append(df)

            except Exception as e:
                logger.error(f"Error fetching data for trade {trade}: {e}")
                continue

        if not all_data:
            logger.warning("No trade context data could be fetched")
            return pd.DataFrame()

        combined_df = pd.concat(all_data, ignore_index=True)
        logger.info(f"Fetched {len(combined_df)} candles of context data")

        return combined_df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate same indicators as training (MUST MATCH train_xgb_5m.py)"""
        logger.info("Calculating technical indicators")

        # RSI
        df['rsi'] = ta.RSI(df['close'], timeperiod=14)
        df['rsi_fast'] = ta.RSI(df['close'], timeperiod=7)
        df['rsi_slow'] = ta.RSI(df['close'], timeperiod=21)

        # MACD
        macd = ta.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['macd'] = macd['macd']
        df['macd_signal'] = macd['macdsignal']
        df['macd_hist'] = macd['macdhist']
        df['macd_hist_pct'] = df['macd_hist'] / df['close'] * 100

        # EMAs
        df['ema_9'] = ta.EMA(df['close'], timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'], timeperiod=21)
        df['ema_50'] = ta.EMA(df['close'], timeperiod=50)

        # EMA slopes
        df['ema9_slope'] = df['ema_9'].pct_change(periods=3) * 100
        df['ema21_slope'] = df['ema_21'].pct_change(periods=3) * 100
        df['ema9_vs_21'] = (df['ema_9'] - df['ema_21']) / df['ema_21'] * 100
        df['ema9_vs_50'] = (df['ema_9'] - df['ema_50']) / df['ema_50'] * 100

        # Bollinger Bands
        upper, middle, lower = ta.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_percent'] = (df['close'] - lower) / (upper - lower)
        df['bb_width'] = (upper - lower) / middle

        # ATR
        df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        df['atr_pct'] = df['atr'] / df['close'] * 100

        # Volume indicators
        df['volume_mean_20'] = df['volume'].rolling(window=20).mean()
        df['volume_mean_50'] = df['volume'].rolling(window=50).mean()
        df['volume_std_20'] = df['volume'].rolling(window=20).std()
        df['volume_std_50'] = df['volume'].rolling(window=50).std()
        df['volume_zscore'] = (df['volume'] - df['volume_mean_50']) / (df['volume_std_50'] + 1e-10)
        df['volume_ratio_20_50'] = df['volume_mean_20'] / (df['volume_mean_50'] + 1e-10)

        # Price returns
        df['return_1'] = df['close'].pct_change(1) * 100
        df['return_3'] = df['close'].pct_change(3) * 100
        df['return_5'] = df['close'].pct_change(5) * 100

        # High-low range
        df['hl_range_pct'] = (df['high'] - df['low']) / df['close'] * 100

        # Time features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        return df

    def create_labels(self, df: pd.DataFrame, look_ahead: int = 5,
                     target_profit: float = 0.003) -> pd.DataFrame:
        """
        Create labels based on future price movement
        Label = 1 if price rises >= target_profit within look_ahead candles
        """
        logger.info(f"Creating labels (look_ahead={look_ahead}, target={target_profit*100}%)")

        df['future_max'] = df['close'].rolling(window=look_ahead).max().shift(-look_ahead)
        df['future_return'] = (df['future_max'] - df['close']) / df['close']
        df['label'] = (df['future_return'] >= target_profit).astype(int)

        return df

    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and labels for training"""
        # Use same features as original model
        if self.feature_columns is None:
            raise ValueError("Feature columns not loaded from model")

        # Drop NaN rows
        df_clean = df.dropna(subset=self.feature_columns + ['label'])

        if len(df_clean) == 0:
            raise ValueError("No valid training samples after cleaning")

        X = df_clean[self.feature_columns].values
        y = df_clean['label'].values

        logger.info(f"Prepared {len(X)} training samples")
        logger.info(f"Positive class: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")
        logger.info(f"Negative class: {(~y.astype(bool)).sum()} ({(~y.astype(bool)).sum()/len(y)*100:.1f}%)")

        return X, y

    def update_model(self, X_new: np.ndarray, y_new: np.ndarray):
        """
        Update existing XGBoost model with new data
        Uses xgb_model parameter for warm start
        """
        logger.info("Updating model with new data...")

        # Train new estimators on top of existing model
        # XGBoost doesn't have true incremental learning, but we can:
        # 1. Use xgb_model to continue training
        # 2. Or retrain with new data combined

        # For true incremental learning, we continue training
        params = {
            'objective': 'binary:logistic',
            'max_depth': 7,
            'learning_rate': 0.02,  # Lower learning rate for fine-tuning
            'n_estimators': 100,     # Add 100 more trees
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'tree_method': 'hist',
            'eval_metric': 'logloss'
        }

        # Continue training from existing model
        new_model = xgb.XGBClassifier(**params)
        new_model.fit(
            X_new, y_new,
            xgb_model=self.model.get_booster(),  # Continue from existing model
            verbose=True
        )

        # Update model
        self.model = new_model

        # Evaluate on new data
        y_pred = self.model.predict(X_new)
        y_pred_proba = self.model.predict_proba(X_new)[:, 1]

        accuracy = accuracy_score(y_new, y_pred)
        precision = precision_score(y_new, y_pred, zero_division=0)
        recall = recall_score(y_new, y_pred, zero_division=0)
        f1 = f1_score(y_new, y_pred, zero_division=0)

        logger.info(f"Updated Model Performance on New Data:")
        logger.info(f"  Accuracy:  {accuracy:.4f}")
        logger.info(f"  Precision: {precision:.4f}")
        logger.info(f"  Recall:    {recall:.4f}")
        logger.info(f"  F1 Score:  {f1:.4f}")

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    def save_model(self, metrics: Dict):
        """Save updated model and metadata"""
        logger.info(f"Saving updated model to {self.model_path}")

        # Backup old model
        if os.path.exists(self.model_path):
            backup_path = self.model_path.replace('.pkl', f'_backup_{int(datetime.now().timestamp())}.pkl')
            os.rename(self.model_path, backup_path)
            logger.info(f"Backed up old model to {backup_path}")

        # Save new model
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'timestamp': datetime.now().isoformat()
        }

        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)

        # Save metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1': metrics['f1'],
            'incremental_update': True
        }

        metadata_path = self.model_path.replace('.pkl', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info("Model and metadata saved successfully")

    def run(self, session_id: str = None, all_sessions: bool = False,
            last_n_days: int = None):
        """Run complete incremental training pipeline"""
        logger.info("=" * 70)
        logger.info("STARTING INCREMENTAL TRAINING")
        logger.info("=" * 70)

        # Load existing model
        self.load_model()

        # Initialize exchange
        self.init_exchange()

        # Load trades
        trades = self.load_trade_log(session_id, all_sessions, last_n_days)

        if len(trades) == 0:
            logger.warning("No trades found for incremental learning")
            return

        # Fetch market data around trades
        df = self.fetch_trade_context_data(trades)

        if len(df) == 0:
            logger.error("No market data fetched. Cannot perform incremental learning.")
            return

        # Calculate indicators
        df = self.calculate_indicators(df)

        # Create labels
        df = self.create_labels(df)

        # Prepare training data
        X_new, y_new = self.prepare_training_data(df)

        # Update model
        metrics = self.update_model(X_new, y_new)

        # Save updated model
        self.save_model(metrics)

        logger.info("=" * 70)
        logger.info("INCREMENTAL TRAINING COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Incremental XGBoost Training')
    parser.add_argument('--session-id', type=str, help='Specific session ID to learn from')
    parser.add_argument('--all-sessions', action='store_true', help='Learn from all sessions')
    parser.add_argument('--last-n-days', type=int, help='Learn from trades in last N days')
    args = parser.parse_args()

    if not any([args.session_id, args.all_sessions, args.last_n_days]):
        print("Error: Must specify one of: --session-id, --all-sessions, or --last-n-days")
        sys.exit(1)

    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, 'models', 'xgb_5m.pkl')
    data_dir = os.path.join(script_dir, 'data')
    sessions_dir = os.path.join(script_dir, 'sessions')

    # Run incremental training
    trainer = IncrementalTrainer(model_path, data_dir, sessions_dir)
    trainer.run(
        session_id=args.session_id,
        all_sessions=args.all_sessions,
        last_n_days=args.last_n_days
    )


if __name__ == '__main__':
    main()
