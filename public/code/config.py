"""
Configuration module for the Robinhood Breakout Bot.

All configuration is loaded from environment variables via pydantic-settings.
No hardcoded secrets. Fail-closed on missing required values.
"""

from __future__ import annotations

import logging
import sys
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All API keys are required. If any are missing, the application
    will fail to start (fail-closed principle).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # === API Keys (Required) ===
    polygon_api_key: str = Field(..., description="Polygon.io API key")
    lunarcrush_api_key: str = Field(..., description="LunarCrush API key")
    arkham_api_key: str = Field(..., description="Arkham Intelligence API key")
    openai_api_key: str = Field(..., description="OpenAI API key for LLM regime guard")

    # === Robinhood MCP ===
    robinhood_mcp_url: str = Field(
        default="http://localhost:3000",
        description="Robinhood MCP server URL",
    )
    robinhood_mcp_token: str = Field(..., description="Robinhood MCP auth token")

    # === Trading Parameters ===
    total_capital: float = Field(default=250.0, gt=0, description="Total account capital in USD")
    max_position_size: float = Field(default=50.0, gt=0, description="Max position size per trade in USD")
    max_concurrent_positions: int = Field(default=3, gt=0, description="Maximum concurrent open positions")
    max_trades_per_asset_24h: int = Field(default=2, gt=0, description="Max trades per asset in rolling 24h window")

    # === Risk Parameters ===
    max_spread_pct: float = Field(default=0.75, gt=0, description="Maximum bid-ask spread percentage to allow entry")
    stop_loss_atr_multiplier: float = Field(default=2.0, gt=0, description="ATR multiplier for stop-loss distance")
    take_profit_pct: float = Field(default=8.0, gt=0, description="Take-profit percentage for partial exit")
    trailing_sma_period: int = Field(default=20, gt=0, description="SMA period for trailing stop")
    time_stop_hours: int = Field(default=48, gt=0, description="Hours before time-stop liquidation")

    # === Weekend Blackout ===
    blackout_start_day: str = Field(default="friday", description="Blackout start day (lowercase)")
    blackout_start_hour: int = Field(default=20, ge=0, le=23, description="Blackout start hour (EST)")
    blackout_end_day: str = Field(default="sunday", description="Blackout end day (lowercase)")
    blackout_end_hour: int = Field(default=20, ge=0, le=23, description="Blackout end hour (EST)")

    # === Logging ===
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="logs/bot.log", description="Log file path")

    # === Allowlist ===
    crypto_allowlist: List[str] = Field(
        default=[
            "BTC", "ETH", "SOL", "AVAX", "DOGE", "MATIC", "LINK", "UNI",
            "ATOM", "LTC", "XLM", "ALGO", "DOT", "ADA", "FIL", "AAVE",
            "NEAR", "APT", "ARB", "OP", "SUI", "SEI", "TIA", "INJ", "RNDR",
        ],
        description="Top-25 crypto allowlist symbols",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("blackout_start_day", "blackout_end_day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        """Ensure day names are valid."""
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        v_lower = v.lower()
        if v_lower not in valid_days:
            raise ValueError(f"Invalid day: {v}. Must be one of {valid_days}")
        return v_lower

    @field_validator("crypto_allowlist")
    @classmethod
    def validate_allowlist(cls, v: List[str]) -> List[str]:
        """Ensure allowlist is not empty and symbols are uppercase."""
        if not v:
            raise ValueError("Crypto allowlist cannot be empty")
        if len(v) > 50:
            raise ValueError("Allowlist too large; max 50 symbols")
        return [s.upper() for s in v]


def get_settings() -> Settings:
    """
    Load and validate settings. Raises on any missing required field.
    
    Returns:
        Settings: Validated application settings.
    
    Raises:
        pydantic.ValidationError: If any required field is missing or invalid.
    """
    try:
        settings = Settings()
        logger.info("Configuration loaded successfully")
        return settings
    except Exception as e:
        logger.critical(f"Configuration failed to load: {e}")
        print(f"FATAL: Configuration error - {e}", file=sys.stderr)
        raise


def setup_logging(settings: Settings) -> None:
    """
    Configure application-wide logging.
    
    Args:
        settings: Application settings containing log configuration.
    """
    import os
    
    log_dir = os.path.dirname(settings.log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger.info(f"Logging configured at level {settings.log_level}")
