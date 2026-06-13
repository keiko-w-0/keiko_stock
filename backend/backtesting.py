from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from math import sqrt
from statistics import mean, pstdev
from typing import Any

from . import seed_data
from .history import daily_bars_for_backtest
from .schemas import BacktestInput
from .sentiment import SENTIMENT_METHOD_VERSION, decode_community_daily


STRATEGIES = {
    "quality_momentum": {
        "label": "质量 + 动量",
        "thesis": "用基本面质量过滤，再用技术趋势和量能确认，适合验证“好公司加趋势确认”的研究假设。",
    },
    "catalyst_rotation": {
        "label": "催化轮动",
        "thesis": "偏向催化、情绪和量能，适合验证短期主题扩散，但对新闻真实性和交易成本更敏感。",
    },
    "defensive_quality": {
        "label": "防守质量",
        "thesis": "偏向现金流、低风险和证据可信度，适合验证弱市中回撤控制是否优于基准。",
    },
    "low_rumor": {
        "label": "低传闻高证据",
        "thesis": "排除未证实比例高的标的，验证证据质量对稳定性的影响。",
    },
}


def run_backtest(payload: BacktestInput, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    if conn is not None:
        database_result = run_database_backtest(payload, conn)
        if database_result is not None:
            return database_result

    symbols = symbols_for_market(payload.market)
    days = trading_days(payload.start_date, payload.end_date)
    if not symbols or len(days) < 8:
        return empty_result(payload, symbols, days)

    max_positions = min(payload.max_positions, len(symbols))
    fee_rate = (payload.fee_bps + payload.slippage_bps) / 10000
    rebalance_indexes = set(rebalance_indexes_for(days, payload.rebalance))
    prices = {symbol: synthetic_prices(symbol, len(days)) for symbol in symbols}

    equity = payload.initial_cash
    benchmark = payload.initial_cash
    peak = equity
    holdings: list[str] = []
    previous_holdings: list[str] = []
    turnover_events = 0
    daily_returns: list[float] = []
    benchmark_returns: list[float] = []
    curve: list[dict[str, Any]] = []
    rebalance_rows: list[dict[str, Any]] = []

    for index, current_day in enumerate(days):
        if index == 0 or index in rebalance_indexes or not holdings:
            holdings = rank_symbols(symbols, payload.strategy)[:max_positions]
            if previous_holdings:
                changed = len(set(holdings).symmetric_difference(previous_holdings))
                turnover_events += changed
                equity *= max(0, 1 - fee_rate * changed / max(max_positions, 1))
            previous_holdings = list(holdings)
            rebalance_rows.append(
                {
                    "date": current_day.isoformat(),
                    "holdings": [{"symbol": symbol, "weight": round(1 / max_positions, 4)} for symbol in holdings],
                    "reason": rebalance_reason(payload.strategy),
                }
            )

        if index == 0:
            curve.append({"date": current_day.isoformat(), "value": round(equity, 2), "drawdown": 0, "benchmark": round(benchmark, 2)})
            continue

        returns = [prices[symbol][index] / prices[symbol][index - 1] - 1 for symbol in holdings]
        daily_return = mean(returns) if returns else 0
        benchmark_return = mean(prices[symbol][index] / prices[symbol][index - 1] - 1 for symbol in symbols)
        equity *= 1 + daily_return
        benchmark *= 1 + benchmark_return
        peak = max(peak, equity)
        drawdown = equity / peak - 1 if peak else 0
        daily_returns.append(daily_return)
        benchmark_returns.append(benchmark_return)
        curve.append(
            {
                "date": current_day.isoformat(),
                "value": round(equity, 2),
                "drawdown": round(drawdown * 100, 2),
                "benchmark": round(benchmark, 2),
            }
        )

    total_return = equity / payload.initial_cash - 1
    benchmark_total_return = benchmark / payload.initial_cash - 1
    volatility = pstdev(daily_returns) * sqrt(252) if len(daily_returns) > 1 else 0
    annualized = (1 + total_return) ** (252 / max(len(daily_returns), 1)) - 1
    sharpe = annualized / volatility if volatility > 0 else 0
    max_drawdown = min((point["drawdown"] for point in curve), default=0) / 100
    win_rate = sum(1 for value in daily_returns if value > 0) / len(daily_returns) if daily_returns else 0

    return {
        "mode": "research-backtest",
        "run_id": f"bt-{payload.strategy}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "config": payload.model_dump(),
        "strategy": STRATEGIES.get(payload.strategy, STRATEGIES["quality_momentum"]),
        "summary": {
            "total_return": round(total_return * 100, 2),
            "annualized_return": round(annualized * 100, 2),
            "benchmark_return": round(benchmark_total_return * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate * 100, 2),
            "turnover_events": turnover_events,
            "trading_days": len(days),
        },
        "equity_curve": curve,
        "rebalance_log": rebalance_rows[-8:],
        "attribution": attribution_for(symbols, payload.strategy, daily_returns, benchmark_returns),
        "research_notes": research_notes(payload, symbols),
        "sentiment_panels": empty_sentiment_panels(),
    }


def run_database_backtest(payload: BacktestInput, conn: sqlite3.Connection) -> dict[str, Any] | None:
    bars = daily_bars_for_backtest(conn, payload.market, payload.start_date, payload.end_date)
    if len(bars) < 2:
        return None
    dates = sorted(set.intersection(*(set(item["trade_date"] for item in rows) for rows in bars.values())))
    if len(dates) < 8:
        return None

    by_symbol = {
        symbol: {row["trade_date"]: row for row in rows}
        for symbol, rows in bars.items()
    }
    symbols = list(by_symbol.keys())
    max_positions = min(payload.max_positions, len(symbols))
    fee_rate = (payload.fee_bps + payload.slippage_bps) / 10000
    rebalance_indexes = set(rebalance_indexes_for([datetime.strptime(day, "%Y-%m-%d").date() for day in dates], payload.rebalance))

    equity = payload.initial_cash
    benchmark = payload.initial_cash
    peak = equity
    holdings: list[str] = []
    previous_holdings: list[str] = []
    turnover_events = 0
    daily_returns: list[float] = []
    benchmark_returns: list[float] = []
    curve: list[dict[str, Any]] = []
    rebalance_rows: list[dict[str, Any]] = []

    for index, current_day in enumerate(dates):
        if index == 0 or index in rebalance_indexes or not holdings:
            holdings = rank_symbols_from_bars(symbols, by_symbol, current_day, payload.strategy)[:max_positions]
            if previous_holdings:
                changed = len(set(holdings).symmetric_difference(previous_holdings))
                turnover_events += changed
                equity *= max(0, 1 - fee_rate * changed / max(max_positions, 1))
            previous_holdings = list(holdings)
            rebalance_rows.append(
                {
                    "date": current_day,
                    "holdings": [{"symbol": symbol, "weight": round(1 / max_positions, 4)} for symbol in holdings],
                    "reason": rebalance_reason(payload.strategy),
                }
            )

        if index == 0:
            curve.append({"date": current_day, "value": round(equity, 2), "drawdown": 0, "benchmark": round(benchmark, 2)})
            continue

        previous_day = dates[index - 1]
        returns = [bar_return(by_symbol[symbol][previous_day], by_symbol[symbol][current_day]) for symbol in holdings]
        daily_return = mean(returns) if returns else 0
        benchmark_return = mean(bar_return(by_symbol[symbol][previous_day], by_symbol[symbol][current_day]) for symbol in symbols)
        equity *= 1 + daily_return
        benchmark *= 1 + benchmark_return
        peak = max(peak, equity)
        drawdown = equity / peak - 1 if peak else 0
        daily_returns.append(daily_return)
        benchmark_returns.append(benchmark_return)
        curve.append(
            {
                "date": current_day,
                "value": round(equity, 2),
                "drawdown": round(drawdown * 100, 2),
                "benchmark": round(benchmark, 2),
            }
        )

    total_return = equity / payload.initial_cash - 1
    benchmark_total_return = benchmark / payload.initial_cash - 1
    volatility = pstdev(daily_returns) * sqrt(252) if len(daily_returns) > 1 else 0
    annualized = (1 + total_return) ** (252 / max(len(daily_returns), 1)) - 1
    sharpe = annualized / volatility if volatility > 0 else 0
    max_drawdown = min((point["drawdown"] for point in curve), default=0) / 100
    win_rate = sum(1 for value in daily_returns if value > 0) / len(daily_returns) if daily_returns else 0

    return {
        "mode": "database-backtest",
        "run_id": f"bt-db-{payload.strategy}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "config": payload.model_dump(),
        "strategy": STRATEGIES.get(payload.strategy, STRATEGIES["quality_momentum"]),
        "summary": {
            "total_return": round(total_return * 100, 2),
            "annualized_return": round(annualized * 100, 2),
            "benchmark_return": round(benchmark_total_return * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe": round(sharpe, 2),
            "win_rate": round(win_rate * 100, 2),
            "turnover_events": turnover_events,
            "trading_days": len(dates),
        },
        "equity_curve": curve,
        "rebalance_log": rebalance_rows[-8:],
        "attribution": attribution_from_bars(symbols, by_symbol, dates[-1], payload.strategy),
        "sentiment_panels": backtest_sentiment_panels(conn, symbols, dates),
        "research_notes": [
            "本次回测读取 daily_bars 历史仓库，不使用合成价格。",
            "结果仍需继续补充复权因子、停复牌、涨跌停、分红拆股和更完整的交易成本模型。",
            f"本次数据库样本数 {len(symbols)}，最大持仓 {payload.max_positions}，换仓频率 {payload.rebalance}。",
        ],
    }


def empty_sentiment_panels() -> dict[str, Any]:
    return {
        "mode": "sentiment-panels-empty",
        "daily_kline": {"rows": [], "summary": {"rows": 0}},
        "realtime": {"rows": [], "summary": {"rows": 0}},
        "notes": ["本地 fallback 回测没有读取社区情绪日汇总。"],
    }


def backtest_sentiment_panels(conn: sqlite3.Connection, symbols: list[str], dates: list[str]) -> dict[str, Any]:
    rows = backtest_community_daily_kline_rows(conn, symbols, dates)
    realtime = backtest_realtime_sentiment_rows(conn, symbols)
    return {
        "mode": "community-sentiment-panels",
        "daily_kline": {
            "rows": rows,
            "summary": {
                "rows": len(rows),
                "symbols": len({row["symbol"] for row in rows}),
                "latest_trade_date": max((row["trade_date"] for row in rows), default=""),
            },
        },
        "realtime": {
            "rows": realtime,
            "summary": {
                "rows": len(realtime),
                "latest_trade_date": max((row.get("latest_trade_date") or "" for row in realtime), default=""),
                "latest_sentiment_at": max((row.get("latest_sentiment_at") or "" for row in realtime), default=""),
            },
        },
        "notes": [
            "社区情绪日汇总永久保留；单条评论原文和单条分析由 agent 按 3 天清理。",
            "半小时 agent 每轮刷新短窗口 K 线；财务不在社区情绪轮次重复拉取，公告通过 refresh_state 判断有缺口才拉。",
        ],
    }


def backtest_community_daily_kline_rows(
    conn: sqlite3.Connection,
    symbols: list[str],
    dates: list[str],
    limit: int = 14,
) -> list[dict[str, Any]]:
    if not symbols or not dates:
        return []
    symbol_placeholders = ",".join("?" for _ in symbols)
    start_date = min(dates)
    end_date = max(max(dates), date.today().isoformat())
    rows = conn.execute(
        f"""
        select csd.*, s.name
        from community_sentiment_daily csd
        left join symbols s on s.symbol = csd.symbol
        where csd.symbol in ({symbol_placeholders})
          and csd.method_version = ?
          and csd.trade_date between ? and ?
        order by csd.trade_date desc, abs(csd.sentiment_score) desc, csd.analyzed_count desc
        limit ?
        """,
        (*symbols, SENTIMENT_METHOD_VERSION, start_date, end_date, limit),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = decode_community_daily(row)
        bar = daily_bar_for_date(conn, item["symbol"], item["trade_date"])
        result.append(
            {
                "symbol": item["symbol"],
                "name": row["name"] or "",
                "trade_date": item["trade_date"],
                "analyzed_count": item["analyzed_count"],
                "positive_count": item["positive_count"],
                "negative_count": item["negative_count"],
                "neutral_count": item["neutral_count"],
                "sentiment_score": item["sentiment_score"],
                "sentiment_label": item["sentiment_label"],
                "confidence": item["confidence"],
                "conclusion": item["conclusion"],
                "keyword_counts": item["keyword_counts"],
                "close": bar.get("close"),
                "change_pct": bar.get("change_pct"),
                "amount": bar.get("amount"),
                "turnover_rate": bar.get("turnover_rate"),
                "kline_trade_date": bar.get("trade_date", ""),
                "kline_provider": bar.get("provider", ""),
                "kline_fetched_at": bar.get("fetched_at", ""),
            }
        )
    return result


def backtest_realtime_sentiment_rows(
    conn: sqlite3.Connection,
    symbols: list[str],
    limit: int = 8,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    target_symbols = prioritized_realtime_symbols(conn, symbols, limit=limit)
    for symbol in target_symbols:
        symbol_row = conn.execute("select name from symbols where symbol = ?", (symbol,)).fetchone()
        latest_bar = latest_daily_bar(conn, symbol)
        latest_snapshot = conn.execute(
            """
            select *
            from sentiment_snapshots
            where symbol = ?
              and method_version = ?
            order by generated_at desc, id desc
            limit 1
            """,
            (symbol, SENTIMENT_METHOD_VERSION),
        ).fetchone()
        latest_daily = conn.execute(
            """
            select *
            from community_sentiment_daily
            where symbol = ?
              and method_version = ?
            order by trade_date desc, generated_at desc, id desc
            limit 1
            """,
            (symbol, SENTIMENT_METHOD_VERSION),
        ).fetchone()
        today = date.today().isoformat()
        posts_today = conn.execute(
            """
            select count(*) as count
            from community_posts
            where symbol = ?
              and substr(fetched_at, 1, 10) = ?
            """,
            (symbol, today),
        ).fetchone()["count"]
        daily_item = decode_community_daily(latest_daily) if latest_daily else {}
        result.append(
            {
                "symbol": symbol,
                "name": symbol_row["name"] if symbol_row else "",
                "latest_trade_date": latest_bar.get("trade_date", ""),
                "latest_close": latest_bar.get("close"),
                "latest_change_pct": latest_bar.get("change_pct"),
                "kline_provider": latest_bar.get("provider", ""),
                "kline_fetched_at": latest_bar.get("fetched_at", ""),
                "latest_sentiment_at": latest_snapshot["generated_at"] if latest_snapshot else "",
                "composite_score": latest_snapshot["composite_score"] if latest_snapshot else None,
                "community_score": latest_snapshot["community_score"] if latest_snapshot else None,
                "sentiment_label": latest_snapshot["sentiment_label"] if latest_snapshot else "",
                "daily_trade_date": daily_item.get("trade_date", ""),
                "daily_analyzed_count": daily_item.get("analyzed_count", 0),
                "daily_positive_count": daily_item.get("positive_count", 0),
                "daily_negative_count": daily_item.get("negative_count", 0),
                "daily_neutral_count": daily_item.get("neutral_count", 0),
                "daily_conclusion": daily_item.get("conclusion", ""),
                "community_posts_today": int(posts_today or 0),
            }
        )
    result.sort(key=lambda row: (row.get("latest_sentiment_at") or "", abs(float(row.get("community_score") or 0))), reverse=True)
    return result


def prioritized_realtime_symbols(conn: sqlite3.Connection, symbols: list[str], limit: int = 8) -> list[str]:
    symbol_set = set(symbols)
    rows = conn.execute(
        """
        select symbol, max(generated_at) as latest_at
        from community_sentiment_daily
        where method_version = ?
        group by symbol
        order by latest_at desc
        limit ?
        """,
        (SENTIMENT_METHOD_VERSION, max(limit * 3, 20)),
    ).fetchall()
    prioritized: list[str] = []
    seen: set[str] = set()
    for row in rows:
        symbol = str(row["symbol"] or "").upper()
        if symbol in symbol_set and symbol not in seen:
            prioritized.append(symbol)
            seen.add(symbol)
    for symbol in symbols:
        if symbol not in seen:
            prioritized.append(symbol)
            seen.add(symbol)
        if len(prioritized) >= limit:
            break
    return prioritized[:limit]


def daily_bar_for_date(conn: sqlite3.Connection, symbol: str, trade_date: str) -> dict[str, Any]:
    rows = conn.execute(
        """
        select *
        from daily_bars
        where symbol = ?
          and trade_date <= ?
        order by trade_date desc
        limit 20
        """,
        (symbol, trade_date),
    ).fetchall()
    if not rows:
        return {}
    latest_date = rows[0]["trade_date"]
    same_day = [row for row in rows if row["trade_date"] == latest_date]
    row = max(same_day, key=daily_bar_rank)
    return dict(row)


def latest_daily_bar(conn: sqlite3.Connection, symbol: str) -> dict[str, Any]:
    rows = conn.execute(
        """
        select *
        from daily_bars
        where symbol = ?
        order by trade_date desc
        limit 20
        """,
        (symbol,),
    ).fetchall()
    if not rows:
        return {}
    latest_date = rows[0]["trade_date"]
    same_day = [row for row in rows if row["trade_date"] == latest_date]
    return dict(max(same_day, key=daily_bar_rank))


def daily_bar_rank(row: sqlite3.Row) -> tuple[Any, ...]:
    provider_priority = {
        "akshare-market": 5,
        "baostock-market": 4,
        "tushare-market": 3,
        "finnhub-market": 2,
        "mock-market": 1,
    }
    adjust_priority = {"qfq": 4, "hfq": 3, "": 2}
    return (
        provider_priority.get(str(row["provider"] or ""), 0),
        adjust_priority.get(str(row["adjust"] or "").lower(), 0),
        str(row["fetched_at"] or ""),
    )


def bar_return(previous: dict[str, Any], current: dict[str, Any]) -> float:
    prev_close = float(previous["close"] or 0)
    close = float(current["close"] or 0)
    return close / prev_close - 1 if prev_close > 0 else 0


def rank_symbols_from_bars(
    symbols: list[str],
    by_symbol: dict[str, dict[str, dict[str, Any]]],
    current_day: str,
    strategy: str,
) -> list[str]:
    return sorted(symbols, key=lambda symbol: bar_strategy_score(by_symbol[symbol][current_day], strategy), reverse=True)


def bar_strategy_score(row: dict[str, Any], strategy: str) -> float:
    amount_score = min(float(row.get("amount") or 0) / 100000000, 100)
    turnover_score = min(float(row.get("turnover_rate") or 0) * 10, 100)
    pe = float(row.get("pe_ttm") or 0)
    valuation_score = 50 if pe <= 0 else max(0, min(100, (100 - pe)))
    momentum_score = float(row.get("close") or 0)
    if strategy == "defensive_quality":
        return valuation_score * 0.5 + amount_score * 0.3 + turnover_score * 0.2
    if strategy == "catalyst_rotation":
        return turnover_score * 0.45 + amount_score * 0.35 + momentum_score * 0.02
    if strategy == "low_rumor":
        return amount_score * 0.5 + valuation_score * 0.3 + turnover_score * 0.2
    return amount_score * 0.35 + turnover_score * 0.25 + valuation_score * 0.25 + momentum_score * 0.02


def attribution_from_bars(
    symbols: list[str],
    by_symbol: dict[str, dict[str, dict[str, Any]]],
    current_day: str,
    strategy: str,
) -> dict[str, Any]:
    ranked = rank_symbols_from_bars(symbols, by_symbol, current_day, strategy)
    return {
        "leaders": [{"symbol": symbol, "score": round(bar_strategy_score(by_symbol[symbol][current_day], strategy), 2)} for symbol in ranked[:3]],
        "laggards": [{"symbol": symbol, "score": round(bar_strategy_score(by_symbol[symbol][current_day], strategy), 2)} for symbol in ranked[-3:]],
        "annualized_excess_vs_benchmark": 0,
        "main_driver": STRATEGIES.get(strategy, STRATEGIES["quality_momentum"])["label"],
    }


def symbols_for_market(market: str) -> list[str]:
    normalized = market.upper()
    symbols = []
    for item in seed_data.SYMBOLS:
        if normalized != "ALL" and item["market"] != normalized:
            continue
        if item["symbol"] in seed_data.STOCK_PROFILES:
            symbols.append(item["symbol"])
    return symbols


def trading_days(start_date: str, end_date: str) -> list[date]:
    start = parse_date(start_date, date(2026, 3, 2))
    end = parse_date(end_date, date(2026, 6, 5))
    if end < start:
        start, end = end, start
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def parse_date(value: str, fallback: date) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return fallback


def rebalance_indexes_for(days: list[date], mode: str) -> list[int]:
    if mode == "weekly":
        return [index for index, day in enumerate(days) if index == 0 or day.weekday() == 0]
    if mode == "daily":
        return list(range(len(days)))
    indexes = [0]
    last_month = days[0].month
    for index, day in enumerate(days):
        if day.month != last_month:
            indexes.append(index)
            last_month = day.month
    return indexes


def synthetic_prices(symbol: str, length: int) -> list[float]:
    profile = seed_data.STOCK_PROFILES[symbol]
    base_spark = profile["spark"]
    metrics = profile["metrics"]
    start_price = max(base_spark[0], 1)
    drift = (profile["score"] - 65) / 18000 + metrics["ma20_gap_pct"] / 25000
    risk_wave = metrics["volatility_20d"] / 10000
    prices = []
    price = start_price
    for index in range(length):
        spark_return = base_spark[index % len(base_spark)] / base_spark[max(index % len(base_spark) - 1, 0)] - 1 if index else 0
        wave = ((index % 7) - 3) * risk_wave
        price *= 1 + drift + spark_return * 0.16 + wave
        prices.append(round(max(price, 0.01), 4))
    return prices


def rank_symbols(symbols: list[str], strategy: str) -> list[str]:
    return sorted(symbols, key=lambda symbol: strategy_score(seed_data.STOCK_PROFILES[symbol], strategy), reverse=True)


def strategy_score(profile: dict[str, Any], strategy: str) -> float:
    factors = profile["factors"]
    metrics = profile["metrics"]
    if strategy == "catalyst_rotation":
        return factors["催化"] * 0.4 + factors["技术"] * 0.25 + factors["情绪"] * 0.2 + metrics["volume_ratio"] * 8 - metrics["unverified_ratio"] * 25
    if strategy == "defensive_quality":
        return factors["基本面"] * 0.35 + factors["风险"] * 0.28 + factors["估值"] * 0.17 + profile["truth_score"] * 0.2 - metrics["volatility_20d"] * 0.18
    if strategy == "low_rumor":
        return profile["truth_score"] * 0.42 + factors["风险"] * 0.2 + factors["基本面"] * 0.2 + (1 - metrics["unverified_ratio"]) * 30
    return factors["基本面"] * 0.28 + factors["技术"] * 0.28 + factors["催化"] * 0.2 + profile["truth_score"] * 0.14 + factors["估值"] * 0.1


def rebalance_reason(strategy: str) -> str:
    if strategy == "catalyst_rotation":
        return "按催化、量能和情绪强度重新排序。"
    if strategy == "defensive_quality":
        return "按质量、风险和估值稳定性重新排序。"
    if strategy == "low_rumor":
        return "按证据可信度和未证实比例重新排序。"
    return "按质量、趋势、催化和证据可信度综合排序。"


def attribution_for(symbols: list[str], strategy: str, returns: list[float], benchmark_returns: list[float]) -> dict[str, Any]:
    leaders = rank_symbols(symbols, strategy)[:3]
    laggards = rank_symbols(symbols, strategy)[-3:]
    excess = (mean(returns) - mean(benchmark_returns)) * 252 * 100 if returns and benchmark_returns else 0
    return {
        "leaders": [{"symbol": symbol, "score": round(strategy_score(seed_data.STOCK_PROFILES[symbol], strategy), 2)} for symbol in leaders],
        "laggards": [{"symbol": symbol, "score": round(strategy_score(seed_data.STOCK_PROFILES[symbol], strategy), 2)} for symbol in laggards],
        "annualized_excess_vs_benchmark": round(excess, 2),
        "main_driver": STRATEGIES.get(strategy, STRATEGIES["quality_momentum"])["label"],
    }


def research_notes(payload: BacktestInput, symbols: list[str]) -> list[str]:
    return [
        "当前为研究回测，只验证产品流程和指标展示，不代表真实历史收益。",
        "正式回测必须使用复权行情、交易日历、停复牌、涨跌停、分红拆股、交易成本和滑点模型。",
        "样本只包含当前股票池，不能据此判断策略有效性；生产回测需要足够多标的和更长历史区间。",
        f"本次样本数 {len(symbols)}，最大持仓 {payload.max_positions}，换仓频率 {payload.rebalance}。",
    ]


def empty_result(payload: BacktestInput, symbols: list[str], days: list[date]) -> dict[str, Any]:
    return {
        "mode": "research-backtest",
        "run_id": "bt-empty",
        "config": payload.model_dump(),
        "strategy": STRATEGIES.get(payload.strategy, STRATEGIES["quality_momentum"]),
        "summary": {
            "total_return": 0,
            "annualized_return": 0,
            "benchmark_return": 0,
            "max_drawdown": 0,
            "volatility": 0,
            "sharpe": 0,
            "win_rate": 0,
            "turnover_events": 0,
            "trading_days": len(days),
        },
        "equity_curve": [],
        "rebalance_log": [],
        "attribution": {"leaders": [], "laggards": [], "annualized_excess_vs_benchmark": 0, "main_driver": "N/A"},
        "research_notes": research_notes(payload, symbols),
    }
