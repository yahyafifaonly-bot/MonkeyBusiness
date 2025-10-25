"""
Strategy 5: Controlled Breakout Hugging EMA
Port: 8089

Entry Conditions:
- 3 green closes above 9 EMA
- Current candle breaks 2-bar high
- Still near 9 EMA (distance ≤ 0.2%)
- RSI = 50-68 and rising
- Volume ≥ 150% of average

Risk Management:
- Stop Loss: 1-1.5%
- Take Profit: 2-3%
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class Strategy5_Breakout_EMA(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = '5m'
    can_short = False

    minimal_roi = {
        "0": 0.03,
        "15": 0.025,
        "30": 0.02
    }

    stoploss = -0.015

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    startup_candle_count = 200
    process_only_new_candles = True
    use_exit_signal = True

    max_ema_distance_pct = 0.2

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMAs
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Volume
        dataframe['volume_sma_20'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_sma_3'] = ta.SMA(dataframe['volume'], timeperiod=3)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma_20']

        # EMA analysis
        dataframe['ema9_slope'] = dataframe['ema_9'].pct_change(3) * 100
        dataframe['distance_to_ema9'] = ((dataframe['close'] - dataframe['ema_9']) / dataframe['ema_9']) * 100

        # Candle patterns
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)
        dataframe['close_above_ema9'] = (dataframe['close'] > dataframe['ema_9']).astype(int)
        dataframe['close_below_ema9'] = (dataframe['close'] < dataframe['ema_9']).astype(int)

        # Consecutive counts
        dataframe['green_above_ema9_count'] = 0
        dataframe['red_below_ema9_count'] = 0

        for i in range(3, len(dataframe)):
            if all(dataframe['is_green'].iloc[i-j] == 1 and
                   dataframe['close_above_ema9'].iloc[i-j] == 1
                   for j in range(3)):
                dataframe.loc[dataframe.index[i], 'green_above_ema9_count'] = 3

            if all(dataframe['is_red'].iloc[i-j] == 1 and
                   dataframe['close_below_ema9'].iloc[i-j] == 1
                   for j in range(3)):
                dataframe.loc[dataframe.index[i], 'red_below_ema9_count'] = 3

        # 2-bar high breakout
        dataframe['high_2bar'] = dataframe['high'].rolling(2).max().shift(1)
        dataframe['breaks_2bar_high'] = (dataframe['close'] > dataframe['high_2bar']).astype(int)

        # RSI rising
        dataframe['rsi_rising'] = (dataframe['rsi'] > dataframe['rsi'].shift(1)).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Uptrend
                (dataframe['close'] > dataframe['ema_9']) &
                (dataframe['ema_9'] > dataframe['ema_20']) &
                (dataframe['ema9_slope'] > 0) &

                # 3 green closes above 9 EMA
                (dataframe['green_above_ema9_count'] >= 3) &

                # Breaks 2-bar high
                (dataframe['breaks_2bar_high'] == 1) &

                # Still near 9 EMA (≤ 0.2%)
                (abs(dataframe['distance_to_ema9']) <= self.max_ema_distance_pct) &

                # RSI = 50-68 and rising
                (dataframe['rsi'] >= 50) &
                (dataframe['rsi'] <= 68) &
                (dataframe['rsi_rising'] == 1) &

                # Volume ≥ 150% of average
                (dataframe['volume_ratio'] >= 1.5) &

                # No recent 3 red below EMA
                (dataframe['red_below_ema9_count'].rolling(10).sum() == 0) &

                # Green candle
                (dataframe['close'] > dataframe['open']) &

                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # RSI overbought
                (dataframe['rsi'] > 75) |

                # Price significantly below 9 EMA
                (dataframe['close'] < dataframe['ema_9'] * 0.995) |

                # Volume drops significantly
                (dataframe['volume_ratio'] < 0.5)
            ),
            'exit_long'
        ] = 1

        return dataframe
