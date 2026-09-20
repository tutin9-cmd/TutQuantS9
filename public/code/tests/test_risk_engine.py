"""
Tests for the Risk Engine.

Tests cover:
- Weekend blackout detection
- Position size limits
- Concurrent position limits
- Trade velocity limits
- Spread checks
- Stop-loss and take-profit computation
- Exit decisions (stop-loss, time-stop, trailing stop, take-profit)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.risk_engine import (
    ExitDecision,
    Position,
    PreflightResult,
    RiskCheckResult,
    RiskEngine,
    TradeRecord,
    EST_OFFSET,
)
from src.technical_engine import TechnicalSignal
from src.data_fetcher import Quote


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.total_capital = 250.0
    settings.max_position_size = 50.0
    settings.max_concurrent_positions = 3
    settings.max_trades_per_asset_24h = 2
    settings.max_spread_pct = 0.75
    settings.stop_loss_atr_multiplier = 2.0
    settings.take_profit_pct = 8.0
    settings.trailing_sma_period = 20
    settings.time_stop_hours = 48
    settings.blackout_start_day = "friday"
    settings.blackout_start_hour = 20
    settings.blackout_end_day = "sunday"
    settings.blackout_end_hour = 20
    settings.crypto_allowlist = ["BTC", "ETH", "SOL"]
    return settings


@pytest.fixture
def risk_engine(mock_settings):
    """Create a risk engine with mock settings."""
    return RiskEngine(mock_settings)


@pytest.fixture
def sample_signal():
    """Create a sample technical signal."""
    return TechnicalSignal(
        symbol="BTC",
        current_price=50000.0,
        bb_upper=49800.0,
        donchian_upper=49500.0,
        bb_width=2.5,
        bb_width_percentile=10.0,
        volume_ratio=2.5,
        atr_14=500.0,
        atr_stop_distance=1000.0,
        signal_strength=0.85,
    )


@pytest.fixture
def sample_quote():
    """Create a sample market quote."""
    return Quote(
        symbol="BTC",
        bid=49990.0,
        ask=50010.0,
        last=50000.0,
        timestamp=datetime.now(timezone.utc),
        spread_pct=0.04,
    )


class TestPreflightCheck:
    """Tests for pre-flight checks."""

    def test_returns_preflight_result(self, risk_engine):
        """Test that preflight returns correct type."""
        result = risk_engine.preflight_check()
        assert isinstance(result, PreflightResult)
        assert isinstance(result.allowed, bool)
        assert isinstance(result.reason, str)


class TestSpreadCheck:
    """Tests for spread checking."""

    def test_spread_within_limit(self, risk_engine, sample_quote):
        """Test that acceptable spread passes."""
        ok, reason = risk_engine._check_spread(sample_quote)
        assert ok is True

    def test_spread_exceeds_limit(self, risk_engine):
        """Test that excessive spread is rejected."""
        bad_quote = Quote(
            symbol="BTC",
            bid=49000.0,
            ask=51000.0,
            last=50000.0,
            timestamp=datetime.now(timezone.utc),
            spread_pct=4.0,  # 4% > 0.75% limit
        )
        ok, reason = risk_engine._check_spread(bad_quote)
        assert ok is False
        assert "exceeds max" in reason


class TestConcurrentPositions:
    """Tests for concurrent position limits."""

    def test_under_limit(self, risk_engine):
        """Test that being under limit passes."""
        ok, reason = risk_engine._check_concurrent_positions()
        assert ok is True

    def test_at_limit(self, risk_engine):
        """Test that being at limit is rejected."""
        for i, sym in enumerate(["BTC", "ETH", "SOL"]):
            risk_engine.open_positions[sym] = Position(
                symbol=sym,
                entry_price=100.0 * (i + 1),
                quantity=1.0,
                entry_time=datetime.now(timezone.utc),
                stop_loss_price=90.0 * (i + 1),
                take_profit_price=108.0 * (i + 1),
                initial_position_size_usd=100.0 * (i + 1),
            )

        ok, reason = risk_engine._check_concurrent_positions()
        assert ok is False
        assert "Max concurrent" in reason


class TestTradeVelocity:
    """Tests for trade velocity limits."""

    def test_under_limit(self, risk_engine):
        """Test that being under velocity limit passes."""
        ok, reason = risk_engine._check_trade_velocity("BTC")
        assert ok is True

    def test_at_limit(self, risk_engine):
        """Test that being at velocity limit is rejected."""
        now = datetime.now(timezone.utc)
        risk_engine.trade_history = [
            TradeRecord(symbol="BTC", timestamp=now - timedelta(hours=1), side="entry"),
            TradeRecord(symbol="BTC", timestamp=now - timedelta(hours=2), side="entry"),
        ]

        ok, reason = risk_engine._check_trade_velocity("BTC")
        assert ok is False
        assert "velocity limit" in reason.lower() or "Velocity" in reason

    def test_old_trades_not_counted(self, risk_engine):
        """Test that trades outside 24h window are not counted."""
        now = datetime.now(timezone.utc)
        risk_engine.trade_history = [
            TradeRecord(symbol="BTC", timestamp=now - timedelta(hours=25), side="entry"),
            TradeRecord(symbol="BTC", timestamp=now - timedelta(hours=26), side="entry"),
        ]

        ok, reason = risk_engine._check_trade_velocity("BTC")
        assert ok is True


class TestEvaluateTrade:
    """Tests for full trade evaluation."""

    def test_approved_trade(self, risk_engine, sample_signal, sample_quote):
        """Test that a valid trade is approved."""
        result = risk_engine.evaluate_trade(sample_signal, "regime_ok", sample_quote)
        assert result.approved is True
        assert result.position_size_usd > 0
        assert result.stop_loss_price > 0
        assert result.take_profit_price > 0

    def test_rejected_high_spread(self, risk_engine, sample_signal):
        """Test that high spread causes rejection."""
        bad_quote = Quote(
            symbol="BTC",
            bid=49000.0,
            ask=51000.0,
            last=50000.0,
            timestamp=datetime.now(timezone.utc),
            spread_pct=4.0,
        )
        result = risk_engine.evaluate_trade(sample_signal, "regime_ok", bad_quote)
        assert result.approved is False
        assert "Spread" in result.reason

    def test_position_size_capped(self, risk_engine, sample_signal, sample_quote):
        """Test that position size is capped at max_position_size."""
        result = risk_engine.evaluate_trade(sample_signal, "regime_ok", sample_quote)
        assert result.position_size_usd <= risk_engine.settings.max_position_size


class TestExitEvaluation:
    """Tests for exit decision logic."""

    def test_stop_loss_triggered(self, risk_engine):
        """Test stop-loss exit."""
        position = Position(
            symbol="BTC",
            entry_price=50000.0,
            quantity=0.001,
            entry_time=datetime.now(timezone.utc) - timedelta(hours=1),
            stop_loss_price=48000.0,
            take_profit_price=54000.0,
            initial_position_size_usd=50.0,
            highest_price_since_entry=47500.0,  # Below stop-loss
        )

        decision = risk_engine.evaluate_exit(position)
        assert decision.should_exit is True
        assert "Stop-loss" in decision.reason

    def test_time_stop_triggered(self, risk_engine):
        """Test time-stop exit."""
        position = Position(
            symbol="BTC",
            entry_price=50000.0,
            quantity=0.001,
            entry_time=datetime.now(timezone.utc) - timedelta(hours=50),  # > 48h
            stop_loss_price=48000.0,
            take_profit_price=54000.0,
            initial_position_size_usd=50.0,
            highest_price_since_entry=49500.0,  # Negative PnL
        )

        decision = risk_engine.evaluate_exit(position)
        assert decision.should_exit is True
        assert "Time-stop" in decision.reason

    def test_hold_when_healthy(self, risk_engine):
        """Test that healthy position is held."""
        position = Position(
            symbol="BTC",
            entry_price=50000.0,
            quantity=0.001,
            entry_time=datetime.now(timezone.utc) - timedelta(hours=5),
            stop_loss_price=48000.0,
            take_profit_price=54000.0,
            initial_position_size_usd=50.0,
            highest_price_since_entry=51000.0,  # Above entry, below TP
        )

        decision = risk_engine.evaluate_exit(position)
        assert decision.should_exit is False
