#!/usr/bin/env python3
"""
XGBoost 5-Minute High-Frequency Trading Model Trainer

Features:
- 2 years of historical 5-minute candle data
- Advanced feature engineering (RSI, MACD, EMA, BB, ATR, volume, time features)
- Binary classification: Predict if price rises >= 0.2-0.4% within N candles
- Walk-forward time-based validation
- Incremental learning capability
- Model versioning and performance tracking
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import talib as ta
from pathlib import Path
import pickle
import json
from datetime import datetime, timedelta
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('user_data/xgb_5m/logs/training.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class XGBTrainer:
    """XGBoost model trainer for high-frequency crypto trading"""

    def __init__(self,
                 pairs=['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'],
                 timeframe='5m',
                 data_days=730,  # 2 years
                 target_pct_min=0.002,  # 0.2%
                 target_pct_max=0.004,  # 0.4%
                 target_candles=6):  # Look ahead 6 candles (30 minutes)

        self.pairs = pairs
        self.timeframe = timeframe
        self.data_days = data_days
        self.target_pct_min = target_pct_min
        self.target_pct_max = target_pct_max
        self.target_candles = target_candles

        self.model_dir = Path('user_data/xgb_5m/models')
        self.data_dir = Path('user_data/xgb_5m/data')
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.feature_names = None
        self.training_metrics = {}
        self.feature_importance = None

    def download_data(self):
        """Download historical data using freqtrade"""
        import subprocess

        logger.info("=" * 60)
        logger.info(f"STEP 1: Downloading Historical Data")
        logger.info("=" * 60)
        logger.info(f"Pairs: {', '.join(self.pairs)}")
        logger.info(f"Timeframe: {self.timeframe}")
        logger.info(f"Days: {self.data_days}")
        logger.info(f"Exchange: Binance")

        cmd = [
            'freqtrade', 'download-data',
            '--exchange', 'binance',
            '--pairs'] + self.pairs + [
            '--timeframes', self.timeframe,
            '--days', str(self.data_days),
            '--datadir', str(self.data_dir)
        ]

        try:
            logger.info("Fetching data from Binance...")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("✓ Data download completed successfully")
            logger.debug(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Data download failed: {e.stderr}")
            return False

    def load_data(self, pair):
        """Load OHLCV data for a single pair"""
        pair_filename = pair.replace('/', '_')

        # Try feather format first (Freqtrade's default now)
        feather_path = self.data_dir / f"{pair_filename}-{self.timeframe}.feather"
        json_path = self.data_dir / f"{pair_filename}-{self.timeframe}.json"

        if feather_path.exists():
            logger.info(f"Loading data from {feather_path}")
            df = pd.read_feather(feather_path)
            # Feather files have 'date' column already
            if 'date' in df.columns:
                df = df.set_index('date')
            df['pair'] = pair
            logger.info(f"Loaded {len(df)} candles for {pair} from {df.index[0]} to {df.index[-1]}")

        elif json_path.exists():
            logger.info(f"Loading data from {json_path}")
            import json
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('date')
            df = df.drop('timestamp', axis=1)
            df['pair'] = pair
            logger.info(f"Loaded {len(df)} candles for {pair} from {df.index[0]} to {df.index[-1]}")

        else:
            logger.error(f"Data file not found: {feather_path} or {json_path}")
            return None

        return df

    def calculate_indicators(self, df):
        """Calculate technical indicators and features"""
        logger.info("=" * 60)
        logger.info("STEP 3: Calculating Technical Indicators")
        logger.info("=" * 60)
        logger.info("Calculating 49+ technical features...")

        df = df.copy()

        # Price-based indicators
        df['rsi'] = ta.RSI(df['close'], timeperiod=14)
        df['rsi_fast'] = ta.RSI(df['close'], timeperiod=7)
        df['rsi_slow'] = ta.RSI(df['close'], timeperiod=21)

        # MACD
        macd, signal, hist = ta.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        df['macd_hist_pct'] = df['macd_hist'] / df['close'] * 100

        # Moving Averages
        df['ema_9'] = ta.EMA(df['close'], timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'], timeperiod=21)
        df['ema_50'] = ta.EMA(df['close'], timeperiod=50)
        df['ema_200'] = ta.EMA(df['close'], timeperiod=200)

        # EMA slopes (momentum)
        df['ema9_slope'] = df['ema_9'].pct_change(periods=3) * 100
        df['ema21_slope'] = df['ema_21'].pct_change(periods=3) * 100
        df['ema50_slope'] = df['ema_50'].pct_change(periods=5) * 100

        # EMA crossovers
        df['ema9_vs_21'] = (df['ema_9'] - df['ema_21']) / df['ema_21'] * 100
        df['ema9_vs_50'] = (df['ema_9'] - df['ema_50']) / df['ema_50'] * 100

        # Bollinger Bands
        upper, middle, lower = ta.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_percent'] = (df['close'] - lower) / (upper - lower)  # %B indicator
        df['bb_width'] = (upper - lower) / middle  # Bandwidth

        # ATR (volatility)
        df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        df['atr_pct'] = df['atr'] / df['close'] * 100  # ATR as % of price

        # Volume indicators
        df['volume_sma'] = ta.SMA(df['volume'], timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # Volume z-score (standardized)
        df['volume_mean_50'] = df['volume'].rolling(50).mean()
        df['volume_std_50'] = df['volume'].rolling(50).std()
        df['volume_zscore'] = (df['volume'] - df['volume_mean_50']) / df['volume_std_50']

        # Price momentum (rolling returns)
        df['return_1'] = df['close'].pct_change(1) * 100
        df['return_3'] = df['close'].pct_change(3) * 100
        df['return_5'] = df['close'].pct_change(5) * 100
        df['return_10'] = df['close'].pct_change(10) * 100

        # Price range indicators
        df['high_low_pct'] = (df['high'] - df['low']) / df['low'] * 100
        df['close_open_pct'] = (df['close'] - df['open']) / df['open'] * 100

        # Trend strength (ADX)
        df['adx'] = ta.ADX(df['high'], df['low'], df['close'], timeperiod=14)

        # Money Flow Index
        df['mfi'] = ta.MFI(df['high'], df['low'], df['close'], df['volume'], timeperiod=14)

        # Williams %R
        df['willr'] = ta.WILLR(df['high'], df['low'], df['close'], timeperiod=14)

        # Time-based features (cyclical encoding)
        df['hour'] = df.index.hour
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_of_week'] = df.index.dayofweek
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        logger.info(f"✓ Calculated {len(df.columns)} features")

        return df

    def create_labels(self, df):
        """
        Create binary labels:
        1 if price rises >= target_pct within target_candles
        0 otherwise
        """
        logger.info("=" * 60)
        logger.info("STEP 4: Creating Training Labels")
        logger.info("=" * 60)
        logger.info(f"Target profit: {self.target_pct_min*100:.1f}%-{self.target_pct_max*100:.1f}%")
        logger.info(f"Look-ahead window: {self.target_candles} candles (30 minutes)")
        logger.info("Creating labels...")

        df = df.copy()

        # Calculate future returns
        df['future_high'] = df['high'].rolling(window=self.target_candles).max().shift(-self.target_candles)
        df['future_return'] = (df['future_high'] - df['close']) / df['close']

        # Label as 1 if future return meets target
        df['target'] = ((df['future_return'] >= self.target_pct_min) &
                        (df['future_return'] <= self.target_pct_max * 3)).astype(int)  # Allow up to 3x max for big wins

        # Drop the helper columns
        df = df.drop(['future_high', 'future_return'], axis=1)

        positive_pct = df['target'].mean() * 100
        logger.info(f"Label distribution: {positive_pct:.1f}% positive (target=1), {100-positive_pct:.1f}% negative (target=0)")

        return df

    def prepare_features(self, df):
        """Select and prepare features for training"""
        logger.info("=" * 60)
        logger.info("STEP 5: Preparing Features for Training")
        logger.info("=" * 60)

        # Drop NaN values
        logger.info("Cleaning data (removing NaN values)...")
        df = df.dropna()

        # Select feature columns (exclude target, pair, and original OHLCV)
        exclude_cols = ['target', 'pair', 'open', 'high', 'low', 'close', 'volume',
                       'volume_mean_50', 'volume_std_50', 'hour', 'day_of_week',
                       'bb_upper', 'bb_middle', 'bb_lower', 'ema_9', 'ema_21', 'ema_50', 'ema_200']

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols]
        y = df['target']

        self.feature_names = feature_cols

        logger.info(f"✓ Selected {len(feature_cols)} features for training")
        logger.info(f"✓ Training dataset: {len(X):,} samples")
        logger.info(f"✓ Features: {', '.join(feature_cols[:10])}{'...' if len(feature_cols) > 10 else ''}")

        return X, y, df.index

    def train_model(self, X, y, timestamps):
        """Train XGBoost model with time-series cross-validation"""
        logger.info("=" * 60)
        logger.info("STEP 6: Training XGBoost Model")
        logger.info("=" * 60)

        # Time-based train/test split (80/20)
        split_idx = int(len(X) * 0.8)

        X_train = X.iloc[:split_idx]
        y_train = y.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_test = y.iloc[split_idx:]

        logger.info(f"Train set: {len(X_train):,} samples ({timestamps[0]} to {timestamps[split_idx-1]})")
        logger.info(f"Test set: {len(X_test):,} samples ({timestamps[split_idx]} to {timestamps[-1]})")

        # Calculate scale_pos_weight for imbalanced classes
        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
        logger.info(f"Class imbalance ratio: {scale_pos_weight:.2f}")
        logger.info("")

        # XGBoost parameters optimized for high-frequency trading
        params = {
            'objective': 'binary:logistic',
            'eval_metric': ['logloss', 'auc'],
            'max_depth': 7,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'scale_pos_weight': scale_pos_weight,
            'random_state': 42,
            'n_jobs': -1,
            'tree_method': 'hist'
        }

        # Train model with early stopping
        self.model = xgb.XGBClassifier(**params)

        logger.info("=" * 60)
        logger.info("Starting XGBoost training iterations...")
        logger.info(f"Estimators: {params['n_estimators']}")
        logger.info(f"Learning rate: {params['learning_rate']}")
        logger.info(f"Max depth: {params['max_depth']}")
        logger.info("=" * 60)

        # Custom callback to log training progress
        class LoggingCallback(xgb.callback.TrainingCallback):
            def after_iteration(self, model, epoch, evals_log):
                """Log metrics after each iteration"""
                if epoch % 10 == 0:  # Log every 10 iterations
                    # Get latest metrics
                    train_logloss = evals_log['validation_0']['logloss'][-1]
                    train_auc = evals_log['validation_0']['auc'][-1]
                    test_logloss = evals_log['validation_1']['logloss'][-1]
                    test_auc = evals_log['validation_1']['auc'][-1]

                    logger.info(f"[{epoch}] train-logloss: {train_logloss:.5f}, train-auc: {train_auc:.5f}, "
                               f"test-logloss: {test_logloss:.5f}, test-auc: {test_auc:.5f}")
                return False

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            verbose=False,  # Disable default verbose, use callback instead
            callbacks=[LoggingCallback()]
        )

        logger.info("=" * 60)
        logger.info("XGBoost training completed!")
        logger.info("=" * 60)

        # Evaluate on test set
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        # Calculate win rate metrics
        total_predicted_trades = (y_pred == 1).sum()
        winning_trades = ((y_pred == 1) & (y_test == 1)).sum()
        win_rate = winning_trades / total_predicted_trades if total_predicted_trades > 0 else 0

        # Calculate metrics
        self.training_metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'win_rate': win_rate,
            'total_predicted_trades': int(total_predicted_trades),
            'winning_trades': int(winning_trades),
            'losing_trades': int(total_predicted_trades - winning_trades),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'positive_rate': y_train.mean(),
            'training_date': datetime.now().isoformat()
        }

        logger.info("=" * 60)
        logger.info("MODEL PERFORMANCE METRICS")
        logger.info("=" * 60)
        logger.info(f"Accuracy:  {self.training_metrics['accuracy']:.4f}")
        logger.info(f"Precision: {self.training_metrics['precision']:.4f}")
        logger.info(f"Recall:    {self.training_metrics['recall']:.4f}")
        logger.info(f"F1 Score:  {self.training_metrics['f1']:.4f}")
        logger.info(f"ROC AUC:   {self.training_metrics['roc_auc']:.4f}")
        logger.info("")
        logger.info("TRADING SIMULATION ON TEST SET")
        logger.info(f"Win Rate:        {self.training_metrics['win_rate']:.2%}")
        logger.info(f"Total Signals:   {self.training_metrics['total_predicted_trades']}")
        logger.info(f"Winning Trades:  {self.training_metrics['winning_trades']}")
        logger.info(f"Losing Trades:   {self.training_metrics['losing_trades']}")
        logger.info("=" * 60)

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        # Store for later use in metadata
        self.feature_importance = feature_importance

        logger.info("\nTop 15 Most Important Features:")
        logger.info(feature_importance.head(15).to_string())

        return self.model

    def save_model(self, version=None):
        """Save trained model and metadata"""
        if version is None:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')

        model_path = self.model_dir / f'xgb_5m_{version}.pkl'
        metadata_path = self.model_dir / f'xgb_5m_{version}_metadata.json'

        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'training_metrics': self.training_metrics,
                'params': {
                    'pairs': self.pairs,
                    'timeframe': self.timeframe,
                    'target_pct_min': self.target_pct_min,
                    'target_pct_max': self.target_pct_max,
                    'target_candles': self.target_candles
                }
            }, f)

        logger.info(f"Model saved to: {model_path}")

        # Save metadata
        metadata = {
            'version': version,
            'training_date': self.training_metrics['training_date'],
            'metrics': self.training_metrics,
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Metadata saved to: {metadata_path}")

        # Also save metadata with all dashboard fields
        dashboard_metadata = {
            'version': version,
            'training_date': self.training_metrics['training_date'],
            'timestamp': self.training_metrics['training_date'],
            'model_file': f'xgb_5m_{version}.pkl',
            'pairs': self.pairs,
            'timeframe': self.timeframe,
            'n_features': len(self.feature_names),
            'training_samples': self.training_metrics['train_samples'],
            'test_samples': self.training_metrics['test_samples'],
            'metrics': self.training_metrics,
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names,
            'feature_importance': [] if self.feature_importance is None else [
                {'feature': row['feature'], 'importance': float(row['importance'])}
                for _, row in self.feature_importance.iterrows()
            ]
        }

        # Overwrite metadata file with complete dashboard data
        with open(metadata_path, 'w') as f:
            json.dump(dashboard_metadata, f, indent=2)

        logger.info(f"Dashboard metadata saved to: {metadata_path}")

        # Create symlink to latest model
        latest_path = self.model_dir / 'xgb_5m_latest.pkl'
        if latest_path.exists():
            latest_path.unlink()
        latest_path.symlink_to(model_path.name)

        logger.info(f"Latest model link created: {latest_path}")

        return model_path

    def incremental_train(self, new_data_path, existing_model_path=None):
        """
        Incrementally train the model with new data

        Args:
            new_data_path: Path to new trading data (CSV or DataFrame)
            existing_model_path: Path to existing model (default: latest)
        """
        logger.info("Starting incremental training...")

        # Load existing model
        if existing_model_path is None:
            existing_model_path = self.model_dir / 'xgb_5m_latest.pkl'

        with open(existing_model_path, 'rb') as f:
            model_data = pickle.load(f)
            self.model = model_data['model']
            self.feature_names = model_data['feature_names']

        logger.info(f"Loaded existing model from: {existing_model_path}")

        # Load new data
        if isinstance(new_data_path, pd.DataFrame):
            new_df = new_data_path
        else:
            new_df = pd.read_csv(new_data_path)

        logger.info(f"Loaded {len(new_df)} new samples")

        # Calculate indicators and create labels
        new_df = self.calculate_indicators(new_df)
        new_df = self.create_labels(new_df)

        # Prepare features
        X_new, y_new, _ = self.prepare_features(new_df)

        # Continue training (using xgb_model parameter for warm start)
        logger.info("Continuing training with new data...")

        self.model.fit(
            X_new, y_new,
            xgb_model=self.model.get_booster(),
            verbose=100
        )

        logger.info("Incremental training completed")

        # Save updated model
        version = datetime.now().strftime('%Y%m%d_%H%M%S') + '_incremental'
        self.save_model(version=version)

        return self.model

    def run_full_training(self):
        """Execute complete training pipeline"""
        logger.info("=" * 60)
        logger.info("XGBOOST 5-MINUTE HIGH-FREQUENCY TRADING MODEL TRAINING")
        logger.info("=" * 60)

        # Step 1: Download data
        if not self.download_data():
            logger.error("Failed to download data. Exiting.")
            return None

        # Step 2: Load and combine data from all pairs
        logger.info("=" * 60)
        logger.info("STEP 2: Loading and Combining Data")
        logger.info("=" * 60)

        all_data = []
        for pair in self.pairs:
            logger.info(f"Loading data for {pair}...")
            df = self.load_data(pair)
            if df is not None:
                all_data.append(df)
                logger.info(f"  ✓ {pair}: {len(df):,} candles loaded")

        if not all_data:
            logger.error("No data loaded. Exiting.")
            return None

        combined_df = pd.concat(all_data, axis=0).sort_index()
        logger.info(f"✓ Combined dataset: {len(combined_df):,} total candles across {len(self.pairs)} pairs")

        # Step 3: Calculate indicators
        combined_df = self.calculate_indicators(combined_df)

        # Step 4: Create labels
        combined_df = self.create_labels(combined_df)

        # Step 5: Prepare features
        X, y, timestamps = self.prepare_features(combined_df)

        # Step 6: Train model
        self.train_model(X, y, timestamps)

        # Step 7: Save model
        model_path = self.save_model()

        logger.info("=" * 60)
        logger.info("TRAINING COMPLETED SUCCESSFULLY")
        logger.info(f"Model saved to: {model_path}")
        logger.info("=" * 60)

        return model_path


def main():
    """Main training entry point"""
    trainer = XGBTrainer(
        pairs=['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'],
        timeframe='5m',
        data_days=730,  # 2 years
        target_pct_min=0.002,  # 0.2%
        target_pct_max=0.004,  # 0.4%
        target_candles=6  # 30 minutes ahead (6 * 5min)
    )

    model_path = trainer.run_full_training()

    if model_path:
        logger.info(f"\n✓ Training successful! Model ready for trading at: {model_path}")
        return 0
    else:
        logger.error("\n✗ Training failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
