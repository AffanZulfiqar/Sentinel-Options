"""
sentiment_analyzer.py – Gemini-powered sentiment analysis for news headlines.

Uses the google-genai SDK (google.genai) — the current supported package.

Returns a structured JSON assessment per ticker:
  {
    "ticker":          str,
    "sentiment":       "BULLISH" | "BEARISH" | "NEUTRAL",
    "confidence":      float,        # 0.0 – 1.0
    "reasoning":       str,
    "key_headlines":   [str, ...],
    "suggested_trade": "CALL" | "PUT" | null
  }
"""
import json
from typing import Dict, List, Optional

from google import genai
from google.genai import types

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
        self._client = genai.Client(api_key=Config.GEMINI_API_KEY)

    # ── public API ────────────────────────────────────────────────────────────

    def analyze(self, ticker: str, articles: List[Dict]) -> Optional[Dict]:
        """Run sentiment analysis for *ticker* using *articles*."""
        if not articles:
            log.info("No articles for %s – skipping sentiment.", ticker)
            return None

        user_content = self._build_prompt(ticker, articles)
        try:
            response = self._client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.2,
                    max_output_tokens=2048,
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE",
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE",
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE",
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE",
                        ),
                    ],
                ),
            )

            # Guard against empty / blocked responses
            raw = (response.text or "").strip()
            if not raw:
                log.warning(
                    "Gemini returned empty response for %s (likely safety filter). "
                    "finish_reason=%s",
                    ticker,
                    response.candidates[0].finish_reason if response.candidates else "unknown",
                )
                return None

            # Strip markdown fences if Gemini wraps output in ```json ... ```
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)
            result["ticker"] = ticker
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
            log.error("Failed to parse Gemini response for %s: %s", ticker, exc)
            return None
        except Exception as exc:
            log.error("Gemini API error for %s: %s", ticker, exc)
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
