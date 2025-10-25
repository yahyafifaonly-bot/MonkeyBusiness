"""
Strategy 1: EMA + RSI Pullback Buy (Relaxed Version)
Port: 8085

Entry Conditions (RELAXED):
- Price > 9 EMA > 20 EMA (uptrend)
- RSI > 40 (relaxed from crossing 50)
- Price near 9 EMA (within 1% - relaxed from 0.2%)
- 2 consecutive green candles above 9 EMA (relaxed from 3)
- No 3 consecutive red candles below EMA (safety check)

Risk Management:
- Risk: 2% per trade
- Stop Loss: 1.5% below entry
- Take Profit: 2-3% above entry
- R:R Ratio: ~2:1

Last Updated: 2025-10-25 - Relaxed entry conditions for more trades
Auto-backtest enabled - Check GitHub Actions for results
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

    # Risk management (2% risk, 1.5% SL, 3% TP = 2:1 R:R)
    minimal_roi = {
        "0": 0.03,  # 3% take profit
        "15": 0.025,  # 2.5% after 15 min
        "30": 0.02   # 2% after 30 min
    }

    stoploss = -0.015  # -1.5% stop loss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01  # Start trailing at +1%
    trailing_stop_positive_offset = 0.015  # Trail by 1.5%
    trailing_only_offset_is_reached = True

    # Strategy parameters
    startup_candle_count = 200
    process_only_new_candles = True
    use_exit_signal = True

    # EMA distance threshold (relaxed for more trade opportunities)
    max_ema_distance_pct = 1.0  # 1% max distance from 9 EMA

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate indicators"""

        # EMAs
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Volume
        dataframe['volume_sma_3'] = ta.SMA(dataframe['volume'], timeperiod=3)

        # EMA slopes and distances
        dataframe['ema9_slope'] = dataframe['ema_9'].pct_change(3) * 100
        dataframe['distance_to_ema9'] = ((dataframe['close'] - dataframe['ema_9']) / dataframe['ema_9']) * 100

        # Count green/red candles
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)
        dataframe['close_above_ema9'] = (dataframe['close'] > dataframe['ema_9']).astype(int)
        dataframe['close_below_ema9'] = (dataframe['close'] < dataframe['ema_9']).astype(int)

        # Consecutive green candles above EMA9
        dataframe['green_above_ema9_count'] = 0
        for i in range(2, len(dataframe)):
            if all(dataframe['is_green'].iloc[i-j] == 1 and
                   dataframe['close_above_ema9'].iloc[i-j] == 1
                   for j in range(2)):
                dataframe.loc[dataframe.index[i], 'green_above_ema9_count'] = 2

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
        """Entry conditions"""

        dataframe.loc[
            (
                # Uptrend: price > 9 EMA > 20 EMA
                (dataframe['close'] > dataframe['ema_9']) &
                (dataframe['ema_9'] > dataframe['ema_20']) &

                # 9 EMA trending up
                (dataframe['ema9_slope'] > 0) &

                # Price near 9 EMA (within 1% - relaxed)
                (abs(dataframe['distance_to_ema9']) <= self.max_ema_distance_pct) &

                # RSI > 40 (relaxed from crossing 50)
                (dataframe['rsi'] > 40) &

                # RSI rising
                (dataframe['rsi_rising'] == 1) &

                # 2 consecutive green candles above 9 EMA (relaxed from 3)
                (dataframe['green_above_ema9_count'] >= 2) &

                # No 3 consecutive red candles below EMA recently
                (dataframe['red_below_ema9_count'].rolling(10).sum() == 0) &

                # Green candle with upward momentum
                (dataframe['close'] > dataframe['open']) &

                # Volume > 0
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
                (dataframe['rsi'] < 40) |

                # Exit if price crosses below 9 EMA
                (dataframe['close'] < dataframe['ema_9'])
            ),
            'exit_long'
        ] = 1

        return dataframe
