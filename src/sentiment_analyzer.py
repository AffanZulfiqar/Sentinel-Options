"""
sentiment_analyzer.py – Claude-powered sentiment analysis for news headlines.

Claude reads a bundle of news articles for each ticker and returns a
structured JSON assessment:
  {
    "ticker":          str,          # e.g. "AAPL"
    "sentiment":       str,          # "BULLISH" | "BEARISH" | "NEUTRAL"
    "confidence":      float,        # 0.0 – 1.0
    "reasoning":       str,          # one-paragraph explanation
    "key_headlines":   [str, ...],   # up to 3 most impactful headlines
    "suggested_trade": str | null    # "CALL" | "PUT" | null
  }
"""
import json
from typing import Dict, List, Optional

import anthropic

from .config import Config
from .logger import get_logger, log_sentiment

log = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are an expert options trading analyst. You will be given recent news headlines
and summaries for a specific stock ticker. Your job is to:

1. Assess the overall sentiment (BULLISH, BEARISH, or NEUTRAL).
2. Assign a confidence score between 0.0 and 1.0.
3. Briefly explain the key drivers.
4. Identify up to 3 most impactful headlines.
5. Suggest whether to buy a CALL option, PUT option, or make no trade (null).

Respond ONLY with a valid JSON object matching this exact schema:
{
  "ticker":          "<TICKER>",
  "sentiment":       "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence":      <float 0.0-1.0>,
  "reasoning":       "<one paragraph>",
  "key_headlines":   ["<headline1>", ...],
  "suggested_trade": "CALL" | "PUT" | null
}

Rules:
- Only suggest a CALL or PUT if confidence >= 0.65.
- Be conservative: if news is mixed, return NEUTRAL with suggested_trade null.
- Never include markdown fences or any text outside the JSON.
"""


class SentimentAnalyzer:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    # ── public API ────────────────────────────────────────────────────────────

    def analyze(self, ticker: str, articles: List[Dict]) -> Optional[Dict]:
        """Run sentiment analysis for *ticker* using *articles*.

        Returns the parsed JSON dict or None on failure.
        """
        if not articles:
            log.info("No articles for %s – skipping sentiment.", ticker)
            return None

        user_content = self._build_prompt(ticker, articles)
        try:
            message = self._client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)
            result["ticker"] = ticker          # ensure correct ticker always
            result["num_articles"] = len(articles)
            log.info(
                "Sentiment for %s → %s (confidence=%.2f, trade=%s)",
                ticker,
                result.get("sentiment"),
                result.get("confidence", 0),
                result.get("suggested_trade"),
            )
            log_sentiment(result)
            return result

        except (json.JSONDecodeError, KeyError) as exc:
            log.error("Failed to parse Claude response for %s: %s", ticker, exc)
            return None
        except Exception as exc:
            log.error("Claude API error for %s: %s", ticker, exc)
            return None

    def analyze_all(self, news_by_ticker: Dict[str, List[Dict]]) -> List[Dict]:
        """Analyze all tickers and return a list of sentiment dicts."""
        results = []
        for ticker, articles in news_by_ticker.items():
            result = self.analyze(ticker, articles)
            if result:
                results.append(result)
        return results

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(ticker: str, articles: List[Dict]) -> str:
        lines = [f"Ticker: {ticker}", f"Total articles: {len(articles)}", ""]
        for i, art in enumerate(articles, 1):
            lines.append(f"--- Article {i} ---")
            lines.append(f"Title:   {art.get('title', '')}")
            lines.append(f"Summary: {art.get('summary', '')[:300]}")
            lines.append(f"Date:    {art.get('published', '')}")
            lines.append("")
        return "\n".join(lines)
