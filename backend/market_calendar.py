from __future__ import annotations

import sqlite3
from datetime import date, datetime, time as datetime_time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

CN_TZ = ZoneInfo("Asia/Shanghai")
MARKET_OPEN = datetime_time(9, 30)
MARKET_CLOSE = datetime_time(15, 0)
SENTIMENT_WATCHLIST_REFRESH_START = datetime_time(8, 0)


def cn_now() -> datetime:
    return datetime.now(CN_TZ)


def is_sentiment_watchlist_refresh_window(now: datetime | None = None) -> bool:
    """True during daily 08:00-24:00 (Asia/Shanghai); outside hours the watchlist agent skips."""
    current = (now or cn_now()).astimezone(CN_TZ)
    return current.time() >= SENTIMENT_WATCHLIST_REFRESH_START


def cn_market_session(now: datetime | None = None) -> str:
    current = (now or cn_now()).astimezone(CN_TZ)
    if current.weekday() >= 5:
        return "closed"
    clock = current.time()
    if clock < MARKET_OPEN:
        return "pre_market"
    if clock < MARKET_CLOSE:
        return "trading"
    return "after_close"


def previous_trading_day(value: date) -> date:
    cursor = value - timedelta(days=1)
    while cursor.weekday() >= 5:
        cursor -= timedelta(days=1)
    return cursor


def last_completed_trading_day(now: datetime | None = None) -> str:
    current = (now or cn_now()).astimezone(CN_TZ)
    session = cn_market_session(current)
    today = current.date()
    if session in {"closed", "pre_market"}:
        if session == "pre_market" and today.weekday() < 5:
            return previous_trading_day(today).isoformat()
        cursor = today
        while cursor.weekday() >= 5:
            cursor -= timedelta(days=1)
        return cursor.isoformat()
    if session == "trading":
        return previous_trading_day(today).isoformat()
    return today.isoformat()


def evaluate_market_quote_refresh(db_latest_trade_date: str | None, now: datetime | None = None) -> dict[str, Any]:
    current = (now or cn_now()).astimezone(CN_TZ)
    session = cn_market_session(current)
    today = current.date()
    today_iso = today.isoformat() if today.weekday() < 5 else None
    last_completed = last_completed_trading_day(current)
    db_latest = str(db_latest_trade_date or "").strip()

    needs_live_quote = False
    needs_history_refresh = False
    reason = ""

    if session in {"closed", "pre_market"}:
        if db_latest and db_latest >= last_completed:
            return _plan("skip", "db already covers last completed trading day", session, db_latest, last_completed, False, False)
        needs_live_quote = True
        needs_history_refresh = True
        reason = "db behind last completed trading day outside session"
    elif session == "after_close":
        if today_iso and db_latest and db_latest >= today_iso:
            return _plan("skip", "db already covers today's close", session, db_latest, today_iso, False, False)
        needs_live_quote = True
        needs_history_refresh = not bool(db_latest and today_iso and db_latest >= today_iso)
        reason = "after close but db missing today's bar"
    else:
        if db_latest and db_latest >= last_completed:
            return _plan("skip", "db already covers last completed trading day", session, db_latest, last_completed, False, False)
        needs_live_quote = True
        needs_history_refresh = True
        reason = "intraday and db missing last completed trading day"

    action = "live_only" if needs_live_quote and not needs_history_refresh else "refresh"
    return _plan(action, reason, session, db_latest, last_completed, needs_live_quote, needs_history_refresh)


def _plan(
    action: str,
    reason: str,
    session: str,
    db_latest: str,
    expected: str,
    needs_live_quote: bool,
    needs_history_refresh: bool,
) -> dict[str, Any]:
    return {
        "action": action,
        "reason": reason,
        "session": session,
        "db_latest_trade_date": db_latest or None,
        "expected_trade_date": expected,
        "needs_live_quote": needs_live_quote,
        "needs_history_refresh": needs_history_refresh,
    }


def latest_db_trade_date(conn: sqlite3.Connection, symbol: str) -> str | None:
    row = conn.execute(
        """
        select max(trade_date) as latest_trade_date
        from daily_bars
        where symbol = ?
          and provider != 'mock-market'
        """,
        (str(symbol or "").upper(),),
    ).fetchone()
    if not row or not row["latest_trade_date"]:
        return None
    return str(row["latest_trade_date"])
