"""
LLM Regime Guard Module.

Uses an LLM to evaluate whether a breakout signal is safe to trade
based on on-chain and social sentiment data.

The LLM is used ONLY as a veto mechanism. Output is strictly parsed JSON.
Any parsing failure = veto (fail-closed).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI, APIError, APITimeoutError, APIConnectionError

from config import Settings
from src.data_fetcher import DataFetcher, MarketData, DataFetchError

logger = logging.getLogger(__name__)

LLM_MODEL = "gpt-4o-mini"
LLM_MAX_TOKENS = 300
LLM_TEMPERATURE = 0.1
LLM_TIMEOUT = 15
MAX_LLM_RETRIES = 2

SYSTEM_PROMPT = """You are a crypto trading risk analyst. Your job is to EVALUATE whether a volatility breakout signal is safe to execute.

CRITICAL RULES:
1. Assume ALL breakouts are FAKEOUTS unless on-chain and social data EXPLICITLY proves otherwise.
2. You are a VETO mechanism. Your default answer is NO.
3. Only approve if BOTH conditions are met:
   a) On-chain data shows whale accumulation (net inflows to non-exchange wallets)
   b) Social sentiment is positive (Galaxy Score > 50 AND social volume is rising)
4. If data is missing, ambiguous, or contradictory, you MUST veto.
5. Output ONLY valid JSON. No markdown, no explanation outside JSON.

OUTPUT FORMAT (strict JSON, no other text):
{"safe_to_trade": true, "reason": "concise reason under 100 chars"}
OR
{"safe_to_trade": false, "reason": "concise reason under 100 chars"}"""


class RegimeGuardError(Exception):
    """Raised when the regime guard cannot produce a valid verdict."""
    pass


@dataclass
class RegimeVerdict:
    """Result of LLM regime evaluation."""
    safe_to_trade: bool
    reason: str
    symbol: str
    raw_response: str


class LLMRegimeGuard:
    """LLM-based regime guard. Fail-closed on any error."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.data_fetcher = DataFetcher(settings)
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=LLM_TIMEOUT,
            max_retries=0,
        )
        logger.info("LLMRegimeGuard initialized")

    def _build_user_prompt(self, data: MarketData) -> str:
        """Construct the user prompt with market context."""
        symbol = data.symbol
        quote = data.quote
        sentiment = data.sentiment
        on_chain = data.on_chain

        parts = [
            f"EVALUATE BREAKOUT SIGNAL FOR: {symbol}",
            f"",
            f"CURRENT MARKET DATA:",
            f"- Price: ${quote.last:.4f}",
            f"- Bid: ${quote.bid:.4f} | Ask: ${quote.ask:.4f}",
            f"- Spread: {quote.spread_pct:.3f}%",
        ]

        if sentiment:
            parts.extend([
                f"", f"SOCIAL SENTIMENT (LunarCrush):",
                f"- Galaxy Score: {sentiment.galaxy_score:.1f}/100",
                f"- Alt Rank: #{sentiment.alt_rank}",
                f"- Social Volume: {sentiment.social_volume}",
                f"- Social Contributors: {sentiment.social_contributors}",
                f"- Social Dominance: {sentiment.social_dominance:.2f}%",
            ])
        else:
            parts.extend([f"", f"SOCIAL SENTIMENT: UNAVAILABLE"])

        if on_chain:
            parts.extend([
                f"", f"ON-CHAIN DATA (Arkham):",
                f"- Net Flow 24h: ${on_chain.net_flow_24h:,.0f}",
                f"- Large Transactions (>$100k): {on_chain.large_tx_count}",
                f"- Whale Accumulation: {'YES' if on_chain.whale_accumulation else 'NO'}",
                f"- Exchange Net Flow: ${on_chain.exchange_net_flow:,.0f}",
            ])
        else:
            parts.extend([f"", f"ON-CHAIN DATA: UNAVAILABLE"])

        parts.extend([f"", f"REMINDER: Default to VETO unless data explicitly supports the breakout."])
        return "\n".join(parts)

    def _parse_llm_response(self, response_text: str, symbol: str) -> RegimeVerdict:
        """Parse LLM response into strict RegimeVerdict. Fail-closed."""
        cleaned = response_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise RegimeGuardError(f"JSON parse failed for {symbol}: {e}")

        if not isinstance(parsed, dict):
            raise RegimeGuardError(f"Response not dict for {symbol}")
        if "safe_to_trade" not in parsed:
            raise RegimeGuardError(f"Missing 'safe_to_trade' for {symbol}")
        if "reason" not in parsed:
            raise RegimeGuardError(f"Missing 'reason' for {symbol}")

        safe = parsed["safe_to_trade"]
        reason = str(parsed["reason"])

        if not isinstance(safe, bool):
            raise RegimeGuardError(f"'safe_to_trade' must be bool for {symbol}")

        return RegimeVerdict(safe_to_trade=safe, reason=reason[:200],
                           symbol=symbol, raw_response=response_text)

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with retry logic."""
        last_error: Optional[Exception] = None

        for attempt in range(MAX_LLM_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=LLM_MAX_TOKENS,
                    temperature=LLM_TEMPERATURE,
                    timeout=LLM_TIMEOUT,
                )
                content = response.choices[0].message.content
                if not content:
                    raise RegimeGuardError("Empty LLM response")
                return content
            except APITimeoutError as e:
                last_error = e
                logger.warning(f"LLM timeout (attempt {attempt + 1})")
            except APIConnectionError as e:
                last_error = e
                logger.warning(f"LLM connection error (attempt {attempt + 1})")
            except APIError as e:
                if "authentication" in str(e).lower():
                    raise RegimeGuardError(f"LLM auth failed: {e}")
                last_error = e

        raise RegimeGuardError(f"LLM failed after {MAX_LLM_RETRIES + 1} attempts: {last_error}")

    def evaluate(self, symbol: str) -> RegimeVerdict:
        """Evaluate whether a breakout signal is safe to trade."""
        logger.info(f"Regime guard evaluating {symbol}")

        try:
            market_data = self.data_fetcher.fetch_market_data(symbol)
        except DataFetchError as e:
            raise RegimeGuardError(f"Cannot fetch data for regime evaluation: {e}")

        prompt = self._build_user_prompt(market_data)
        raw_response = self._call_llm(prompt)
        verdict = self._parse_llm_response(raw_response, symbol)

        logger.info(f"Regime verdict for {symbol}: safe={verdict.safe_to_trade}")
        return verdict
