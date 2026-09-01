"""
news_fetcher.py – Fetch recent headlines for each ticker via Google News RSS.

Returns a list of article dicts:
  { "ticker": str, "title": str, "summary": str, "published": str, "link": str }
"""
import time
from typing import Dict, List

import feedparser
import requests

from .logger import get_logger

log = get_logger(__name__)

# Google News RSS template – searches for "{ticker} stock" news
_RSS_TEMPLATE = (
    "https://news.google.com/rss/search"
    "?q={query}+stock&hl=en-US&gl=US&ceid=US:en"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NewsSentimentBot/1.0; "
        "+https://github.com/trading-agent)"
    )
}

# Max articles per ticker per cycle
MAX_ARTICLES_PER_TICKER = 10


def fetch_news_for_ticker(ticker: str, max_articles: int = MAX_ARTICLES_PER_TICKER) -> List[Dict]:
    """Fetch latest news articles for *ticker* from Google News RSS."""
    url = _RSS_TEMPLATE.format(query=ticker)
    articles: List[Dict] = []
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:max_articles]:
            articles.append(
                {
                    "ticker":    ticker,
                    "title":     entry.get("title", ""),
                    "summary":   entry.get("summary", ""),
                    "published": entry.get("published", ""),
                    "link":      entry.get("link", ""),
                }
            )
        log.info("Fetched %d articles for %s", len(articles), ticker)
    except Exception as exc:
        log.warning("Failed to fetch news for %s: %s", ticker, exc)
    return articles


def fetch_news_for_watchlist(watchlist: List[str], delay_seconds: float = 1.0) -> Dict[str, List[Dict]]:
    """Fetch news for every ticker in *watchlist*.

    Returns a dict: { ticker -> [article, ...] }
    A small delay between requests avoids hammering the RSS endpoint.
    """
    results: Dict[str, List[Dict]] = {}
    for ticker in watchlist:
        results[ticker] = fetch_news_for_ticker(ticker)
        time.sleep(delay_seconds)
    return results
