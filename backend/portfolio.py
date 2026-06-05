from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from .accounts import ensure_account_and_symbol, number_for_json, trades_for_account
from .db import now_iso


FX_TO_CNY = {
    "CNY": 1,
    "HKD": 0.92,
    "USD": 7.2,
}


MOCK_PRICES = {
    "002594.SZ": 214.36,
    "0700.HK": 391.8,
    "NVDA": 118.64,
    "600519.SH": 1518.2,
    "1810.HK": 29.72,
    "AAPL": 203.44,
}

PRICE_REFRESH_COUNT = 0
PRICE_DELTAS = [0.006, -0.003, 0.004, -0.002, 0.007, 0.001]


def account_portfolio(conn: sqlite3.Connection, account_id: str) -> dict[str, Any]:
    if not conn.execute("select 1 from accounts where id = ?", (account_id,)).fetchone():
        raise HTTPException(status_code=404, detail="account not found")

    trades = trades_for_account(conn, account_id)
    symbols = sorted({trade["symbol"] for trade in trades})
    positions = [
        position
        for position in (calculate_position(conn, account_id, symbol, trades) for symbol in symbols)
        if position["quantity"] > 0
    ]
    totals = portfolio_totals(positions)
    cache_positions(conn, account_id, positions)
    return {
        "account_id": account_id,
        "positions": positions,
        "totals": totals,
        "computed_at": now_iso(),
        "pricing_mode": "mock_latest_price",
    }


def symbols_for_account(conn: sqlite3.Connection, account_id: str) -> list[str]:
    if not conn.execute("select 1 from accounts where id = ?", (account_id,)).fetchone():
        raise HTTPException(status_code=404, detail="account not found")
    return [
        row["symbol"]
        for row in conn.execute(
            """
            select distinct symbol
            from account_trades
            where account_id = ?
            order by symbol
            """,
            (account_id,),
        )
    ]


def refresh_mock_prices(symbols: list[str]) -> dict[str, float]:
    global PRICE_REFRESH_COUNT
    PRICE_REFRESH_COUNT += 1
    updated: dict[str, float] = {}
    for index, symbol in enumerate(symbols):
        if symbol not in MOCK_PRICES:
            continue
        delta = PRICE_DELTAS[(PRICE_REFRESH_COUNT + index) % len(PRICE_DELTAS)]
        MOCK_PRICES[symbol] = round(MOCK_PRICES[symbol] * (1 + delta), 2)
        updated[symbol] = MOCK_PRICES[symbol]
    return updated


def calculate_position(
    conn: sqlite3.Connection,
    account_id: str,
    symbol: str,
    account_trades: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ensure_account_and_symbol(conn, account_id, symbol)
    stock = conn.execute("select symbol, name, currency, market from symbols where symbol = ?", (symbol,)).fetchone()
    trades = account_trades if account_trades is not None else trades_for_account(conn, account_id)
    symbol_trades = sorted(
        [trade for trade in trades if trade["symbol"] == symbol],
        key=lambda item: (item["date"], item["id"]),
    )

    quantity = 0.0
    cost_basis = 0.0
    realized_profit = 0.0
    total_buy_cost = 0.0

    for trade in symbol_trades:
        gross = float(trade["quantity"]) * float(trade["price"])
        fee = float(trade["fee"])
        if trade["side"] == "BUY":
            quantity += float(trade["quantity"])
            cost_basis += gross + fee
            total_buy_cost += gross + fee
            continue

        sell_quantity = min(float(trade["quantity"]), quantity)
        avg_cost = cost_basis / quantity if quantity > 0 else 0
        realized_cost = avg_cost * sell_quantity
        proceeds = sell_quantity * float(trade["price"]) - fee
        realized_profit += proceeds - realized_cost
        quantity -= sell_quantity
        cost_basis -= realized_cost

    currency = stock["currency"]
    current_price = MOCK_PRICES.get(symbol, symbol_trades[-1]["price"] if symbol_trades else 0)
    market_value = quantity * current_price
    unrealized_profit = market_value - cost_basis
    total_profit = realized_profit + unrealized_profit
    return_rate = (total_profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
    avg_cost = cost_basis / quantity if quantity > 0 else 0

    return {
        "symbol": symbol,
        "name": stock["name"],
        "market": stock["market"],
        "currency": currency,
        "quantity": number_for_json(quantity),
        "avg_cost": round(avg_cost, 4),
        "current_price": round(float(current_price), 4),
        "market_value": round(market_value, 4),
        "realized_profit": round(realized_profit, 4),
        "unrealized_profit": round(unrealized_profit, 4),
        "total_profit": round(total_profit, 4),
        "total_buy_cost": round(total_buy_cost, 4),
        "return_rate": round(return_rate, 4),
        "trade_count": len(symbol_trades),
        "last_trade": symbol_trades[-1] if symbol_trades else None,
    }


def portfolio_totals(positions: list[dict[str, Any]]) -> dict[str, Any]:
    by_currency: dict[str, dict[str, float]] = {}
    market_value_cny = 0.0
    profit_cny = 0.0
    buy_cost_cny = 0.0

    for position in positions:
        currency = position["currency"]
        values = by_currency.setdefault(currency, {"market_value": 0.0, "total_profit": 0.0, "total_buy_cost": 0.0})
        values["market_value"] += float(position["market_value"])
        values["total_profit"] += float(position["total_profit"])
        values["total_buy_cost"] += float(position["total_buy_cost"])
        fx = FX_TO_CNY.get(currency, 1)
        market_value_cny += float(position["market_value"]) * fx
        profit_cny += float(position["total_profit"]) * fx
        buy_cost_cny += float(position["total_buy_cost"]) * fx

    return {
        "position_count": len(positions),
        "by_currency": {
            currency: {key: round(value, 4) for key, value in values.items()}
            for currency, values in by_currency.items()
        },
        "market_value_cny": round(market_value_cny, 4),
        "profit_cny": round(profit_cny, 4),
        "buy_cost_cny": round(buy_cost_cny, 4),
        "return_rate": round((profit_cny / buy_cost_cny) * 100, 4) if buy_cost_cny > 0 else 0,
    }


def cache_positions(conn: sqlite3.Connection, account_id: str, positions: list[dict[str, Any]]) -> None:
    computed_at = now_iso()
    conn.execute("delete from account_positions_cache where account_id = ?", (account_id,))
    for position in positions:
        conn.execute(
            """
            insert into account_positions_cache (
              account_id, symbol, quantity, avg_cost, realized_pnl, unrealized_pnl, return_rate, computed_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(account_id, symbol) do update set
              quantity = excluded.quantity,
              avg_cost = excluded.avg_cost,
              realized_pnl = excluded.realized_pnl,
              unrealized_pnl = excluded.unrealized_pnl,
              return_rate = excluded.return_rate,
              computed_at = excluded.computed_at
            """,
            (
                account_id,
                position["symbol"],
                position["quantity"],
                position["avg_cost"],
                position["realized_profit"],
                position["unrealized_profit"],
                position["return_rate"],
                computed_at,
            ),
        )
