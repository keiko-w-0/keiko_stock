from __future__ import annotations

import sqlite3
from typing import Any

from .db import row_to_dict
from .pinyin import pinyin_initials


SYMBOL_ALIASES = {
    "华大智造": "688114.SH",
    "华大智造科技": "688114.SH",
    "华大智造科技股份有限公司": "688114.SH",
    "688114": "688114.SH",
    "hd": "688114.SH",
    "hdz": "688114.SH",
    "hdzz": "688114.SH",
}


def resolve_symbol(conn: sqlite3.Connection, query: str, market: str = "all") -> dict[str, Any] | None:
    clean = query.strip()
    if not clean:
        return None

    market_filter = normalize_market(market)
    upper = clean.upper().replace(" ", "")
    compact = compact_query(clean)
    candidates = [upper]

    alias = SYMBOL_ALIASES.get(compact) or SYMBOL_ALIASES.get(clean)
    if alias:
        candidates.insert(0, alias)

    inferred = infer_symbol(upper)
    if inferred and inferred not in candidates:
        candidates.insert(0, inferred)

    for candidate in candidates:
        row = fetch_symbol(conn, candidate, market_filter)
        if row:
            return row

    row = fetch_symbol_by_alias(conn, clean, market_filter)
    if row:
        return row

    row = fetch_symbol_by_name(conn, clean, market_filter)
    if row:
        return row

    row = fetch_symbol_by_pinyin(conn, clean, market_filter)
    if row:
        return row

    if alias:
        return {"symbol": alias, "market": market_from_symbol(alias), "name": clean}

    return None


def normalize_symbol_query(conn: sqlite3.Connection, query: str, market: str = "all") -> str:
    resolved = resolve_symbol(conn, query, market)
    if resolved:
        return str(resolved["symbol"])
    clean = query.strip()
    return infer_symbol(clean.upper()) or clean.upper()


def fetch_symbol(conn: sqlite3.Connection, symbol: str, market: str = "ALL") -> dict[str, Any] | None:
    if market == "ALL":
        row = conn.execute("select * from symbols where upper(symbol) = ?", (symbol.upper(),)).fetchone()
    else:
        row = conn.execute(
            "select * from symbols where upper(symbol) = ? and upper(market) = ?",
            (symbol.upper(), market),
        ).fetchone()
    return row_to_dict(row) if row else None


def fetch_symbol_by_name(conn: sqlite3.Connection, query: str, market: str = "ALL") -> dict[str, Any] | None:
    clean = query.strip().lower()
    if not clean:
        return None
    params: tuple[Any, ...]
    sql = """
        select *
        from symbols
        where lower(name) = ?
    """
    params = (clean,)
    if market != "ALL":
        sql += " and upper(market) = ?"
        params = (clean, market)
    sql += " order by symbol limit 1"
    row = conn.execute(sql, params).fetchone()
    if row:
        return row_to_dict(row)

    like = f"%{clean}%"
    sql = """
        select *
        from symbols
        where lower(name) like ?
    """
    params = (like,)
    if market != "ALL":
        sql += " and upper(market) = ?"
        params = (like, market)
    sql += " order by symbol limit 1"
    row = conn.execute(sql, params).fetchone()
    return row_to_dict(row) if row else None


def fetch_symbol_by_alias(conn: sqlite3.Connection, query: str, market: str = "ALL") -> dict[str, Any] | None:
    normalized = compact_query(query).lower()
    if not normalized:
        return None
    sql = """
        select s.*
        from symbol_aliases a
        join symbols s on s.symbol = a.symbol
        where a.normalized_alias = ?
    """
    params: tuple[Any, ...] = (normalized,)
    if market != "ALL":
        sql += " and upper(s.market) = ?"
        params = (normalized, market)
    sql += " order by s.symbol limit 1"
    row = conn.execute(sql, params).fetchone()
    if row:
        return row_to_dict(row)

    like = f"%{normalized}%"
    sql = """
        select s.*
        from symbol_aliases a
        join symbols s on s.symbol = a.symbol
        where a.normalized_alias like ?
    """
    params = (like,)
    if market != "ALL":
        sql += " and upper(s.market) = ?"
        params = (like, market)
    sql += " order by s.symbol limit 1"
    row = conn.execute(sql, params).fetchone()
    return row_to_dict(row) if row else None


def fetch_symbol_by_pinyin(conn: sqlite3.Connection, query: str, market: str = "ALL") -> dict[str, Any] | None:
    normalized = compact_query(query).lower()
    if not normalized or not normalized.isascii() or normalized.isdigit():
        return None
    rows = conn.execute(
        """
        select *
        from symbols
        where ? = 'ALL' or upper(market) = ?
        order by symbol
        """,
        (market, market),
    ).fetchall()
    matches = []
    for row in rows:
        item = row_to_dict(row)
        initials = pinyin_initials(item["name"])
        if initials == normalized:
            matches.append((0, item))
        elif initials.startswith(normalized):
            matches.append((1, item))
    if not matches:
        return None
    return sorted(matches, key=lambda item: (item[0], symbol_priority(item[1]["symbol"])))[0][1]


def symbol_priority(symbol: str) -> tuple[int, str]:
    return (0 if symbol == "688114.SH" else 1, symbol)


def infer_symbol(value: str) -> str | None:
    clean = value.strip().upper().replace(" ", "")
    if not clean:
        return None
    if "." in clean:
        return clean
    if clean.isdigit() and len(clean) == 6:
        if clean.startswith(("5", "6", "9")):
            return f"{clean}.SH"
        if clean.startswith(("0", "2", "3")):
            return f"{clean}.SZ"
        if clean.startswith(("4", "8")):
            return f"{clean}.BJ"
    if clean.isdigit() and len(clean) <= 5:
        return f"{clean.zfill(5)}.HK"
    return None


def market_from_symbol(symbol: str) -> str:
    upper = symbol.upper()
    if upper.endswith((".SH", ".SZ", ".BJ")):
        return "A"
    if upper.endswith(".HK"):
        return "HK"
    return "US"


def normalize_market(market: str) -> str:
    clean = market.strip().upper()
    return clean if clean in {"A", "HK", "US"} else "ALL"


def compact_query(value: str) -> str:
    return "".join(str(value).strip().lower().split())
