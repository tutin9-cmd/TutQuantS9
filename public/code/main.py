"""
Main entry point for the Robinhood Breakout Bot.

Orchestrates the scan loop:
1. Fetch market data for all allowlist assets
2. Run technical analysis to find breakout candidates
3. Query LLM regime guard for each candidate
4. Apply risk engine checks
5. Execute approved trades via Robinhood MCP

Runs on a 5-minute scan interval. Fail-closed on any error.
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timezone
from threading import Event
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, jsonify

from config import Settings, get_settings, setup_logging
from src.data_fetcher import DataFetcher, DataFetchError
from src.execution_manager import ExecutionManager, ExecutionError
from src.llm_regime_guard import LLMRegimeGuard, RegimeGuardError
from src.risk_engine import RiskEngine, RiskCheckResult
from src.technical_engine import TechnicalEngine, TechnicalSignal

logger = logging.getLogger(__name__)

# Graceful shutdown event
shutdown_event = Event()


class BreakoutBot:
    """
    Main bot orchestrator. Coordinates data fetching, technical analysis,
    LLM regime guard, risk engine, and execution.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.data_fetcher = DataFetcher(settings)
        self.technical_engine = TechnicalEngine(settings)
        self.regime_guard = LLMRegimeGuard(settings)
        self.risk_engine = RiskEngine(settings)
        self.execution_manager = ExecutionManager(settings)
        self._scan_count = 0
        self._last_scan_time: Optional[datetime] = None
        logger.info("BreakoutBot initialized with all components")

    def run_scan_cycle(self) -> None:
        """Execute one complete scan cycle across all allowlist assets."""
        self._scan_count += 1
        self._last_scan_time = datetime.now(timezone.utc)
        scan_id = f"scan_{self._scan_count}"
        logger.info(f"[{scan_id}] Starting scan cycle")

        # Step 1: Pre-flight risk checks
        preflight = self.risk_engine.preflight_check()
        if not preflight.allowed:
            logger.info(f"[{scan_id}] Preflight blocked: {preflight.reason}")
            return

        # Step 2: Fetch market data
        try:
            market_data = self.data_fetcher.fetch_all_market_data(
                self.settings.crypto_allowlist
            )
        except DataFetchError as e:
            logger.error(f"[{scan_id}] Data fetch failed (fail-closed): {e}")
            return

        if not market_data:
            logger.warning(f"[{scan_id}] No market data returned")
            return

        # Step 3: Technical analysis
        candidates = self.technical_engine.scan_for_breakouts(market_data)
        logger.info(f"[{scan_id}] Found {len(candidates)} breakout candidates")

        if not candidates:
            return

        # Step 4: Process each candidate
        for signal in candidates:
            self._process_candidate(scan_id, signal)

        logger.info(f"[{scan_id}] Scan cycle complete")

    def _process_candidate(self, scan_id: str, signal: TechnicalSignal) -> None:
        """Process a single breakout candidate through the full pipeline."""
        symbol = signal.symbol
        logger.info(f"[{scan_id}] Processing candidate: {symbol}")

        # LLM Regime Guard
        try:
            regime_verdict = self.regime_guard.evaluate(symbol)
        except RegimeGuardError as e:
            logger.warning(f"[{scan_id}] Regime guard failed for {symbol} (fail-closed): {e}")
            return

        if not regime_verdict.safe_to_trade:
            logger.info(f"[{scan_id}] {symbol} vetoed: {regime_verdict.reason}")
            return

        # Risk Engine
        risk_result = self.risk_engine.evaluate_trade(
            signal=signal, regime_reason=regime_verdict.reason,
        )

        if not risk_result.approved:
            logger.info(f"[{scan_id}] {symbol} rejected by risk engine: {risk_result.reason}")
            return

        # Execute trade
        try:
            order_result = self.execution_manager.execute_entry(
                symbol=symbol,
                position_size_usd=risk_result.position_size_usd,
                stop_loss_price=risk_result.stop_loss_price,
                take_profit_price=risk_result.take_profit_price,
            )
            logger.info(f"[{scan_id}] {symbol} executed: {order_result.order_id}")
        except ExecutionError as e:
            logger.error(f"[{scan_id}] Execution failed for {symbol}: {e}")

    def manage_existing_positions(self) -> None:
        """Check and manage all existing positions for exits."""
        try:
            positions = self.execution_manager.get_open_positions()
        except ExecutionError as e:
            logger.error(f"Failed to fetch positions: {e}")
            return

        for position in positions:
            try:
                exit_decision = self.risk_engine.evaluate_exit(position)
                if exit_decision.should_exit:
                    result = self.execution_manager.execute_exit(
                        symbol=position.symbol,
                        reason=exit_decision.reason,
                        partial_pct=exit_decision.partial_pct,
                    )
                    logger.info(f"Exit {position.symbol}: {exit_decision.reason}")
            except Exception as e:
                logger.error(f"Position management failed for {position.symbol}: {e}")

    def get_status(self) -> dict:
        """Return current bot status for health endpoint."""
        return {
            "status": "running",
            "scan_count": self._scan_count,
            "last_scan": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def create_health_app(bot: BreakoutBot) -> Flask:
    """Create Flask app for health check endpoint."""
    app = Flask(__name__)

    @app.route("/health")
    def health():
        return jsonify(bot.get_status()), 200

    return app


def signal_handler(signum: int, frame: object) -> None:
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    shutdown_event.set()


def main() -> None:
    """Main entry point."""
    settings = get_settings()
    setup_logging(settings)

    logger.info("=" * 60)
    logger.info("Robinhood Breakout Bot starting")
    logger.info(f"Capital: ${settings.total_capital:.2f}")
    logger.info(f"Max position: ${settings.max_position_size:.2f}")
    logger.info(f"Max concurrent: {settings.max_concurrent_positions}")
    logger.info(f"Allowlist: {len(settings.crypto_allowlist)} assets")
    logger.info("=" * 60)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bot = BreakoutBot(settings)

    # Health check server
    health_app = create_health_app(bot)

    # Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(bot.run_scan_cycle, trigger=IntervalTrigger(minutes=5),
                      id="scan_cycle", max_instances=1, coalesce=True)
    scheduler.add_job(bot.manage_existing_positions, trigger=IntervalTrigger(minutes=1),
                      id="position_management", max_instances=1, coalesce=True)
    scheduler.start()

    logger.info("Scheduler started. Bot is running.")

    # Initial scan
    bot.run_scan_cycle()
    bot.manage_existing_positions()

    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()
