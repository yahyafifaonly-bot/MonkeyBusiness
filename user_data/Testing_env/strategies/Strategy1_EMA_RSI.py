"""
Strategy 1: EMA + RSI Pullback Buy (IMPROVED VERSION)
Port: 8085

BACKTEST RESULTS (Relaxed): -89.9% loss, 9.7% win rate, 4395 trades
IMPROVEMENTS APPLIED: Tightened entry conditions for better quality trades

Entry Conditions (IMPROVED):
- Price > 9 EMA > 20 EMA (uptrend)
- RSI > 50 AND rising (IMPROVED: was >40)
- Price near 9 EMA (within 0.4% - IMPROVED: was 1%)
- 3 consecutive green candles above 9 EMA (IMPROVED: was 2)
- No 3 consecutive red candles below EMA (safety check)
- Volume confirmation added

Risk Management:
- Risk: 2% per trade
- Stop Loss: 2% below entry (IMPROVED: was 1.5% - less premature exits)
- Take Profit: 2.5-3% above entry
- R:R Ratio: ~1.5:1

Expected Improvements:
- Higher win rate (targeting 30-40% vs 9.7%)
- Fewer trades (targeting 50-100/day vs 146/day)
- Positive expectancy

Last Updated: 2025-10-25 - Improved parameters based on backtest analysis
Auto-backtest enabled - Results shown in GitHub Actions logs and saved to VPS
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd
import numpy as np

class Strategy1_EMA_RSI(IStrategy):
    INTERFACE_VERSION = 3

    # Strategy settings
    timeframe = '5m'
    can_short = False

    # Risk management (2% risk, 2% SL, 3% TP = 1.5:1 R:R)
    minimal_roi = {
        "0": 0.03,    # 3% take profit
        "20": 0.025,  # 2.5% after 20 min
        "40": 0.02    # 2% after 40 min
    }

    stoploss = -0.02  # -2% stop loss (reduced premature exits)

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01  # Start trailing at +1%
    trailing_stop_positive_offset = 0.015  # Trail by 1.5%
    trailing_only_offset_is_reached = True

    # Strategy parameters
    startup_candle_count = 200
    process_only_new_candles = True
    use_exit_signal = True

    # EMA distance threshold (tightened for better quality signals)
    max_ema_distance_pct = 0.4  # 0.4% max distance from 9 EMA (IMPROVED: was 1%)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate indicators"""

        # EMAs
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Volume
        dataframe['volume_sma_3'] = ta.SMA(dataframe['volume'], timeperiod=3)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma_3']

        # EMA slopes and distances
        dataframe['ema9_slope'] = dataframe['ema_9'].pct_change(3) * 100
        dataframe['distance_to_ema9'] = ((dataframe['close'] - dataframe['ema_9']) / dataframe['ema_9']) * 100

        # Count green/red candles
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)
        dataframe['close_above_ema9'] = (dataframe['close'] > dataframe['ema_9']).astype(int)
        dataframe['close_below_ema9'] = (dataframe['close'] < dataframe['ema_9']).astype(int)

        # Consecutive green candles above EMA9 (IMPROVED: 3 candles instead of 2)
        dataframe['green_above_ema9_count'] = 0
        for i in range(3, len(dataframe)):
            if all(dataframe['is_green'].iloc[i-j] == 1 and
                   dataframe['close_above_ema9'].iloc[i-j] == 1
                   for j in range(3)):
                dataframe.loc[dataframe.index[i], 'green_above_ema9_count'] = 3

        # Consecutive red candles below EMA9 (disable signal)
        dataframe['red_below_ema9_count'] = 0
        for i in range(3, len(dataframe)):
            if all(dataframe['is_red'].iloc[i-j] == 1 and
                   dataframe['close_below_ema9'].iloc[i-j] == 1
                   for j in range(3)):
                dataframe.loc[dataframe.index[i], 'red_below_ema9_count'] = 3

        # RSI rising
        dataframe['rsi_rising'] = (dataframe['rsi'] > dataframe['rsi'].shift(1)).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry conditions - IMPROVED from relaxed version"""

        dataframe.loc[
            (
                # Uptrend: price > 9 EMA > 20 EMA
                (dataframe['close'] > dataframe['ema_9']) &
                (dataframe['ema_9'] > dataframe['ema_20']) &

                # 9 EMA trending up (IMPROVED: stronger requirement)
                (dataframe['ema9_slope'] > 0.05) &

                # Price VERY near 9 EMA (IMPROVED: within 0.4% vs 1%)
                (abs(dataframe['distance_to_ema9']) <= self.max_ema_distance_pct) &

                # RSI > 50 AND rising (IMPROVED: was >40)
                (dataframe['rsi'] > 50) &
                (dataframe['rsi_rising'] == 1) &

                # 3 consecutive green candles above 9 EMA (IMPROVED: was 2)
                (dataframe['green_above_ema9_count'] >= 3) &

                # No 3 consecutive red candles below EMA recently
                (dataframe['red_below_ema9_count'].rolling(10).sum() == 0) &

                # Green candle with upward momentum
                (dataframe['close'] > dataframe['open']) &

                # Volume confirmation (IMPROVED: added volume ratio check)
                (dataframe['volume_ratio'] > 1.0) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit conditions"""

        dataframe.loc[
            (
                # Exit if RSI drops significantly
                (dataframe['rsi'] < 45) |

                # Exit if price crosses below 9 EMA with bearish candle
                ((dataframe['close'] < dataframe['ema_9']) & (dataframe['close'] < dataframe['open']))
            ),
            'exit_long'
        ] = 1

        return dataframe
