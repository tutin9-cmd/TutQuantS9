"""
Execution Manager Module.

Handles order execution via Robinhood's Agentic Trading MCP.
Implements idempotency keys to prevent duplicate orders.
Fail-closed: any execution error aborts the trade.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import requests

from config import Settings
from src.risk_engine import Position

logger = logging.getLogger(__name__)

EXECUTION_TIMEOUT = 15
MAX_EXECUTION_RETRIES = 1


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class ExecutionError(Exception):
    """Raised when order execution fails."""
    pass


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    status: OrderStatus
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    idempotency_key: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrderRecord:
    order_id: str
    idempotency_key: str
    symbol: str
    side: str
    quantity: float
    price: float
    status: str
    created_at: datetime
    updated_at: datetime
    reason: str = ""


class ExecutionManager:
    """Manages order execution via Robinhood MCP with idempotency."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {settings.robinhood_mcp_token}",
            "Content-Type": "application/json",
        })
        self.base_url = settings.robinhood_mcp_url.rstrip("/")
        self.order_history: List[OrderRecord] = []
        self._positions: Dict[str, Position] = {}
        logger.info(f"ExecutionManager initialized | MCP: {self.base_url}")

    def _generate_idempotency_key(self, symbol: str, side: str) -> str:
        short_uuid = uuid.uuid4().hex[:8]
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        return f"{symbol}_{side}_{short_uuid}_{timestamp_ms}"

    def _execute_mcp_request(self, endpoint: str, payload: dict,
                             idempotency_key: str) -> dict:
        """Execute request to Robinhood MCP. Fail-closed."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Idempotency-Key": idempotency_key}
        last_error: Optional[Exception] = None

        for attempt in range(MAX_EXECUTION_RETRIES + 1):
            try:
                response = self.session.post(url, json=payload, headers=headers,
                                            timeout=EXECUTION_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                if not data:
                    raise ExecutionError(f"Empty MCP response: {endpoint}")
                return data
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"MCP timeout (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError as e:
                raise ExecutionError(f"MCP connection failed: {e}")
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else 0
                if 400 <= status < 500:
                    raise ExecutionError(f"MCP client error {status}: {e}")
                last_error = e
            except (ValueError, KeyError) as e:
                raise ExecutionError(f"Invalid MCP response: {e}")

        raise ExecutionError(f"MCP failed after retries: {last_error}")

    def execute_entry(self, symbol: str, position_size_usd: float,
                      stop_loss_price: float, take_profit_price: float) -> OrderResult:
        """Execute a buy order (entry)."""
        idempotency_key = self._generate_idempotency_key(symbol, "buy")
        logger.info(f"BUY {symbol} | ${position_size_usd:.2f} | SL=${stop_loss_price:.4f}")

        payload = {
            "action": "place_order", "symbol": symbol, "side": "buy",
            "type": "market", "notional": position_size_usd, "time_in_force": "gtc",
            "metadata": {
                "strategy": "volatility_breakout",
                "stop_loss": stop_loss_price, "take_profit": take_profit_price,
                "idempotency_key": idempotency_key,
            },
        }

        response = self._execute_mcp_request("orders", payload, idempotency_key)

        try:
            order_id = str(response.get("order_id", response.get("id", "")))
            status_str = str(response.get("status", "failed")).lower()
            filled_qty = float(response.get("filled_qty", 0))
            filled_price = float(response.get("filled_price", 0))

            if not order_id:
                raise ExecutionError(f"No order_id for {symbol}")

            status = OrderStatus.FILLED if status_str == "filled" else OrderStatus(
                status_str if status_str in [s.value for s in OrderStatus] else "failed")

            if status in (OrderStatus.REJECTED, OrderStatus.FAILED):
                raise ExecutionError(f"Order rejected for {symbol}: {response.get('error', '')}")

        except (KeyError, ValueError, TypeError) as e:
            raise ExecutionError(f"Invalid order response for {symbol}: {e}")

        result = OrderResult(order_id=order_id, symbol=symbol, side=OrderSide.BUY,
                           quantity=filled_qty, price=filled_price, status=status,
                           filled_quantity=filled_qty, filled_price=filled_price,
                           idempotency_key=idempotency_key)

        now = datetime.now(timezone.utc)
        self.order_history.append(OrderRecord(
            order_id=order_id, idempotency_key=idempotency_key, symbol=symbol,
            side="buy", quantity=result.quantity, price=result.price,
            status=status.value, created_at=now, updated_at=now,
            reason="volatility_breakout_entry"))

        logger.info(f"BUY executed: {order_id} | {status.value}")
        return result

    def execute_exit(self, symbol: str, reason: str,
                     partial_pct: float = 0.0) -> OrderResult:
        """Execute a sell order (exit)."""
        idempotency_key = self._generate_idempotency_key(symbol, "sell")
        position = self._positions.get(symbol)

        if position is None:
            raise ExecutionError(f"No position for {symbol}")

        sell_quantity = (position.remaining_quantity * partial_pct
                        if partial_pct > 0 else position.remaining_quantity)

        if sell_quantity <= 0:
            raise ExecutionError(f"Invalid sell quantity for {symbol}")

        logger.info(f"SELL {symbol} | Qty={sell_quantity:.6f} | {reason}")

        payload = {
            "action": "place_order", "symbol": symbol, "side": "sell",
            "type": "market", "quantity": sell_quantity, "time_in_force": "gtc",
            "metadata": {
                "strategy": "volatility_breakout", "exit_reason": reason,
                "partial_pct": partial_pct, "idempotency_key": idempotency_key,
            },
        }

        response = self._execute_mcp_request("orders", payload, idempotency_key)

        try:
            order_id = str(response.get("order_id", response.get("id", "")))
            status_str = str(response.get("status", "failed")).lower()
            filled_qty = float(response.get("filled_qty", 0))
            filled_price = float(response.get("filled_price", 0))

            if not order_id:
                raise ExecutionError(f"No order_id for {symbol}")

            status = OrderStatus.FILLED if status_str == "filled" else OrderStatus(
                status_str if status_str in [s.value for s in OrderStatus] else "failed")

        except (KeyError, ValueError, TypeError) as e:
            raise ExecutionError(f"Invalid sell response for {symbol}: {e}")

        result = OrderResult(order_id=order_id, symbol=symbol, side=OrderSide.SELL,
                           quantity=sell_quantity, price=filled_price, status=status,
                           filled_quantity=filled_qty, filled_price=filled_price,
                           idempotency_key=idempotency_key)

        # Update position
        if position:
            position.remaining_quantity -= sell_quantity
            if 0 < partial_pct < 1.0:
                position.partial_exit_executed = True
            if position.remaining_quantity <= 1e-8:
                del self._positions[symbol]

        now = datetime.now(timezone.utc)
        self.order_history.append(OrderRecord(
            order_id=order_id, idempotency_key=idempotency_key, symbol=symbol,
            side="sell", quantity=sell_quantity, price=filled_price,
            status=status.value, created_at=now, updated_at=now, reason=reason))

        return result

    def get_open_positions(self) -> List[Position]:
        """Get all currently open positions."""
        try:
            response = self._execute_mcp_request(
                "positions", {"action": "list_positions"},
                idempotency_key=f"list_{int(datetime.now(timezone.utc).timestamp())}")

            positions_data = response.get("positions", [])
            positions: List[Position] = []

            for p in positions_data:
                try:
                    symbol = str(p["symbol"])
                    qty = float(p.get("qty", 0))
                    if qty > 0 and symbol in self._positions:
                        positions.append(self._positions[symbol])
                except (KeyError, ValueError):
                    continue

            return positions
        except ExecutionError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to fetch positions: {e}")

    def sync_position(self, position: Position) -> None:
        self._positions[position.symbol] = position
