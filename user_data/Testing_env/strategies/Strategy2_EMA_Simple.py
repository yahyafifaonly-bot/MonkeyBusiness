"""
Strategy 2: Simple 9/21 EMA Pullback (High Frequency)
Port: 8082

Strategy Requirements:
- 9 EMA and 21 EMA ONLY (no other indicators)
- Long positions only
- High frequency (targeting 100+ trades/day)
- 5 min timeframe
- Risk to Reward: 2:1 minimum
- Risk: 2% per trade
- Max open trades: 3

Entry Conditions:
- Price > 9 EMA > 21 EMA (uptrend confirmed)
- Price pulls back close to 9 EMA (within 0.5%)
- Current candle closes above 9 EMA (bounce confirmation)

Exit Conditions:
- Stop Loss: 2% below entry
- Take Profit: 4% above entry (2:1 R:R)

Expected Performance:
- High frequency trades (100-200/day)
- Win rate target: 40-50%
- Positive expectancy with 2:1 R:R

Last Updated: 2025-10-25 - Initial simple EMA strategy
Auto-backtest enabled - Results in dashboard at http://72.61.162.23:8091
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class Strategy2_EMA_Simple(IStrategy):
    INTERFACE_VERSION = 3

    # Strategy settings
    timeframe = '5m'
    can_short = False

    # Risk management (2% risk, 4% profit = 2:1 R:R)
    minimal_roi = {
        "0": 0.04,    # 4% take profit (2:1 R:R)
    }

    stoploss = -0.02  # 2% stop loss

    # Trailing stop disabled for clean 2:1 R:R
    trailing_stop = False

    # Max open trades
    max_open_trades = 3

    # Startup candles
    startup_candle_count = 30

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate ONLY 9 EMA and 21 EMA - nothing else.
        """
        # Calculate EMAs
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)

        # Distance from 9 EMA (for entry trigger)
        dataframe['distance_from_ema9'] = ((dataframe['close'] - dataframe['ema_9']) / dataframe['ema_9']) * 100

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Signal:
        1. Price > 9 EMA > 21 EMA (uptrend)
        2. Price within 0.5% of 9 EMA (pullback/close to EMA)
        3. Current candle closes above 9 EMA (bounce confirmation)
        """
        dataframe.loc[
            (
                # Uptrend: Price above both EMAs
                (dataframe['close'] > dataframe['ema_9']) &
                (dataframe['ema_9'] > dataframe['ema_21']) &

                # Pullback: Price close to 9 EMA (within 0.5%)
                (dataframe['distance_from_ema9'] >= 0) &
                (dataframe['distance_from_ema9'] <= 0.5) &

                # Bounce confirmation: Current candle closes above 9 EMA
                (dataframe['close'] > dataframe['ema_9']) &

                # Volume check (basic)
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit handled by ROI (4% profit) and stoploss (2% loss).
        No manual exit signals needed.
        """
        # No exit signal - let ROI and stoploss handle exits
        dataframe['exit_long'] = 0
        return dataframe
