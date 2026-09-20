"""
Robinhood Breakout Bot - Source Package.

Modules:
    - data_fetcher: Market data acquisition from Polygon.io, LunarCrush, Arkham
    - technical_engine: Bollinger Bands, ATR, Donchian, Volume analysis
    - llm_regime_guard: LLM-based regime evaluation with strict JSON parsing
    - risk_engine: Deterministic risk management and position sizing
    - execution_manager: Robinhood MCP order execution with idempotency
"""

__version__ = "1.0.0"
__author__ = "Quant Engineering Team"
