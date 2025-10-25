"""
Strategy 3: Stochastic + RSI Momentum Restart
Port: 8087

Entry Conditions:
- Price near 9 EMA (within 0.2%)
- Stochastic %K crosses above %D from below 40
- RSI > 45 and rising
- 3 consecutive green candles above 9 EMA

Risk Management:
- Stop Loss: 1-1.5%
- Take Profit: 2-3%
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class Strategy3_Stoch_RSI(IStrategy):
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

        # Stochastic
        stoch = ta.STOCH(dataframe, fastk_period=14, slowk_period=3, slowd_period=3)
        dataframe['slowk'] = stoch['slowk']
        dataframe['slowd'] = stoch['slowd']

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Volume
        dataframe['volume_sma_3'] = ta.SMA(dataframe['volume'], timeperiod=3)

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

        # Stochastic crossover from oversold
        dataframe['stoch_cross_above'] = (
            (dataframe['slowk'] > dataframe['slowd']) &
            (dataframe['slowk'].shift(1) <= dataframe['slowd'].shift(1)) &
            (dataframe['slowk'].shift(1) < 40)
        ).astype(int)

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

                # Price near 9 EMA
                (abs(dataframe['distance_to_ema9']) <= self.max_ema_distance_pct) &

                # Stochastic crossover from oversold
                (dataframe['stoch_cross_above'] == 1) &

                # RSI > 45 and rising
                (dataframe['rsi'] > 45) &
                (dataframe['rsi_rising'] == 1) &

                # 3 green candles above EMA
                (dataframe['green_above_ema9_count'] >= 3) &

                # No recent 3 red below EMA
                (dataframe['red_below_ema9_count'].rolling(10).sum() == 0) &

                # Volume confirmation
                (dataframe['volume'] > dataframe['volume_sma_3']) &

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
                # Stochastic overbought
                (dataframe['slowk'] > 80) |

                # Price below 9 EMA
                (dataframe['close'] < dataframe['ema_9'])
            ),
            'exit_long'
        ] = 1

        return dataframe
