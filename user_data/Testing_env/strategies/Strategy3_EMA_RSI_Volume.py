"""
EMA-RSI-Volume Scalper Strategy

Target Metrics:
- Win rate: ≥ 60%
- Risk per trade: ≤ 2%
- Risk:Reward: ≥ 2:1
- Trade frequency: ~50 trades/day
- Timeframe: 1 minute

Entry Logic (Long only for spot markets):
- Long: EMA9 > EMA21, RSI 50-70, Volume > 1.5× average

Exit Logic:
- Stop Loss: 1.5× ATR
- Take Profit: 3× ATR (2:1 R:R)
- Trailing stop: 0.5% buffer
- Exit on opposite EMA crossover

Risk Management:
- Max 3-5 concurrent trades
- Daily max loss: 5%
"""

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class Strategy3_EMA_RSI_Volume(IStrategy):

    # Strategy metadata
    INTERFACE_VERSION = 3

    # Timeframe
    timeframe = '1m'

    # Can short (disable for spot markets)
    can_short = False

    # ROI table - Take profit at 6% (3× the 2% risk = 2:1 R:R)
    # With dynamic ATR-based exits, this acts as a safety net
    minimal_roi = {
        "0": 0.06
    }

    # Stop loss - Base stop loss at 3% (will be overridden by custom_stoploss with ATR)
    stoploss = -0.03

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.005  # 0.5% buffer
    trailing_only_offset_is_reached = True
    trailing_stop_positive_offset = 0.01  # Start trailing after 1% profit

    # Max open trades
    max_open_trades = 5

    # Position sizing - 2% risk per trade
    stake_amount = 'unlimited'

    # Startup candle count
    startup_candle_count = 50

    # Protection settings for daily max loss
    @property
    def protections(self):
        return [
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 1440,  # 24 hours on 1m
                "trade_limit": 1,
                "stop_duration_candles": 1440,  # Stop for 24 hours
                "max_allowed_drawdown": 0.05  # 5% daily max loss
            }
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add indicators needed for entry and exit signals
        """

        # EMA indicators
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Volume analysis
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']

        # ATR for dynamic stop loss and take profit
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # Calculate ATR-based levels for reference
        dataframe['atr_stop_long'] = dataframe['close'] - (1.5 * dataframe['atr'])
        dataframe['atr_stop_short'] = dataframe['close'] + (1.5 * dataframe['atr'])
        dataframe['atr_target_long'] = dataframe['close'] + (3.0 * dataframe['atr'])
        dataframe['atr_target_short'] = dataframe['close'] - (3.0 * dataframe['atr'])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry signal logic
        """

        # Long entry conditions
        dataframe.loc[
            (
                # EMA trend condition
                (dataframe['ema_9'] > dataframe['ema_21']) &

                # RSI momentum condition (50-70 range)
                (dataframe['rsi'] >= 50) &
                (dataframe['rsi'] <= 70) &

                # Volume spike condition
                (dataframe['volume_ratio'] > 1.5) &

                # Price above EMA9 for confirmation
                (dataframe['close'] > dataframe['ema_9']) &

                # Volume must be positive
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        # Short entry disabled (spot market only - can_short=False)
        # dataframe.loc[
        #     (
        #         (dataframe['ema_9'] < dataframe['ema_21']) &
        #         (dataframe['rsi'] >= 30) &
        #         (dataframe['rsi'] <= 50) &
        #         (dataframe['volume_ratio'] > 1.5) &
        #         (dataframe['close'] < dataframe['ema_9']) &
        #         (dataframe['volume'] > 0)
        #     ),
        #     'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signal logic - Exit on opposite EMA crossover
        """

        # Exit long on bearish EMA crossover
        dataframe.loc[
            (
                (dataframe['ema_9'] < dataframe['ema_21']) &
                (dataframe['ema_9'].shift(1) >= dataframe['ema_21'].shift(1))
            ),
            'exit_long'] = 1

        # Exit short disabled (spot market only - can_short=False)
        # dataframe.loc[
        #     (
        #         (dataframe['ema_9'] > dataframe['ema_21']) &
        #         (dataframe['ema_9'].shift(1) <= dataframe['ema_21'].shift(1))
        #     ),
        #     'exit_short'] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: 'datetime',
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Dynamic stop loss based on ATR (1.5× ATR) - Long positions only
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # Get ATR value
        atr = last_candle['atr']

        # For long positions - Stop loss is 1.5× ATR below entry
        stop_distance = (1.5 * atr) / trade.open_rate
        return -stop_distance

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime',
                    current_rate: float, current_profit: float, **kwargs) -> 'Optional[Union[str, bool]]':
        """
        Dynamic take profit based on ATR (3× ATR for 2:1 R:R) - Long positions only
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # Get ATR value
        atr = last_candle['atr']

        # For long positions - take profit when price rises 3× ATR
        target_profit_pct = (3.0 * atr) / trade.open_rate
        if current_profit >= target_profit_pct:
            return 'atr_target_long'

        return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: 'datetime', entry_tag: 'Optional[str]',
                           side: str, **kwargs) -> bool:
        """
        Confirm trade entry - enforce max open trades and verify conditions
        """
        # Max 5 open trades as per strategy design
        if self.config['max_open_trades'] > 5:
            return False

        return True

    def leverage(self, pair: str, current_time: 'datetime', current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: 'Optional[str]',
                 side: str, **kwargs) -> float:
        """
        No leverage - spot trading only for capital preservation
        """
        return 1.0
