"""
Deterministic Risk Engine.

Enforces ALL hard risk limits. This module is the final authority
on whether a trade can proceed. The LLM cannot override these limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from config import Settings
from src.data_fetcher import Quote
from src.technical_engine import TechnicalSignal

logger = logging.getLogger(__name__)

EST_OFFSET = timezone(timedelta(hours=-5))

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


class ExitReason(Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT_PARTIAL = "take_profit_partial"
    TRAILING_STOP = "trailing_stop"
    TIME_STOP = "time_stop"


@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss_price: float
    take_profit_price: float
    initial_position_size_usd: float
    partial_exit_executed: bool = False
    remaining_quantity: float = 0.0
    trailing_stop_price: Optional[float] = None
    highest_price_since_entry: float = 0.0

    def __post_init__(self) -> None:
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = self.quantity
        if self.highest_price_since_entry == 0.0:
            self.highest_price_since_entry = self.entry_price


@dataclass
class RiskCheckResult:
    """Result of a risk evaluation."""
    approved: bool
    reason: str
    position_size_usd: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    quantity: float = 0.0


@dataclass
class PreflightResult:
    allowed: bool
    reason: str


@dataclass
class ExitDecision:
    should_exit: bool
    reason: str
    partial_pct: float = 0.0


@dataclass
class TradeRecord:
    symbol: str
    timestamp: datetime
    side: str


class RiskEngine:
    """Deterministic risk engine enforcing all hard limits."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.open_positions: Dict[str, Position] = {}
        self.trade_history: List[TradeRecord] = []
        logger.info(f"RiskEngine initialized | Capital=${settings.total_capital:.2f}")

    def preflight_check(self) -> PreflightResult:
        """Run pre-flight checks (weekend blackout, etc.)."""
        now_est = datetime.now(EST_OFFSET)
        current_day = now_est.weekday()
        current_hour = now_est.hour

        blackout_start_day = DAY_MAP.get(self.settings.blackout_start_day, 4)
        blackout_end_day = DAY_MAP.get(self.settings.blackout_end_day, 6)
        blackout_start_hour = self.settings.blackout_start_hour
        blackout_end_hour = self.settings.blackout_end_hour

        in_blackout = False
        if current_day == blackout_start_day and current_hour >= blackout_start_hour:
            in_blackout = True
        elif current_day == blackout_end_day and current_hour < blackout_end_hour:
            in_blackout = True
        elif blackout_start_day < current_day < blackout_end_day:
            in_blackout = True
        elif blackout_start_day > blackout_end_day:
            if current_day >= blackout_start_day or current_day < blackout_end_day:
                if not (current_day == blackout_end_day and current_hour >= blackout_end_hour):
                    in_blackout = True

        if in_blackout:
            return PreflightResult(allowed=False,
                reason=f"Weekend blackout (Fri {blackout_start_hour}:00 - Sun {blackout_end_hour}:00 EST)")

        return PreflightResult(allowed=True, reason="Preflight passed")

    def _check_spread(self, quote: Quote) -> Tuple[bool, str]:
        if quote.spread_pct > self.settings.max_spread_pct:
            return False, f"Spread {quote.spread_pct:.3f}% exceeds max {self.settings.max_spread_pct}%"
        return True, "Spread acceptable"

    def _check_concurrent_positions(self) -> Tuple[bool, str]:
        current_count = len(self.open_positions)
        if current_count >= self.settings.max_concurrent_positions:
            return False, f"Max concurrent positions: {current_count}/{self.settings.max_concurrent_positions}"
        return True, "Position slots available"

    def _check_trade_velocity(self, symbol: str) -> Tuple[bool, str]:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=24)
        recent = [t for t in self.trade_history if t.symbol == symbol and t.timestamp >= window_start]
        if len(recent) >= self.settings.max_trades_per_asset_24h:
            return False, f"Velocity limit for {symbol}: {len(recent)}/{self.settings.max_trades_per_asset_24h} in 24h"
        return True, "Velocity OK"

    def _check_duplicate_position(self, symbol: str) -> Tuple[bool, str]:
        if symbol in self.open_positions:
            return False, f"Already have position in {symbol}"
        return True, "No duplicate"

    def _compute_position_size(self, signal: TechnicalSignal, quote: Quote) -> Tuple[float, float]:
        position_size_usd = min(self.settings.max_position_size, self.settings.total_capital * 0.20)
        deployed = sum(p.remaining_quantity * p.entry_price for p in self.open_positions.values())
        available = self.settings.total_capital - deployed
        position_size_usd = min(position_size_usd, available)

        if position_size_usd <= 0:
            return 0.0, 0.0

        entry_price = quote.ask
        if entry_price <= 0:
            return 0.0, 0.0

        quantity = position_size_usd / entry_price
        return position_size_usd, quantity

    def evaluate_trade(self, signal: TechnicalSignal, regime_reason: str,
                       quote: Optional[Quote] = None) -> RiskCheckResult:
        """Evaluate whether a trade should be executed. All hard limits checked."""
        symbol = signal.symbol

        if quote is None:
            quote = Quote(symbol=symbol, bid=signal.current_price * 0.999,
                         ask=signal.current_price * 1.001, last=signal.current_price,
                         timestamp=datetime.now(timezone.utc), spread_pct=0.2)

        # Check 1: Spread
        spread_ok, reason = self._check_spread(quote)
        if not spread_ok:
            return RiskCheckResult(approved=False, reason=reason)

        # Check 2: Concurrent positions
        pos_ok, reason = self._check_concurrent_positions()
        if not pos_ok:
            return RiskCheckResult(approved=False, reason=reason)

        # Check 3: Duplicate
        dup_ok, reason = self._check_duplicate_position(symbol)
        if not dup_ok:
            return RiskCheckResult(approved=False, reason=reason)

        # Check 4: Velocity
        vel_ok, reason = self._check_trade_velocity(symbol)
        if not vel_ok:
            return RiskCheckResult(approved=False, reason=reason)

        # Position sizing
        position_size_usd, quantity = self._compute_position_size(signal, quote)
        if position_size_usd <= 0 or quantity <= 0:
            return RiskCheckResult(approved=False, reason="Insufficient capital")

        # Stop-loss and take-profit
        entry_price = quote.ask
        stop_loss_price = entry_price - signal.atr_stop_distance
        take_profit_price = entry_price * (1.0 + self.settings.take_profit_pct / 100.0)

        if stop_loss_price <= 0:
            return RiskCheckResult(approved=False, reason=f"Stop-loss negative: ${stop_loss_price:.4f}")

        # Risk/reward check (minimum 1.5:1)
        risk = entry_price - stop_loss_price
        reward = take_profit_price - entry_price
        if risk > 0 and reward / risk < 1.5:
            return RiskCheckResult(approved=False, reason=f"R:R too low: {reward/risk:.2f}")

        # Record trade
        self.trade_history.append(TradeRecord(symbol=symbol,
            timestamp=datetime.now(timezone.utc), side="entry"))

        logger.info(f"APPROVED {symbol} | Size=${position_size_usd:.2f} | SL=${stop_loss_price:.4f}")
        return RiskCheckResult(approved=True, reason=f"All checks passed | {regime_reason}",
                              position_size_usd=position_size_usd, stop_loss_price=stop_loss_price,
                              take_profit_price=take_profit_price, quantity=quantity)

    def evaluate_exit(self, position: Position) -> ExitDecision:
        """Evaluate whether an existing position should be exited."""
        current_price = position.highest_price_since_entry

        # Stop-loss
        if current_price <= position.stop_loss_price:
            return ExitDecision(should_exit=True,
                reason=f"Stop-loss: ${current_price:.4f} <= ${position.stop_loss_price:.4f}")

        # Time-stop
        now = datetime.now(timezone.utc)
        hours_held = (now - position.entry_time).total_seconds() / 3600.0
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100.0

        if hours_held >= self.settings.time_stop_hours and pnl_pct <= 0:
            return ExitDecision(should_exit=True,
                reason=f"Time-stop: {hours_held:.1f}h, PnL={pnl_pct:.2f}%")

        # Take-profit partial
        if not position.partial_exit_executed and current_price >= position.take_profit_price:
            return ExitDecision(should_exit=True,
                reason=f"Take-profit partial at +{self.settings.take_profit_pct}%",
                partial_pct=0.5)

        # Trailing stop
        if position.partial_exit_executed and position.trailing_stop_price is not None:
            if current_price <= position.trailing_stop_price:
                return ExitDecision(should_exit=True, reason="Trailing stop hit")

        return ExitDecision(should_exit=False, reason="Hold")

    def register_position(self, position: Position) -> None:
        self.open_positions[position.symbol] = position

    def remove_position(self, symbol: str) -> None:
        if symbol in self.open_positions:
            del self.open_positions[symbol]
