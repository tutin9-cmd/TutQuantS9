"""
Technical Analysis Engine.

Computes indicators and detects Volatility Breakout signals:
- Bollinger Band Width (20-period) at 30-day low
- Price breaking above 20-period Donchian Channel / Upper Bollinger Band
- Volume > 1.5x 20-period SMA of volume
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from config import Settings
from src.data_fetcher import MarketData

logger = logging.getLogger(__name__)


@dataclass
class TechnicalSignal:
    """Represents a detected breakout signal."""
    symbol: str
    current_price: float
    bb_upper: float
    donchian_upper: float
    bb_width: float
    bb_width_percentile: float
    volume_ratio: float
    atr_14: float
    atr_stop_distance: float
    signal_strength: float


class TechnicalEngine:
    """Computes technical indicators and detects breakout signals."""

    BB_PERIOD = 20
    BB_STD_DEV = 2.0
    DONCHIAN_PERIOD = 20
    VOLUME_SMA_PERIOD = 20
    ATR_PERIOD = 14
    BB_WIDTH_LOOKBACK = 30
    VOLUME_THRESHOLD = 1.5

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        logger.info("TechnicalEngine initialized")

    @staticmethod
    def compute_bollinger_bands(closes: np.ndarray, period: int = 20,
                                num_std: float = 2.0) -> tuple:
        """Compute Bollinger Bands: (middle, upper, lower, bandwidth)."""
        if len(closes) < period:
            raise ValueError(f"Insufficient data: need {period}, got {len(closes)}")

        sma = np.full_like(closes, np.nan, dtype=np.float64)
        std = np.full_like(closes, np.nan, dtype=np.float64)

        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1:i + 1]
            sma[i] = np.mean(window)
            std[i] = np.std(window, ddof=0)

        upper = sma + (num_std * std)
        lower = sma - (num_std * std)
        bandwidth = np.where(sma > 0, (upper - lower) / sma * 100.0, np.nan)

        return sma, upper, lower, bandwidth

    @staticmethod
    def compute_donchian_channel(highs: np.ndarray, lows: np.ndarray,
                                 period: int = 20) -> tuple:
        """Compute Donchian Channel: (upper, middle, lower)."""
        if len(highs) < period:
            raise ValueError(f"Insufficient data: need {period}, got {len(highs)}")

        upper = np.full_like(highs, np.nan, dtype=np.float64)
        lower = np.full_like(lows, np.nan, dtype=np.float64)

        for i in range(period - 1, len(highs)):
            upper[i] = np.max(highs[i - period + 1:i + 1])
            lower[i] = np.min(lows[i - period + 1:i + 1])

        middle = (upper + lower) / 2.0
        return upper, middle, lower

    @staticmethod
    def compute_atr(highs: np.ndarray, lows: np.ndarray,
                    closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Compute Average True Range (ATR) using Wilder's smoothing."""
        if len(closes) < period + 1:
            raise ValueError(f"Insufficient data for ATR: need {period + 1}")

        tr = np.full_like(closes, np.nan, dtype=np.float64)
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr[i] = max(hl, hc, lc)

        atr = np.full_like(closes, np.nan, dtype=np.float64)
        first_valid = period
        atr[first_valid] = np.nanmean(tr[1:first_valid + 1])

        for i in range(first_valid + 1, len(closes)):
            if not np.isnan(tr[i]) and not np.isnan(atr[i - 1]):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        return atr

    @staticmethod
    def compute_volume_sma(volumes: np.ndarray, period: int = 20) -> np.ndarray:
        """Compute Simple Moving Average of volume."""
        sma = np.full_like(volumes, np.nan, dtype=np.float64)
        for i in range(period - 1, len(volumes)):
            sma[i] = np.mean(volumes[i - period + 1:i + 1])
        return sma

    @staticmethod
    def compute_percentile_rank(values: np.ndarray, current: float) -> float:
        """Compute percentile rank of current value within the array."""
        valid = values[~np.isnan(values)]
        if len(valid) == 0:
            return 50.0
        count_below = np.sum(valid < current)
        return (count_below / len(valid)) * 100.0

    def analyze_symbol(self, data: MarketData) -> Optional[TechnicalSignal]:
        """Analyze a single symbol for breakout conditions."""
        symbol = data.symbol
        candles = data.candles

        min_candles = max(self.BB_WIDTH_LOOKBACK, self.BB_PERIOD, self.ATR_PERIOD + 1)
        if len(candles) < min_candles:
            return None

        closes = np.array([c.close for c in candles], dtype=np.float64)
        highs = np.array([c.high for c in candles], dtype=np.float64)
        lows = np.array([c.low for c in candles], dtype=np.float64)
        volumes = np.array([c.volume for c in candles], dtype=np.float64)

        try:
            _, bb_upper, _, bb_width = self.compute_bollinger_bands(closes)
            donchian_upper, _, _ = self.compute_donchian_channel(highs, lows)
            atr = self.compute_atr(highs, lows, closes)
            vol_sma = self.compute_volume_sma(volumes)

            current_price = closes[-1]
            current_bb_upper = bb_upper[-1]
            current_donchian_upper = donchian_upper[-1]
            current_bb_width = bb_width[-1]
            current_volume = volumes[-1]
            current_vol_sma = vol_sma[-1]
            current_atr = atr[-1]

            if np.isnan(current_bb_width) or np.isnan(current_atr) or np.isnan(current_vol_sma):
                return None
            if current_vol_sma <= 0:
                return None

            # Condition 1: BB Width at 30-day low (bottom 20th percentile)
            recent_widths = bb_width[-self.BB_WIDTH_LOOKBACK:]
            valid_widths = recent_widths[~np.isnan(recent_widths)]
            if len(valid_widths) < 10:
                return None

            bb_width_pct = self.compute_percentile_rank(valid_widths, current_bb_width)
            if bb_width_pct > 20.0:
                return None

            # Condition 2: Price breaks above Donchian/BB upper
            breakout_level = max(current_bb_upper, current_donchian_upper)
            previous_close = closes[-2] if len(closes) >= 2 else current_price

            if current_price <= breakout_level:
                return None
            if previous_close >= breakout_level:
                return None

            # Condition 3: Volume > 1.5x SMA
            volume_ratio = current_volume / current_vol_sma
            if volume_ratio < self.VOLUME_THRESHOLD:
                return None

            # All conditions met
            atr_stop_distance = current_atr * self.settings.stop_loss_atr_multiplier
            signal_strength = min(1.0,
                (volume_ratio / 3.0) * 0.4 +
                ((100 - bb_width_pct) / 100) * 0.3 +
                (min(current_price / breakout_level - 1.0, 0.05) / 0.05) * 0.3
            )

            signal = TechnicalSignal(
                symbol=symbol, current_price=current_price,
                bb_upper=current_bb_upper, donchian_upper=current_donchian_upper,
                bb_width=current_bb_width, bb_width_percentile=bb_width_pct,
                volume_ratio=volume_ratio, atr_14=current_atr,
                atr_stop_distance=atr_stop_distance, signal_strength=signal_strength,
            )

            logger.info(f"{symbol}: BREAKOUT | Price={current_price:.4f} | "
                       f"BB_pct={bb_width_pct:.1f}% | Vol={volume_ratio:.2f}x")
            return signal

        except (ValueError, IndexError, ZeroDivisionError) as e:
            logger.error(f"{symbol}: Technical analysis error: {e}")
            return None

    def scan_for_breakouts(self, market_data: Dict[str, MarketData]) -> List[TechnicalSignal]:
        """Scan all assets for breakout signals."""
        signals: List[TechnicalSignal] = []

        for symbol, data in market_data.items():
            signal = self.analyze_symbol(data)
            if signal is not None:
                signals.append(signal)

        signals.sort(key=lambda s: s.signal_strength, reverse=True)
        logger.info(f"Breakout scan complete: {len(signals)} signals detected")
        return signals
