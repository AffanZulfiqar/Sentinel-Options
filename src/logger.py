"""
logger.py – JSON-based audit logger.

Every trade decision (executed OR refused) is written to a append-only
JSON-lines file so that every action is fully auditable.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

from .config import Config

# ── stdlib logger ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Return a named stdlib logger."""
    return logging.getLogger(name)


# ── JSON audit helpers ────────────────────────────────────────────────────────

def _append_json(path: str, record: Dict[str, Any]) -> None:
    """Append a single JSON record (one per line) to *path*."""
    Config.ensure_data_dir()
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def log_trade(record: Dict[str, Any]) -> None:
    """Append an executed trade record."""
    _append_json(Config.TRADES_LOG, record)


def log_refused_trade(record: Dict[str, Any]) -> None:
    """Append a refused trade record (risk-gate rejection)."""
    _append_json(Config.REFUSED_TRADES_LOG, record)


def log_sentiment(record: Dict[str, Any]) -> None:
    """Append a sentiment analysis record."""
    _append_json(Config.SENTIMENT_LOG, record)


def log_portfolio_snapshot(record: Dict[str, Any]) -> None:
    """Append a portfolio value snapshot."""
    _append_json(Config.PORTFOLIO_HISTORY, record)


# ── Read helpers (for dashboard) ──────────────────────────────────────────────

def _read_json_lines(path: str) -> list:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def read_trades() -> list:
    return _read_json_lines(Config.TRADES_LOG)


def read_refused_trades() -> list:
    return _read_json_lines(Config.REFUSED_TRADES_LOG)


def read_sentiment_log() -> list:
    return _read_json_lines(Config.SENTIMENT_LOG)


def read_portfolio_history() -> list:
    return _read_json_lines(Config.PORTFOLIO_HISTORY)
