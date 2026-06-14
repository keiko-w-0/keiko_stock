from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from .db import now_iso, row_to_dict
from .schemas import TradeInput


def fetch_account(conn: sqlite3.Connection, account_id: str) -> dict[str, Any] | None:
    row = conn.execute("select * from accounts where id = ?", (account_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_accounts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in conn.execute("select * from accounts order by created_at, id")]


def ensure_account_and_symbol(conn: sqlite3.Connection, account_id: str, symbol: str) -> None:
    if not conn.execute("select 1 from accounts where id = ?", (account_id,)).fetchone():
        raise HTTPException(status_code=404, detail="account not found")
    if not conn.execute("select 1 from symbols where symbol = ?", (symbol,)).fetchone():
        raise HTTPException(status_code=404, detail="symbol not found")


def favorites_for_account(conn: sqlite3.Connection, account_id: str) -> list[str]:
    return [
        row["symbol"]
        for row in conn.execute(
            "select symbol from account_favorites where account_id = ? order by created_at",
            (account_id,),
        )
    ]


def favorite_symbols_for_accounts(conn: sqlite3.Connection, account_id: str | None = None) -> list[str]:
    if account_id:
        return [str(symbol).upper() for symbol in favorites_for_account(conn, account_id)]
    rows = conn.execute(
        """
        select distinct symbol
        from account_favorites
        order by symbol
        """
    ).fetchall()
    return [str(row["symbol"]).upper() for row in rows]


def trades_for_account(conn: sqlite3.Connection, account_id: str) -> list[dict[str, Any]]:
    return [
        normalize_trade(row)
        for row in conn.execute(
            """
            select id, symbol, side, trade_date, quantity, price, fee, currency
            from account_trades
            where account_id = ?
            order by trade_date, id
            """,
            (account_id,),
        )
    ]


def set_account_favorite(
    conn: sqlite3.Connection,
    account_id: str,
    symbol: str,
    favorite: bool,
    note: str = "",
) -> list[str]:
    ensure_account_and_symbol(conn, account_id, symbol)
    if favorite:
        conn.execute(
            """
            insert into account_favorites (account_id, symbol, created_at, note)
            values (?, ?, ?, ?)
            on conflict(account_id, symbol) do update set note = excluded.note
            """,
            (account_id, symbol, now_iso(), note),
        )
    else:
        conn.execute(
            "delete from account_favorites where account_id = ? and symbol = ?",
            (account_id, symbol),
        )
    return favorites_for_account(conn, account_id)


def add_account_trade(conn: sqlite3.Connection, account_id: str, payload: TradeInput) -> dict[str, Any]:
    symbol = payload.symbol.upper()
    side = payload.side.upper()
    if side not in {"BUY", "SELL"}:
        raise HTTPException(status_code=422, detail="side must be BUY or SELL")

    ensure_account_and_symbol(conn, account_id, symbol)
    currency = conn.execute("select currency from symbols where symbol = ?", (symbol,)).fetchone()["currency"]
    cursor = conn.execute(
        """
        insert into account_trades (
          account_id, symbol, side, trade_date, quantity, price, fee, currency, created_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            account_id,
            symbol,
            side,
            payload.date,
            payload.quantity,
            payload.price,
            payload.fee,
            currency,
            now_iso(),
        ),
    )
    row = conn.execute(
        """
        select id, symbol, side, trade_date, quantity, price, fee, currency
        from account_trades
        where id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return normalize_trade(row)


def normalize_trade(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["date"] = item.pop("trade_date")
    item["quantity"] = number_for_json(item["quantity"])
    item["price"] = float(item["price"])
    item["fee"] = float(item["fee"])
    return item


def number_for_json(value: float) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number
