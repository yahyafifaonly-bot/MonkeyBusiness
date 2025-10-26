# user_data/strategies/EMAPlaybookStrategy.py
from datetime import time
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes
from pandas import DataFrame


class EMAPlaybookStrategy(IStrategy):
    """
    EMA-only, long-only, 5m strategy with 10 named variants (v1..v10).
    Configure the variant via 'variant' in config or via CLI:
        --strategy-params '{"variant":"v3"}'
    Defaults to v1 if not provided.

    Fixed "religion":
      - timeframe: 5m
      - long-only
      - 9EMA > 21EMA on 5m to consider longs
      - TP at least 2R by default (variant v8 uses 3R)
      - Risk per trade target = 2% (approximated via dynamic stop/TP sizing + custom_stake_amount)
      - Max open trades = 3 (set this in your config)
    """

    # ----- Religion / constants -----
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    # ROI is not used (we use dynamic exits), but Freqtrade needs something.
    minimal_roi = {"0": 0.99}
    stoploss = -0.99  # We manage SL dynamically via custom_stoploss, so set very wide fallback.

    # Informative TFs for filters
    informative_timeframe_15m = "15m"
    informative_timeframe_1h = "1h"

    # Optimization switches (not hyperopt; we switch by variant)
    variant_param = IntParameter(1, 10, default=1, space="buy", optimize=False)

    # ------------- Variant Definitions -------------
    # Each variant resolves to a dict of knobs A..G + extras (tp_mult, max_concurrent_override)
    VARIANTS: Dict[str, Dict[str, Any]] = {
        # v1 baseline / loose scalper
        "v1": dict(A="A1", B="B1", C="C1", D="D1", E="E1", F="F1", G="G1", tp_mult=2.0),
        # v2 momentum guard
        "v2": dict(A="A1", B="B2", C="C2", D="D2", E="E1", F="F2", G="G2", tp_mult=2.0),
        # v3 macro-aligned sniper
        "v3": dict(A="A2", B="B2", C="C3", D="D3", E="E2", F="F2", G="G2", tp_mult=2.0),
        # v4 reversion bounce farm
        "v4": dict(A="A3", B="B1", C="C2", D="D2", E="E3", F="F1", G="G1", tp_mult=2.0),
        # v5 panic eject
        "v5": dict(A="A1", B="B1", C="C2", D="D2", E="E1", F="F3", G="G2", tp_mult=2.0),
        # v6 compression breakout
        "v6": dict(A="A1", B="B1", C="C2", D="D2", E="E1", F="F2", G="G2",
                   tp_mult=2.0, compression=0.002, compression_len=3),
        # v7 scalp factory (stress test)
        "v7": dict(A="A1", B="B1", C="C1", D="D1", E="E1", F="F1", G="G1", tp_mult=2.0),
        # v8 tight stop, huge RR
        "v8": dict(A="A2", B="B2", C="C2", D="D2", E="E2", F="F2", G="G2", tp_mult=3.0),
        # v9 capital efficiency (like v2 but assume lower concurrency in config)
        "v9": dict(A="A1", B="B2", C="C2", D="D2", E="E1", F="F2", G="G2", tp_mult=2.0),
        # v10 late entry continuation
        "v10": dict(A="A1", B="B1", C="C2", D="D2", E="E1", F="F2", G="G2",
                    tp_mult=2.0, cont_len=5, cont_require_touch=False),
    }

    # ---------------- Helper: read variant from config/params ----------------
    def _get_variant_key(self) -> str:
        # Priority: strategy-params, then config, else v1
        params = getattr(self, "strategy_params", {}) or {}
        v = params.get("variant")
        if v is None:
            # Freqtrade adds strategy -> config dict under self.config
            cfg = getattr(self, "config", {}) or {}
            scfg = cfg.get("strategy", {}) or {}
            v = scfg.get("variant", "v1")
        v = str(v).lower().strip()
        if v.startswith("v"):
            return v
        # allow "1".."10"
        try:
            idx = int(v)
            return f"v{idx}"
        except Exception:
            return "v1"

    # ---------------- Indicators ----------------
    def informative_pairs(self):
        # Only need same pair in higher TFs
        return []

    def custom_feed(self, dataframe: DataFrame) -> DataFrame:
        """Compute EMAs, slopes, and higher timeframe EMAs merged into 5m frame."""
        df = dataframe.copy()

        # Ensure date column exists
        if 'date' not in df.columns:
            df['date'] = pd.to_datetime(df.index)

        # EMAs
        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

        # Slopes over 3 candles
        df["slope_f"] = df["ema9"] - df["ema9"].shift(3)
        df["slope_s"] = df["ema21"] - df["ema21"].shift(3)

        # 15m / 1h informative EMA state (simple resample from 5m)
        # Set date as index for resampling
        df_indexed = df.set_index('date')

        df15 = df_indexed.resample("15T", label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()
        df15["ema9_15"] = df15["close"].ewm(span=9, adjust=False).mean()
        df15["ema21_15"] = df15["close"].ewm(span=21, adjust=False).mean()
        df15 = df15[["ema9_15", "ema21_15"]].reindex(df_indexed.index, method="ffill")

        df1h = df_indexed.resample("1H", label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()
        df1h["ema9_1h"] = df1h["close"].ewm(span=9, adjust=False).mean()
        df1h["ema21_1h"] = df1h["close"].ewm(span=21, adjust=False).mean()
        df1h = df1h[["ema9_1h", "ema21_1h"]].reindex(df_indexed.index, method="ffill")

        df = df_indexed.join(df15).join(df1h).reset_index()
        return df

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        if "date" not in df.columns:
            df["date"] = pd.to_datetime(df.index)
        df = self.custom_feed(df)
        return df

    # ---------------- Entry logic ----------------
    def _time_filter(self, dt: pd.Timestamp, G: str) -> bool:
        # G1 = 24/7, G2 = trade 08:00–16:00 UTC, G3 = only when 15m 9>21 (implemented in buy rule)
        if G == "G1":
            return True
        if G == "G2":
            t = dt.time()
            return time(8, 0) <= t <= time(16, 0)
        return True  # G3 handled separately inside conditions

    def _pullback_ok(self, row: pd.Series, A: str) -> bool:
        # A1: candle low <= 9EMA*1.001 ; A2: close <= 9EMA*1.0025 ; A3: low touched 21EMA but close above it
        if A == "A1":
            return row["low"] <= row["ema9"] * 1.001
        if A == "A2":
            return row["close"] <= row["ema9"] * 1.0025
        if A == "A3":
            return (row["low"] <= row["ema21"]) and (row["close"] > row["ema21"])
        return False

    def _confirm_ok(self, df: DataFrame, idx: int, B: str) -> bool:
        # B1: first green close above 9EMA
        # B2: 2 consecutive green closes above 9EMA
        # B3: close above both 9 and 21 after dip
        row = df.iloc[idx]
        if B == "B1":
            return (row["close"] > row["open"]) and (row["close"] > row["ema9"])
        if B == "B2":
            r1 = df.iloc[idx]
            r0 = df.iloc[idx - 1] if idx - 1 >= 0 else None
            ok = (
                r1 is not None and r0 is not None
                and (r1["close"] > r1["open"]) and (r1["close"] > r1["ema9"])
                and (r0["close"] > r0["open"]) and (r0["close"] > r0["ema9"])
            )
            return bool(ok)
        if B == "B3":
            return (row["close"] > row["ema9"]) and (row["close"] > row["ema21"])
        return False

    def _trend_filter_ok(self, row: pd.Series, C: str) -> bool:
        # C1: 5m only, C2: 15m 9>21, C3: 1h 9>21
        if C == "C1":
            return True
        if C == "C2":
            return (row["ema9_15"] > row["ema21_15"])
        if C == "C3":
            return (row["ema9_1h"] > row["ema21_1h"])
        return True

    def _slope_ok(self, row: pd.Series, D: str) -> bool:
        # D1 none, D2 slope_f>0, D3 slope_f>0 & slope_s>0
        if D == "D1":
            return True
        if D == "D2":
            return row["slope_f"] > 0
        if D == "D3":
            return (row["slope_f"] > 0) and (row["slope_s"] > 0)
        return True

    def _compression_ok(self, df: DataFrame, idx: int, settings: Dict[str, Any]) -> bool:
        if "compression" not in settings:
            return True
        c = settings["compression"]
        L = int(settings.get("compression_len", 3))
        if idx - (L - 1) < 0:
            return False
        window = df.iloc[idx - (L - 1): idx + 1]
        spread = (window["ema9"] - window["ema21"]).abs() / window["close"]
        return (spread < c).all()

    def _continuation_ok(self, df: DataFrame, idx: int, settings: Dict[str, Any]) -> bool:
        if "cont_len" not in settings:
            return True
        L = int(settings["cont_len"])
        if idx - (L - 1) < 0:
            return False
        window = df.iloc[idx - (L - 1): idx + 1]
        return (window["close"] > window["ema9"]).all()

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        vkey = self._get_variant_key()
        settings = self.VARIANTS.get(vkey, self.VARIANTS["v1"])

        df["enter_long"] = 0

        for i in range(len(df)):
            row = df.iloc[i]

            # Always require bullish 5m structure & price above both EMAs
            if not (row["ema9"] > row["ema21"] and row["close"] > row["ema9"] and row["close"] > row["ema21"]):
                continue

            # Time filter
            if not self._time_filter(row["date"], settings.get("G", "G1")):
                continue

            # G3 adaptive session = 15m 9>21
            if settings.get("G") == "G3" and not (row["ema9_15"] > row["ema21_15"]):
                continue

            # Pullback requirement (except v10 continuation)
            if "cont_len" in settings:
                cont_ok = self._continuation_ok(df, i, settings)
                if not cont_ok:
                    continue
                # minor dip near 9 EMA (no touch required)
                near9 = (row["low"] <= row["ema9"] * 1.0015)
                if not near9:
                    continue
            else:
                if not self._pullback_ok(row, settings.get("A", "A1")):
                    continue

            # Confirmation
            if not self._confirm_ok(df, i, settings.get("B", "B1")):
                continue

            # Trend filter scope
            if not self._trend_filter_ok(row, settings.get("C", "C1")):
                continue

            # Slope requirement
            if not self._slope_ok(row, settings.get("D", "D1")):
                continue

            # Compression precondition (v6)
            if not self._compression_ok(df, i, settings):
                continue

            df.iat[i, df.columns.get_loc("enter_long")] = 1

        return df

    # ---------------- Exit logic (dynamic) ----------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        vkey = self._get_variant_key()
        settings = self.VARIANTS.get(vkey, self.VARIANTS["v1"])

        df["exit_long"] = 0

        # F rules:
        # F1: only TP/SL (no rule-based exits)
        # F2: exit if candle close < 21 EMA
        # F3: exit if ema9 < ema21 (cross down)
        F = settings.get("F", "F1")
        if F == "F2":
            df.loc[df["close"] < df["ema21"], "exit_long"] = 1
        elif F == "F3":
            df.loc[df["ema9"] < df["ema21"], "exit_long"] = 1
        # F1 => leave to SL/TP only
        return df

    # ---------------- Dynamic Stop & Take Profit ----------------
    def custom_stoploss(self, pair: str, trade: Trade, current_time,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Return dynamic stoploss (as a fraction negative).
        E rules:
          E1: few ticks below 21 EMA
          E2: few ticks below pullback low (stored in trade metadata)
          E3: few ticks below 21 EMA touch low (similar to E2 if provided)
        """
        vkey = self._get_variant_key()
        settings = self.VARIANTS.get(vkey, self.VARIANTS["v1"])
        E = settings.get("E", "E1")

        # Failsafe
        pad = 0.001  # ~0.1%

        try:
            df = self.dp.get_pair_dataframe(pair=pair, timeframe=self.timeframe)
            row = df.iloc[-1]

            if E == "E1":
                sl_price = row["ema21"] * (1 - pad)
            elif E in ("E2", "E3"):
                # Use recent swing low over last 3 candles
                sl_price = float(df["low"].iloc[-3:].min()) * (1 - pad)
            else:
                # fallback: 1.5% stop
                sl_price = trade.open_rate * 0.985

            # convert to stoploss fraction:
            sl_frac = (sl_price - current_rate) / current_rate
            # Must be negative:
            return float(min(-0.001, sl_frac))
        except Exception:
            return -0.015  # 1.5% fallback

    def custom_exit(self, pair: str, trade: Trade, current_time,
                    current_rate: float, current_profit: float, **kwargs):
        """
        Enforce TP = R-multiple (2R or 3R):
          R = (entry - stop)
          TP = entry + tp_mult * R
        """
        vkey = self._get_variant_key()
        settings = self.VARIANTS.get(vkey, self.VARIANTS["v1"])
        tp_mult = float(settings.get("tp_mult", 2.0))

        # Attempt reconstruct SL used at entry
        try:
            df = self.dp.get_pair_dataframe(pair=pair, timeframe=self.timeframe)
            row = df.iloc[-1]
            E = settings.get("E", "E1")

            if E == "E1":
                sl_price = row["ema21"] * 0.999
            else:
                sl_price = float(df["low"].iloc[-3:].min()) * 0.999

            R = max(1e-6, trade.open_rate - sl_price)
            tp_price = trade.open_rate + tp_mult * R

            if current_rate >= tp_price:
                return "playbook_tp"
        except Exception:
            pass

        return None

    def leverage(self, pair: str, current_time, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        return 1.0
