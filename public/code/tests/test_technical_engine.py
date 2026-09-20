"""
Tests for the Technical Analysis Engine.

Tests cover:
- Bollinger Band computation
- Donchian Channel computation
- ATR computation
- Volume SMA computation
- Breakout signal detection
- Edge cases (insufficient data, NaN handling)
"""

from __future__ import annotations

import numpy as np
import pytest

from src.technical_engine import TechnicalEngine


class TestBollingerBands:
    """Tests for Bollinger Band computation."""

    def test_basic_computation(self) -> None:
        """Test BB with known values."""
        closes = np.array([10.0, 11.0, 12.0, 11.5, 12.5, 13.0, 12.0, 11.0,
                          12.0, 13.0, 14.0, 13.5, 12.5, 13.0, 14.0, 15.0,
                          14.5, 13.5, 14.0, 15.0, 16.0], dtype=np.float64)

        sma, upper, lower, bandwidth = TechnicalEngine.compute_bollinger_bands(
            closes, period=20, num_std=2.0
        )

        # SMA at index 19 should be mean of all 20 values
        expected_sma = np.mean(closes[:20])
        assert abs(sma[19] - expected_sma) < 1e-10

        # Upper band should be above SMA
        assert upper[19] > sma[19]

        # Lower band should be below SMA
        assert lower[19] < sma[19]

        # Bandwidth should be positive
        assert bandwidth[19] > 0

    def test_insufficient_data_raises(self) -> None:
        """Test that insufficient data raises ValueError."""
        closes = np.array([10.0, 11.0, 12.0], dtype=np.float64)

        with pytest.raises(ValueError, match="Insufficient data"):
            TechnicalEngine.compute_bollinger_bands(closes, period=20)

    def test_constant_prices(self) -> None:
        """Test BB with constant prices (zero std dev)."""
        closes = np.full(25, 100.0, dtype=np.float64)

        sma, upper, lower, bandwidth = TechnicalEngine.compute_bollinger_bands(
            closes, period=20, num_std=2.0
        )

        # All bands should equal the constant price
        assert abs(upper[19] - 100.0) < 1e-10
        assert abs(lower[19] - 100.0) < 1e-10
        assert abs(bandwidth[19]) < 1e-10


class TestDonchianChannel:
    """Tests for Donchian Channel computation."""

    def test_basic_computation(self) -> None:
        """Test Donchian with known highs and lows."""
        highs = np.array([10, 12, 11, 13, 14, 12, 15, 13, 14, 16,
                         15, 14, 13, 15, 16, 17, 15, 14, 16, 18], dtype=np.float64)
        lows = np.array([8, 9, 8, 10, 11, 9, 12, 10, 11, 13,
                        12, 11, 10, 12, 13, 14, 12, 11, 13, 15], dtype=np.float64)

        upper, middle, lower = TechnicalEngine.compute_donchian_channel(
            highs, lows, period=20
        )

        # Upper should be max of all highs in window
        assert upper[19] == np.max(highs[:20])

        # Lower should be min of all lows in window
        assert lower[19] == np.min(lows[:20])

    def test_insufficient_data_raises(self) -> None:
        """Test that insufficient data raises ValueError."""
        highs = np.array([10.0, 12.0], dtype=np.float64)
        lows = np.array([8.0, 9.0], dtype=np.float64)

        with pytest.raises(ValueError, match="Insufficient data"):
            TechnicalEngine.compute_donchian_channel(highs, lows, period=20)


class TestATR:
    """Tests for ATR computation."""

    def test_basic_computation(self) -> None:
        """Test ATR with known values."""
        highs = np.array([10, 12, 11, 13, 14, 12, 15, 13, 14, 16,
                         15, 14, 13, 15, 16, 17], dtype=np.float64)
        lows = np.array([8, 9, 8, 10, 11, 9, 12, 10, 11, 13,
                        12, 11, 10, 12, 13, 14], dtype=np.float64)
        closes = np.array([9, 11, 9, 12, 13, 10, 14, 11, 13, 15,
                          14, 12, 11, 14, 15, 16], dtype=np.float64)

        atr = TechnicalEngine.compute_atr(highs, lows, closes, period=14)

        # ATR should be positive after initial period
        assert not np.isnan(atr[14])
        assert atr[14] > 0

    def test_insufficient_data_raises(self) -> None:
        """Test that insufficient data raises ValueError."""
        closes = np.array([10.0, 11.0], dtype=np.float64)
        highs = np.array([11.0, 12.0], dtype=np.float64)
        lows = np.array([9.0, 10.0], dtype=np.float64)

        with pytest.raises(ValueError, match="Insufficient data"):
            TechnicalEngine.compute_atr(highs, lows, closes, period=14)


class TestVolumeSMA:
    """Tests for Volume SMA computation."""

    def test_basic_computation(self) -> None:
        """Test volume SMA."""
        volumes = np.array([100, 200, 150, 300, 250, 180, 220, 190, 210, 230,
                           200, 180, 250, 220, 190, 210, 240, 200, 230, 210,
                           220], dtype=np.float64)

        sma = TechnicalEngine.compute_volume_sma(volumes, period=20)

        # SMA at index 19 should be mean of first 20 values
        expected = np.mean(volumes[:20])
        assert abs(sma[19] - expected) < 1e-10

    def test_constant_volume(self) -> None:
        """Test SMA with constant volume."""
        volumes = np.full(25, 1000.0, dtype=np.float64)

        sma = TechnicalEngine.compute_volume_sma(volumes, period=20)

        assert abs(sma[19] - 1000.0) < 1e-10


class TestPercentileRank:
    """Tests for percentile rank computation."""

    def test_basic_percentile(self) -> None:
        """Test percentile rank."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

        # Minimum value should be 0th percentile
        assert TechnicalEngine.compute_percentile_rank(values, 1.0) == 0.0

        # Maximum value should be 90th percentile (9 of 10 below)
        assert TechnicalEngine.compute_percentile_rank(values, 10.0) == 90.0

    def test_empty_array(self) -> None:
        """Test with empty array returns neutral."""
        values = np.array([], dtype=np.float64)
        assert TechnicalEngine.compute_percentile_rank(values, 5.0) == 50.0
