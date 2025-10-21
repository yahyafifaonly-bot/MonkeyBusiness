"""
XGBScalp5m - XGBoost-based High-Frequency 5-Minute Scalping Strategy

Features:
- ML predictions using pre-trained XGBoost model
- Dynamic stake sizing based on model confidence (0.62-0.78+ probability)
- 3-hour trading sessions with auto-shutdown
- Session performance reporting
- Trade logging for incremental learning
- Protection against consecutive losses
"""

from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import pandas as pd
import numpy as np
import talib as ta
import pickle
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
import json

logger = logging.getLogger(__name__)


class XGBScalp5m(IStrategy):
    """
    XGBoost 5-Minute High-Frequency Scalping Strategy

    Entry: XGBoost probability >= 0.62
    Stake Sizing:
        - 0.62-0.70: $10
        - 0.70-0.78: $20
        - 0.78+: $50

    Exit: Take-profit +0.4%, Stop-loss -0.6%, Trailing stop after +0.25%
    Session: 3 hours max, then auto-stop with report
    """

    INTERFACE_VERSION = 3

    # Strategy parameters
    timeframe = '5m'
    can_short = False

    # ROI and stoploss
    minimal_roi = {
        "0": 0.004  # 0.4% take profit
    }

    stoploss = -0.006  # -0.6% stop loss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.0025  # Start trailing at +0.25%
    trailing_stop_positive_offset = 0.003  # Trail by 0.3%
    trailing_only_offset_is_reached = True

    # Strategy settings
    startup_candle_count = 200
    process_only_new_candles = True
    use_exit_signal = True

    # XGBoost settings
    min_probability = 0.62  # Minimum confidence to enter trade

    # Dynamic stake sizing thresholds
    stake_low = 10  # $10 for prob 0.62-0.70
    stake_mid = 20  # $20 for prob 0.70-0.78
    stake_high = 50  # $50 for prob 0.78+

    prob_mid_threshold = 0.70
    prob_high_threshold = 0.78

    # Session management
    session_duration_hours = 3
    session_start_time = None
    session_trades = []
    consecutive_losses = 0
    max_consecutive_losses = 10

    # Model
    model = None
    feature_names = None
    model_loaded = False

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.load_model()
        self.session_start_time = datetime.now(timezone.utc)
        logger.info(f"=== XGBScalp5m Strategy Initialized ===")
        logger.info(f"Session start: {self.session_start_time}")
        logger.info(f"Session duration: {self.session_duration_hours} hours")
        logger.info(f"Min probability: {self.min_probability}")

    def load_model(self):
        """Load the trained XGBoost model"""
        model_path = Path('user_data/xgb_5m/models/xgb_5m_latest.pkl')

        if not model_path.exists():
            logger.error(f"Model not found: {model_path}")
            logger.error("Please train the model first using: python user_data/xgb_5m/train_xgb_5m.py")
            return False

        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.feature_names = model_data['feature_names']

            logger.info(f"✓ Model loaded successfully from {model_path}")
            logger.info(f"  Features: {len(self.feature_names)}")
            logger.info(f"  Metrics: {model_data.get('training_metrics', {})}")
            self.model_loaded = True
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all technical indicators (same as training)"""

        if not self.model_loaded:
            logger.warning("Model not loaded, returning empty indicators")
            return dataframe

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe['close'], timeperiod=7)
        dataframe['rsi_slow'] = ta.RSI(dataframe['close'], timeperiod=21)

        # MACD
        macd, signal, hist = ta.MACD(dataframe['close'])
        dataframe['macd'] = macd
        dataframe['macd_signal'] = signal
        dataframe['macd_hist'] = hist
        dataframe['macd_hist_pct'] = dataframe['macd_hist'] / dataframe['close'] * 100

        # EMAs
        dataframe['ema_9'] = ta.EMA(dataframe['close'], timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe['close'], timeperiod=21)
        dataframe['ema_50'] = ta.EMA(dataframe['close'], timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)

        # EMA slopes
        dataframe['ema9_slope'] = dataframe['ema_9'].pct_change(3) * 100
        dataframe['ema21_slope'] = dataframe['ema_21'].pct_change(3) * 100
        dataframe['ema50_slope'] = dataframe['ema_50'].pct_change(5) * 100

        # EMA crossovers
        dataframe['ema9_vs_21'] = (dataframe['ema_9'] - dataframe['ema_21']) / dataframe['ema_21'] * 100
        dataframe['ema9_vs_50'] = (dataframe['ema_9'] - dataframe['ema_50']) / dataframe['ema_50'] * 100

        # Bollinger Bands
        upper, middle, lower = ta.BBANDS(dataframe['close'], timeperiod=20)
        dataframe['bb_upper'] = upper
        dataframe['bb_middle'] = middle
        dataframe['bb_lower'] = lower
        dataframe['bb_percent'] = (dataframe['close'] - lower) / (upper - lower)
        dataframe['bb_width'] = (upper - lower) / middle

        # ATR
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100

        # Volume
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']

        dataframe['volume_mean_50'] = dataframe['volume'].rolling(50).mean()
        dataframe['volume_std_50'] = dataframe['volume'].rolling(50).std()
        dataframe['volume_zscore'] = (dataframe['volume'] - dataframe['volume_mean_50']) / dataframe['volume_std_50']

        # Returns
        dataframe['return_1'] = dataframe['close'].pct_change(1) * 100
        dataframe['return_3'] = dataframe['close'].pct_change(3) * 100
        dataframe['return_5'] = dataframe['close'].pct_change(5) * 100
        dataframe['return_10'] = dataframe['close'].pct_change(10) * 100

        # Price ranges
        dataframe['high_low_pct'] = (dataframe['high'] - dataframe['low']) / dataframe['low'] * 100
        dataframe['close_open_pct'] = (dataframe['close'] - dataframe['open']) / dataframe['open'] * 100

        # ADX
        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        # MFI
        dataframe['mfi'] = ta.MFI(dataframe['high'], dataframe['low'], dataframe['close'], dataframe['volume'], timeperiod=14)

        # Williams %R
        dataframe['willr'] = ta.WILLR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        # Time features
        dataframe['hour'] = pd.to_datetime(dataframe['date']).dt.hour
        dataframe['hour_sin'] = np.sin(2 * np.pi * dataframe['hour'] / 24)
        dataframe['hour_cos'] = np.cos(2 * np.pi * dataframe['hour'] / 24)
        dataframe['day_of_week'] = pd.to_datetime(dataframe['date']).dt.dayofweek
        dataframe['dow_sin'] = np.sin(2 * np.pi * dataframe['day_of_week'] / 7)
        dataframe['dow_cos'] = np.cos(2 * np.pi * dataframe['day_of_week'] / 7)

        # ML Prediction
        dataframe = self.add_ml_predictions(dataframe)

        return dataframe

    def add_ml_predictions(self, dataframe: DataFrame) -> DataFrame:
        """Add XGBoost predictions to dataframe"""
        if not self.model_loaded or self.model is None:
            dataframe['ml_probability'] = 0
            dataframe['ml_predict'] = 0
            return dataframe

        try:
            # Prepare features (must match training exactly)
            df_features = dataframe[self.feature_names].copy()

            # Handle NaN values
            df_features = df_features.fillna(0)

            # Predict probabilities
            probabilities = self.model.predict_proba(df_features)[:, 1]
            predictions = (probabilities >= self.min_probability).astype(int)

            dataframe['ml_probability'] = probabilities
            dataframe['ml_predict'] = predictions

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            dataframe['ml_probability'] = 0
            dataframe['ml_predict'] = 0

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry signal based on ML predictions"""

        # Check session time limit
        if self.is_session_expired():
            logger.info("Session expired - no new entries")
            return dataframe

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            logger.warning(f"Max consecutive losses reached ({self.consecutive_losses}) - stopping entries")
            return dataframe

        dataframe.loc[
            (
                (dataframe['ml_probability'] >= self.min_probability) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit signals (mainly using ROI/stoploss, but can add ML-based exits)"""
        dataframe.loc[
            (
                (dataframe['ml_probability'] < 0.40)  # Exit if confidence drops significantly
            ),
            'exit_long'
        ] = 1

        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                          proposed_stake: float, min_stake: Optional[float], max_stake: float,
                          leverage: float, entry_tag: Optional[str], side: str,
                          **kwargs) -> float:
        """
        Dynamic stake sizing based on ML confidence:
        - 0.62-0.70: $10
        - 0.70-0.78: $20
        - 0.78+: $50
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return self.stake_low

        last_candle = dataframe.iloc[-1]
        probability = last_candle.get('ml_probability', 0)

        if probability >= self.prob_high_threshold:
            stake = self.stake_high
            logger.info(f"HIGH confidence ({probability:.3f}) → ${stake}")
        elif probability >= self.prob_mid_threshold:
            stake = self.stake_mid
            logger.info(f"MEDIUM confidence ({probability:.3f}) → ${stake}")
        else:
            stake = self.stake_low
            logger.info(f"LOW confidence ({probability:.3f}) → ${stake}")

        return stake

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                          side: str, **kwargs) -> bool:
        """Final check before entering trade"""

        # Check session time
        if self.is_session_expired():
            logger.info(f"Session expired - rejecting entry for {pair}")
            return False

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            logger.warning(f"Max losses reached - rejecting entry for {pair}")
            return False

        return True

    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float,
                         rate: float, time_in_force: str, exit_reason: str,
                         current_time: datetime, **kwargs) -> bool:
        """Track trade performance and update consecutive losses"""

        profit_pct = trade.calc_profit_ratio(rate) * 100

        # Log trade for incremental learning
        self.log_trade(pair, trade, profit_pct, exit_reason)

        # Update consecutive losses counter
        if profit_pct < 0:
            self.consecutive_losses += 1
            logger.warning(f"Loss #{self.consecutive_losses}: {pair} {profit_pct:.2f}%")
        else:
            self.consecutive_losses = 0
            logger.info(f"Win: {pair} +{profit_pct:.2f}% (reset loss counter)")

        return True

    def log_trade(self, pair: str, trade, profit_pct: float, exit_reason: str):
        """Log trade details for session report and incremental learning"""
        trade_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'pair': pair,
            'entry_price': trade.open_rate,
            'exit_price': trade.close_rate,
            'profit_pct': profit_pct,
            'profit_abs': trade.close_profit,
            'exit_reason': exit_reason,
            'duration_minutes': (trade.close_date_utc - trade.open_date_utc).total_seconds() / 60
        }

        self.session_trades.append(trade_data)

        # Save to file for incremental learning
        session_log_path = Path('user_data/xgb_5m/sessions/trades.jsonl')
        session_log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(session_log_path, 'a') as f:
            f.write(json.dumps(trade_data) + '\n')

    def is_session_expired(self) -> bool:
        """Check if trading session has exceeded time limit"""
        if self.session_start_time is None:
            return False

        elapsed_hours = (datetime.now(timezone.utc) - self.session_start_time).total_seconds() / 3600

        if elapsed_hours >= self.session_duration_hours:
            if not hasattr(self, '_session_expired_logged'):
                self.print_session_report()
                self._session_expired_logged = True
            return True

        return False

    def print_session_report(self):
        """Print comprehensive session performance report"""
        logger.info("\n" + "=" * 80)
        logger.info("  XGB 5-MINUTE SCALPING - SESSION REPORT")
        logger.info("=" * 80)

        logger.info(f"\nSession Duration: {self.session_duration_hours} hours")
        logger.info(f"Start Time: {self.session_start_time}")
        logger.info(f"End Time: {datetime.now(timezone.utc)}")

        if not self.session_trades:
            logger.info("\nNo trades executed this session.")
            logger.info("=" * 80 + "\n")
            return

        # Calculate metrics
        total_trades = len(self.session_trades)
        winning_trades = [t for t in self.session_trades if t['profit_pct'] > 0]
        losing_trades = [t for t in self.session_trades if t['profit_pct'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        total_profit = sum(t['profit_pct'] for t in self.session_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0

        avg_win = sum(t['profit_pct'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['profit_pct'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        # Print report
        logger.info(f"\n📊 PERFORMANCE METRICS")
        logger.info(f"  Total Trades: {total_trades}")
        logger.info(f"  Winning Trades: {len(winning_trades)}")
        logger.info(f"  Losing Trades: {len(losing_trades)}")
        logger.info(f"  Win Rate: {win_rate:.2f}%")
        logger.info(f"\n💰 PROFIT/LOSS")
        logger.info(f"  Total P&L: {total_profit:.2f}%")
        logger.info(f"  Average P&L: {avg_profit:.2f}%")
        logger.info(f"  Average Win: +{avg_win:.2f}%")
        logger.info(f"  Average Loss: {avg_loss:.2f}%")
        logger.info(f"  Risk/Reward: {abs(avg_win / avg_loss) if avg_loss != 0 else 0:.2f}")

        logger.info(f"\n📈 BEST/WORST TRADES")
        best_trade = max(self.session_trades, key=lambda x: x['profit_pct'])
        worst_trade = min(self.session_trades, key=lambda x: x['profit_pct'])
        logger.info(f"  Best: {best_trade['pair']} +{best_trade['profit_pct']:.2f}%")
        logger.info(f"  Worst: {worst_trade['pair']} {worst_trade['profit_pct']:.2f}%")

        logger.info("\n" + "=" * 80)
        logger.info("  Session ended. Ready for manual restart.")
        logger.info("=" * 80 + "\n")

        # Save report to file
        report_path = Path(f"user_data/xgb_5m/sessions/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            f.write("XGB 5-Minute Scalping Session Report\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Trades: {total_trades}\n")
            f.write(f"Win Rate: {win_rate:.2f}%\n")
            f.write(f"Total P&L: {total_profit:.2f}%\n")
            f.write(f"Average P&L: {avg_profit:.2f}%\n")

        logger.info(f"Report saved to: {report_path}")
