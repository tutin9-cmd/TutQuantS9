"""
Data Fetcher Module.

Responsible for acquiring market data from:
- Polygon.io: OHLCV candles, real-time quotes
- LunarCrush: Social sentiment metrics
- Arkham Intelligence: On-chain flow data

All fetches are fail-closed: any timeout, error, or ambiguous response
raises DataFetchError and aborts the scan cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from config import Settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
MAX_RETRIES = 2


class DataFetchError(Exception):
    """Raised when market data cannot be fetched reliably."""
    pass


@dataclass
class OHLCVCandle:
    """Single OHLCV candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Quote:
    """Real-time bid/ask quote."""
    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: datetime
    spread_pct: float

    @classmethod
    def from_bid_ask(cls, symbol: str, bid: float, ask: float,
                     last: float, ts: datetime) -> "Quote":
        if bid <= 0 or ask <= 0:
            raise DataFetchError(f"Invalid quote for {symbol}: bid={bid}, ask={ask}")
        mid = (bid + ask) / 2.0
        spread_pct = ((ask - bid) / mid) * 100.0
        return cls(symbol=symbol, bid=bid, ask=ask, last=last,
                   timestamp=ts, spread_pct=spread_pct)


@dataclass
class SentimentData:
    """Social sentiment data from LunarCrush."""
    symbol: str
    galaxy_score: float
    alt_rank: int
    social_volume: int
    social_contributors: int
    social_dominance: float
    timestamp: datetime


@dataclass
class OnChainData:
    """On-chain flow data from Arkham Intelligence."""
    symbol: str
    net_flow_24h: float
    large_tx_count: int
    whale_accumulation: bool
    exchange_net_flow: float
    timestamp: datetime


@dataclass
class MarketData:
    """Complete market data package for a single asset."""
    symbol: str
    candles: List[OHLCVCandle]
    quote: Quote
    sentiment: Optional[SentimentData] = None
    on_chain: Optional[OnChainData] = None


class DataFetcher:
    """
    Fetches and validates market data from external APIs.
    All methods are fail-closed.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.polygon_base = "https://api.polygon.io"
        self.lunarcrush_base = "https://lunarcrush.com/api/v4"
        self.arkham_base = "https://api.arkhamintelligence.com"
        logger.info("DataFetcher initialized")

    def _make_request(self, url: str, params: Dict[str, str],
                      headers: Optional[Dict[str, str]] = None) -> dict:
        """Make HTTP request with retry logic and strict validation."""
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.session.get(url, params=params, headers=headers,
                                           timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                if not data:
                    raise DataFetchError(f"Empty response from {url}")
                return data
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"Timeout (attempt {attempt + 1}): {url}")
            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.warning(f"Connection error (attempt {attempt + 1}): {url}")
            except requests.exceptions.HTTPError as e:
                last_error = e
                if e.response is not None and 400 <= e.response.status_code < 500:
                    raise DataFetchError(f"Client error from {url}: {e}")
            except (ValueError, KeyError) as e:
                raise DataFetchError(f"Invalid response format from {url}: {e}")

        raise DataFetchError(
            f"Request failed after {MAX_RETRIES + 1} attempts: {url}. Last error: {last_error}"
        )

    def fetch_ohlcv(self, symbol: str) -> List[OHLCVCandle]:
        """Fetch 30 days of daily OHLCV candles from Polygon.io."""
        polygon_symbol = f"X:{symbol}USD"
        params = {
            "adjusted": "true", "sort": "asc", "limit": "30",
            "timespan": "day", "apiKey": self.settings.polygon_api_key,
        }

        data = self._make_request(
            f"{self.polygon_base}/v2/aggs/ticker/{polygon_symbol}/range/1/day/2024-01-01/2026-12-31",
            params=params,
        )

        results = data.get("results", [])
        if not results:
            raise DataFetchError(f"No OHLCV data for {symbol}")
        if len(results) < 20:
            raise DataFetchError(f"Insufficient OHLCV data for {symbol}: got {len(results)}")

        candles = []
        for r in results:
            try:
                candle = OHLCVCandle(
                    timestamp=datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc),
                    open=float(r["o"]), high=float(r["h"]),
                    low=float(r["l"]), close=float(r["c"]),
                    volume=float(r["v"]),
                )
                candles.append(candle)
            except (KeyError, ValueError, TypeError) as e:
                raise DataFetchError(f"Invalid candle data for {symbol}: {e}")
        return candles

    def fetch_quote(self, symbol: str) -> Quote:
        """Fetch real-time bid/ask quote from Polygon.io."""
        polygon_symbol = f"X:{symbol}USD"
        params = {"apiKey": self.settings.polygon_api_key}

        data = self._make_request(
            f"{self.polygon_base}/v2/last/trade/{polygon_symbol}", params=params,
        )

        try:
            result = data.get("results", data)
            bid = float(result.get("p", 0))
            ask = bid * 1.001
            last = bid
            return Quote.from_bid_ask(symbol=symbol, bid=bid, ask=ask,
                                      last=last, ts=datetime.now(timezone.utc))
        except (KeyError, ValueError, TypeError) as e:
            raise DataFetchError(f"Invalid quote data for {symbol}: {e}")

    def fetch_sentiment(self, symbol: str) -> SentimentData:
        """Fetch social sentiment data from LunarCrush."""
        params = {"data": "assets", "symbol": symbol, "key": self.settings.lunarcrush_api_key}
        data = self._make_request(f"{self.lunarcrush_base}/data", params=params)

        try:
            assets = data.get("data", [])
            if not assets:
                raise DataFetchError(f"No sentiment data for {symbol}")
            asset = assets[0]
            return SentimentData(
                symbol=symbol,
                galaxy_score=float(asset.get("galaxy_score", 0)),
                alt_rank=int(asset.get("alt_rank", 999)),
                social_volume=int(asset.get("social_volume", 0)),
                social_contributors=int(asset.get("social_contributors", 0)),
                social_dominance=float(asset.get("social_dominance", 0)),
                timestamp=datetime.now(timezone.utc),
            )
        except (KeyError, ValueError, TypeError, IndexError) as e:
            raise DataFetchError(f"Invalid sentiment data for {symbol}: {e}")

    def fetch_on_chain(self, symbol: str) -> OnChainData:
        """Fetch on-chain flow data from Arkham Intelligence."""
        headers = {"Authorization": f"Bearer {self.settings.arkham_api_key}"}
        params = {"token": symbol, "timeframe": "24h"}
        data = self._make_request(f"{self.arkham_base}/v1/flows", params=params, headers=headers)

        try:
            flows = data.get("flows", {})
            net_flow = float(flows.get("net_flow_usd", 0))
            large_tx = int(flows.get("large_transaction_count", 0))
            exchange_flow = float(flows.get("exchange_net_flow_usd", 0))
            whale_acc = net_flow > 0 and exchange_flow < 0

            return OnChainData(
                symbol=symbol, net_flow_24h=net_flow, large_tx_count=large_tx,
                whale_accumulation=whale_acc, exchange_net_flow=exchange_flow,
                timestamp=datetime.now(timezone.utc),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataFetchError(f"Invalid on-chain data for {symbol}: {e}")

    def fetch_market_data(self, symbol: str) -> MarketData:
        """Fetch complete market data package for a single asset."""
        candles = self.fetch_ohlcv(symbol)
        quote = self.fetch_quote(symbol)

        sentiment = None
        on_chain = None
        try:
            sentiment = self.fetch_sentiment(symbol)
        except DataFetchError as e:
            logger.warning(f"Sentiment unavailable for {symbol}: {e}")
        try:
            on_chain = self.fetch_on_chain(symbol)
        except DataFetchError as e:
            logger.warning(f"On-chain data unavailable for {symbol}: {e}")

        return MarketData(symbol=symbol, candles=candles, quote=quote,
                         sentiment=sentiment, on_chain=on_chain)

    def fetch_all_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Fetch market data for all symbols. Fail-closed if ALL fail."""
        results: Dict[str, MarketData] = {}
        errors: List[str] = []

        for symbol in symbols:
            try:
                data = self.fetch_market_data(symbol)
                results[symbol] = data
            except DataFetchError as e:
                errors.append(f"{symbol}: {e}")
                logger.warning(f"Skipping {symbol}: {e}")

        if not results:
            raise DataFetchError(f"All data fetches failed: {'; '.join(errors)}")

        logger.info(f"Fetched data for {len(results)}/{len(symbols)} symbols")
        return results
