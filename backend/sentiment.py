from __future__ import annotations

import json
import math
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from .db import ROOT_DIR, now_iso, row_to_dict
from .providers.community import crawl_community_posts, upsert_community_posts
from .stock_detail import preferred_daily_bars
from .symbol_resolver import infer_symbol, resolve_symbol


SENTIMENT_METHOD_VERSION = "sentiment-v1"
LOCAL_MODEL_NAME = "rule-v1"
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
DEEPSEEK_ENV_NAMES = ("DEEPSEEK_API_KEY", "KEIKO_DEEPSEEK_API_KEY")
GLM_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_ENV_NAMES = ("GLM_API_KEY", "ZHIPU_API_KEY", "BIGMODEL_API_KEY", "KEIKO_GLM_API_KEY")
ENV_FILE = ROOT_DIR / ".env"
DEFAULT_COMMUNITY_LIMIT = 120
DEFAULT_SENTIMENT_EVIDENCE_LIMIT = 120
LLM_BATCH_SIZE = 24


@dataclass(frozen=True)
class KeywordRule:
    keyword: str
    score: float
    category: str
    impact_horizon: str


KEYWORD_RULES: tuple[KeywordRule, ...] = (
    KeywordRule("回购", 42, "capital_action", "1w"),
    KeywordRule("增持", 38, "capital_action", "1w"),
    KeywordRule("中标", 34, "order_contract", "1q"),
    KeywordRule("签订合同", 34, "order_contract", "1q"),
    KeywordRule("战略合作", 24, "business_progress", "1q"),
    KeywordRule("股权激励", 20, "governance", "1q"),
    KeywordRule("预增", 42, "earnings", "1q"),
    KeywordRule("扭亏", 40, "earnings", "1q"),
    KeywordRule("同比增长", 24, "earnings", "1q"),
    KeywordRule("利润分配", 18, "shareholder_return", "1m"),
    KeywordRule("现金分红", 24, "shareholder_return", "1m"),
    KeywordRule("审核通过", 24, "approval", "1m"),
    KeywordRule("解除质押", 18, "pledge", "1w"),
    KeywordRule("减持", -36, "capital_action", "1w"),
    KeywordRule("拟减持", -42, "capital_action", "1w"),
    KeywordRule("被减持", -30, "capital_action", "1w"),
    KeywordRule("立案", -58, "regulatory", "1m"),
    KeywordRule("处罚", -52, "regulatory", "1m"),
    KeywordRule("行政处罚", -62, "regulatory", "1q"),
    KeywordRule("监管函", -36, "regulatory", "1m"),
    KeywordRule("问询函", -28, "regulatory", "1w"),
    KeywordRule("关注函", -26, "regulatory", "1w"),
    KeywordRule("乱象", -30, "public_opinion", "1w"),
    KeywordRule("管控短板", -24, "public_opinion", "1w"),
    KeywordRule("短板", -18, "public_opinion", "1w"),
    KeywordRule("投诉", -24, "public_opinion", "1w"),
    KeywordRule("造假", -66, "public_opinion", "1q"),
    KeywordRule("虚假", -44, "public_opinion", "1m"),
    KeywordRule("暴露", -16, "public_opinion", "1w"),
    KeywordRule("诉讼", -34, "legal", "1q"),
    KeywordRule("仲裁", -34, "legal", "1q"),
    KeywordRule("冻结", -44, "legal", "1m"),
    KeywordRule("质押", -18, "pledge", "1m"),
    KeywordRule("违约", -58, "credit", "1q"),
    KeywordRule("债务逾期", -62, "credit", "1q"),
    KeywordRule("风险提示", -34, "risk", "1w"),
    KeywordRule("退市风险", -70, "risk", "1q"),
    KeywordRule("ST", -54, "risk", "1q"),
    KeywordRule("预亏", -52, "earnings", "1q"),
    KeywordRule("亏损", -36, "earnings", "1q"),
    KeywordRule("下修", -32, "earnings", "1m"),
    KeywordRule("终止", -30, "business_progress", "1m"),
    KeywordRule("取消", -22, "business_progress", "1w"),
)

COMMUNITY_POSITIVE_WORDS = {"看多", "利好", "突破", "涨停", "主升", "低估", "加仓", "抄底", "反转", "超预期"}
COMMUNITY_NEGATIVE_WORDS = {"看空", "利空", "跌停", "出货", "踩雷", "割肉", "暴雷", "高估", "破位", "减仓"}


def refresh_sentiment(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    days: int = 30,
    use_llm: bool = True,
    crawl_community: bool = False,
    community_limit: int = DEFAULT_COMMUNITY_LIMIT,
    evidence_limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
) -> dict[str, Any]:
    target_symbols = normalize_symbols(conn, symbols or [])
    if not target_symbols:
        target_symbols = sentiment_candidate_symbols(conn, limit=80, days=days)

    counts = {
        "symbols": 0,
        "filing_news_evidence": 0,
        "community_evidence": 0,
        "market_evidence": 0,
        "community_posts": 0,
        "snapshots": 0,
    }
    errors: list[dict[str, str]] = []
    refreshed: list[str] = []

    for symbol in target_symbols:
        try:
            if crawl_community:
                crawl = crawl_community_for_symbols(conn, [symbol], limit=community_limit)
                counts["community_posts"] += int(crawl["counts"].get("posts", 0))
                errors.extend(crawl.get("errors") or [])
            result = refresh_symbol_sentiment(
                conn,
                symbol,
                days=days,
                use_llm=use_llm,
                evidence_limit=evidence_limit,
            )
            for key in ("filing_news_evidence", "community_evidence", "market_evidence", "snapshots"):
                counts[key] += int(result["counts"].get(key, 0))
            counts["symbols"] += 1
            refreshed.append(symbol)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": str(exc)})

    conn.commit()
    return {
        "mode": "sentiment-refresh",
        "method_version": SENTIMENT_METHOD_VERSION,
        "days": clean_days(days),
        "use_llm": bool(use_llm),
        "llm_configured": bool(preferred_llm_config()["configured"]),
        "llm_provider": preferred_llm_config()["provider"],
        "symbols": refreshed,
        "counts": counts,
        "errors": errors,
        "refreshed_at": now_iso(),
    }


def refresh_symbol_sentiment(
    conn: sqlite3.Connection,
    symbol: str,
    days: int = 30,
    use_llm: bool = True,
    evidence_limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
) -> dict[str, Any]:
    normalized = normalize_symbol(conn, symbol)
    if not normalized:
        raise HTTPException(status_code=404, detail="symbol not found")

    filing_news_count = analyze_filing_news_sentiment(conn, normalized, days=days, use_llm=use_llm, limit=evidence_limit)
    community_count = analyze_community_sentiment(conn, normalized, days=days, use_llm=use_llm, limit=evidence_limit)
    market_count = analyze_market_sentiment(conn, normalized, days=days)
    snapshot = upsert_sentiment_snapshot(conn, normalized, days=days)
    return {
        "symbol": normalized,
        "snapshot": snapshot,
        "counts": {
            "filing_news_evidence": filing_news_count,
            "community_evidence": community_count,
            "market_evidence": market_count,
            "snapshots": 1 if snapshot else 0,
        },
    }


def sentiment_payload(conn: sqlite3.Connection, symbol: str, days: int = 30, evidence_limit: int = 30) -> dict[str, Any]:
    normalized = normalize_symbol(conn, symbol)
    if not normalized:
        raise HTTPException(status_code=404, detail="symbol not found")
    symbol_row = conn.execute("select * from symbols where symbol = ?", (normalized,)).fetchone()
    snapshot_row = conn.execute(
        """
        select *
        from sentiment_snapshots
        where symbol = ? and window_days = ? and method_version = ?
        order by generated_at desc, id desc
        limit 1
        """,
        (normalized, clean_days(days), SENTIMENT_METHOD_VERSION),
    ).fetchone()
    evidence = sentiment_evidence_payload(conn, normalized, days=days, limit=evidence_limit)
    return {
        "mode": "sentiment-payload",
        "symbol": row_to_dict(symbol_row) if symbol_row else {"symbol": normalized},
        "snapshot": decode_snapshot(snapshot_row) if snapshot_row else None,
        "evidence": evidence,
        "data_status": {
            "has_snapshot": bool(snapshot_row),
            "evidence_rows": sum(len(items) for items in evidence.values()),
            "window_days": clean_days(days),
        },
    }


def sentiment_status(conn: sqlite3.Connection) -> dict[str, Any]:
    latest_snapshots = conn.execute(
        """
        select symbol, max(generated_at) as latest_generated_at, count(*) as snapshots
        from sentiment_snapshots
        group by symbol
        order by latest_generated_at desc
        limit 20
        """
    ).fetchall()
    return {
        "mode": "sentiment-status",
        "method_version": SENTIMENT_METHOD_VERSION,
        "llm": llm_config_status(mask=True),
        "counts": {
            "community_posts": scalar_count(conn, "community_posts"),
            "sentiment_evidence": scalar_count(conn, "sentiment_evidence"),
            "sentiment_snapshots": scalar_count(conn, "sentiment_snapshots"),
        },
        "latest_snapshots": [row_to_dict(row) for row in latest_snapshots],
    }


def crawl_community_for_symbols(
    conn: sqlite3.Connection,
    symbols: list[str],
    source: str = "eastmoney_guba",
    limit: int = DEFAULT_COMMUNITY_LIMIT,
    timeout: int = 15,
    sleep_seconds: float = 0.8,
) -> dict[str, Any]:
    target_symbols = normalize_symbols(conn, symbols)
    counts = {"symbols": 0, "posts": 0}
    errors: list[dict[str, str]] = []
    for symbol in target_symbols:
        try:
            payload = crawl_community_posts(
                symbol,
                source=source,
                limit=limit,
                timeout=timeout,
                sleep_seconds=sleep_seconds,
            )
            inserted = upsert_community_posts(conn, payload.get("posts") or [])
            counts["posts"] += inserted
            counts["symbols"] += 1
        except Exception as exc:
            errors.append({"symbol": symbol, "source": source, "error": str(exc)})
    conn.commit()
    return {
        "mode": "community-crawl",
        "source": source,
        "symbols": target_symbols,
        "counts": counts,
        "errors": errors,
        "fetched_at": now_iso(),
    }


def analyze_filing_news_sentiment(
    conn: sqlite3.Connection,
    symbol: str,
    days: int = 30,
    use_llm: bool = True,
    limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
) -> int:
    rows = filing_news_candidates(conn, symbol, days=days, limit=limit)
    analyzed = 0
    for result in analyze_text_items(rows, use_llm=use_llm):
        upsert_sentiment_evidence(conn, result)
        analyzed += 1
    return analyzed


def analyze_community_sentiment(
    conn: sqlite3.Connection,
    symbol: str,
    days: int = 30,
    use_llm: bool = True,
    limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
) -> int:
    cutoff = cutoff_date(days)
    rows = conn.execute(
        """
        select id, symbol, source, title, content, url, published_at, fetched_at, metrics_json
        from community_posts
        where symbol = ?
          and coalesce(nullif(substr(published_at, 1, 10), ''), substr(fetched_at, 1, 10)) >= ?
        order by coalesce(nullif(published_at, ''), fetched_at) desc, id desc
        limit ?
        """,
        (symbol, cutoff, clean_limit(limit, 200)),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        text = " ".join(part for part in [row["title"], row["content"]] if part)
        items.append(
            {
                "symbol": symbol,
                "sentiment_type": "community",
                "source_table": "community_posts",
                "source_id": str(row["id"]),
                "source": row["source"],
                "event_date": row["published_at"] or row["fetched_at"],
                "title": row["title"],
                "url": row["url"],
                "category": "community_discussion",
                "text": text,
                "source_tier": "C",
                "extra": {"metrics": parse_json(row["metrics_json"], {})},
            }
        )
    analyzed = 0
    for result in analyze_text_items(items, use_llm=use_llm, community=True):
        upsert_sentiment_evidence(conn, result)
        analyzed += 1
    return analyzed


def analyze_market_sentiment(conn: sqlite3.Connection, symbol: str, days: int = 30) -> int:
    symbol_row = conn.execute("select * from symbols where symbol = ?", (symbol,)).fetchone()
    if not symbol_row:
        return 0
    bars = preferred_daily_bars(conn, symbol, row_to_dict(symbol_row), limit=max(60, clean_days(days) + 30))
    if len(bars) < 2:
        return 0
    result = market_sentiment_result(symbol, bars, days=days)
    upsert_sentiment_evidence(conn, result)
    return 1


def filing_news_candidates(conn: sqlite3.Connection, symbol: str, days: int = 30, limit: int = 80) -> list[dict[str, Any]]:
    cutoff = cutoff_date(days)
    clean = clean_limit(limit, 200)
    candidates: list[dict[str, Any]] = []
    for row in conn.execute(
        """
        select id, symbol, source, source_tier, title, url, published_at, category
        from filings_history
        where symbol = ?
          and lower(source) not like '%mock%'
          and substr(published_at, 1, 10) >= ?
        order by published_at desc, id desc
        limit ?
        """,
        (symbol, cutoff, clean),
    ).fetchall():
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "filings_history",
                "source_id": str(row["id"]),
                "source": row["source"],
                "source_tier": row["source_tier"],
                "event_date": row["published_at"],
                "title": row["title"],
                "url": row["url"],
                "category": row["category"] or "filing",
                "text": f"{row['title']} {row['category'] or ''}",
                "extra": {},
            }
        )
    for row in conn.execute(
        """
        select id, symbol, provider, report_type, title, summary, published_at
        from company_reports_history
        where symbol = ?
          and lower(provider) not like '%mock%'
          and coalesce(nullif(substr(published_at, 1, 10), ''), substr(fetched_at, 1, 10)) >= ?
        order by coalesce(nullif(published_at, ''), fetched_at) desc, id desc
        limit ?
        """,
        (symbol, cutoff, clean),
    ).fetchall():
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "company_reports_history",
                "source_id": str(row["id"]),
                "source": row["provider"],
                "source_tier": "S",
                "event_date": row["published_at"],
                "title": row["title"] or row["report_type"],
                "url": "",
                "category": f"company_report:{row['report_type']}",
                "text": " ".join(part for part in [row["title"], row["summary"], row["report_type"]] if part),
                "extra": {},
            }
        )
    for row in conn.execute(
        """
        select id, symbol, source, source_tier, title, url, published_at, summary, sentiment_score
        from news_items
        where symbol = ?
          and lower(source) not like '%mock%'
          and substr(published_at, 1, 10) >= ?
        order by published_at desc, id desc
        limit ?
        """,
        (symbol, cutoff, clean),
    ).fetchall():
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "news_items",
                "source_id": str(row["id"]),
                "source": row["source"],
                "source_tier": row["source_tier"],
                "event_date": row["published_at"],
                "title": row["title"],
                "url": row["url"],
                "category": "news",
                "text": " ".join(part for part in [row["title"], row["summary"]] if part),
                "extra": {"provider_sentiment_score": row["sentiment_score"]},
            }
        )
    candidates.extend(financial_metric_candidates(conn, symbol, limit=8))
    candidates.sort(key=lambda item: str(item.get("event_date") or ""), reverse=True)
    return candidates[:clean]


def financial_metric_candidates(conn: sqlite3.Connection, symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select *
        from financial_metrics_history
        where symbol = ?
          and lower(provider) not like '%mock%'
        order by report_period desc, fetched_at desc
        limit ?
        """,
        (symbol, limit),
    ).fetchall()
    candidates: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        raw = parse_json(item.get("raw_json"), {})
        if raw.get("status") == "no_data":
            continue
        score, details = score_financial_metrics(item)
        title = f"{item['report_period']} 基本面快照"
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "financial_metrics_history",
                "source_id": f"{item['symbol']}:{item['report_period']}:{item['provider']}",
                "source": item["provider"],
                "source_tier": "S",
                "event_date": normalize_financial_event_date(
                    item.get("announce_date") or item.get("report_period") or item.get("fetched_at")
                ),
                "title": title,
                "url": "",
                "category": "fundamental",
                "text": financial_metric_text(item),
                "extra": {"rule_score": score, "financial_details": details},
            }
        )
    return candidates


def analyze_text_items(items: list[dict[str, Any]], use_llm: bool = False, community: bool = False) -> list[dict[str, Any]]:
    results = [analyze_text_item(item, use_llm=False, community=community) for item in items]
    llm = preferred_llm_config()
    if not use_llm or not llm["configured"] or not results:
        return results

    batch_size = llm_batch_size()
    for offset in range(0, len(items), batch_size):
        chunk_items = items[offset : offset + batch_size]
        try:
            llm_rows = llm_analyze_text_batch(chunk_items)
        except Exception as exc:
            for result in results[offset : offset + batch_size]:
                result["evidence"] = {**dict(result.get("evidence") or {}), "llm_error": str(exc)[:300]}
            continue
        for llm_row in llm_rows:
            try:
                index = int(llm_row.get("index"))
            except (TypeError, ValueError):
                continue
            absolute_index = offset + index
            if 0 <= absolute_index < len(results):
                merge_llm_sentiment_result(results[absolute_index], llm_row, llm)
    return results


def analyze_text_item(item: dict[str, Any], use_llm: bool = False, community: bool = False) -> dict[str, Any]:
    text = str(item.get("text") or item.get("title") or "")
    local = local_text_sentiment(text, community=community)
    extra = dict(item.get("extra") or {})
    if item.get("category") == "fundamental" and "rule_score" in extra:
        local["sentiment_score"] = clamp_score(extra["rule_score"])
        local["sentiment_label"] = sentiment_label(local["sentiment_score"])
        local["category"] = "fundamental"
        local["impact_horizon"] = "1q"
        local["confidence"] = max(float(local["confidence"]), 0.64)

    result = {
        **item,
        **local,
        "model_provider": "local",
        "model_name": LOCAL_MODEL_NAME,
        "method_version": SENTIMENT_METHOD_VERSION,
        "analyzed_at": now_iso(),
    }
    llm = preferred_llm_config()
    if use_llm and llm["configured"]:
        try:
            llm_result = llm_analyze_text(text, title=str(item.get("title") or ""), category=str(item.get("category") or ""))
            merge_llm_sentiment_result(result, llm_result, llm)
        except Exception as exc:
            result["evidence"] = {**dict(result.get("evidence") or {}), "llm_error": str(exc)[:300]}
    return result


def merge_llm_sentiment_result(result: dict[str, Any], llm_result: dict[str, Any], llm: dict[str, Any]) -> None:
    result.update(
        {
            "sentiment_score": clamp_score(llm_result.get("sentiment_score", result["sentiment_score"])),
            "sentiment_label": sentiment_label(llm_result.get("sentiment_score", result["sentiment_score"])),
            "confidence": clamp_float(llm_result.get("confidence", result["confidence"]), 0.0, 1.0),
            "category": str(llm_result.get("category") or result.get("category") or ""),
            "impact_horizon": str(llm_result.get("impact_horizon") or result.get("impact_horizon") or ""),
            "keywords": safe_string_list(llm_result.get("keywords") or result.get("keywords") or []),
            "evidence": {**dict(result.get("evidence") or {}), "llm_reason": str(llm_result.get("reason") or "")[:500]},
            "model_provider": llm["provider"],
            "model_name": llm["model"],
        }
    )


def local_text_sentiment(text: str, community: bool = False) -> dict[str, Any]:
    normalized = text.upper()
    score = 0.0
    matches: list[dict[str, Any]] = []
    category_scores: dict[str, float] = {}
    horizons: dict[str, str] = {}
    for rule in KEYWORD_RULES:
        if rule.keyword.upper() in normalized:
            score += rule.score
            matches.append({"keyword": rule.keyword, "score": rule.score, "category": rule.category})
            category_scores[rule.category] = category_scores.get(rule.category, 0.0) + abs(rule.score)
            horizons[rule.category] = rule.impact_horizon

    if community:
        for word in COMMUNITY_POSITIVE_WORDS:
            if word in text:
                score += 12
                matches.append({"keyword": word, "score": 12, "category": "community_discussion"})
        for word in COMMUNITY_NEGATIVE_WORDS:
            if word in text:
                score -= 12
                matches.append({"keyword": word, "score": -12, "category": "community_discussion"})

    category = max(category_scores, key=category_scores.get) if category_scores else ("community_discussion" if community else "neutral")
    confidence = min(0.92, 0.38 + 0.09 * len(matches))
    if len(text) > 40:
        confidence += 0.04
    score = clamp_score(score)
    return {
        "sentiment_score": score,
        "sentiment_label": sentiment_label(score),
        "confidence": clamp_float(confidence, 0.25, 0.92),
        "impact_horizon": horizons.get(category, "1w" if community else "1m"),
        "category": category,
        "keywords": [item["keyword"] for item in matches[:10]],
        "evidence": {"rule_matches": matches[:12], "text_length": len(text)},
    }


def market_sentiment_result(symbol: str, bars: list[dict[str, Any]], days: int = 30) -> dict[str, Any]:
    latest = bars[-1]
    window = bars[-clean_days(days) :]
    close_latest = number(latest.get("close"))
    close_5 = number(bars[-6].get("close")) if len(bars) >= 6 else number(bars[0].get("close"))
    close_20 = number(bars[-21].get("close")) if len(bars) >= 21 else number(bars[0].get("close"))
    change_1d = number(latest.get("change_pct"), 0.0) or 0.0
    change_5d = pct_change(close_latest, close_5)
    change_20d = pct_change(close_latest, close_20)
    amount_ratio = latest_ratio(bars, "amount", lookback=20)
    volume_ratio = latest_ratio(bars, "volume", lookback=20)
    latest_turnover = number(latest.get("turnover_rate"), 0.0) or 0.0
    limit_up_days = sum(1 for bar in window if (number(bar.get("change_pct"), 0.0) or 0.0) >= 9.4)
    limit_down_days = sum(1 for bar in window if (number(bar.get("change_pct"), 0.0) or 0.0) <= -9.4)
    drawdown = max_drawdown(window)

    score = change_1d * 2.2 + change_5d * 1.4 + change_20d * 0.45
    if amount_ratio >= 2.0 and change_1d >= 2.0:
        score += 12
    if amount_ratio >= 2.0 and change_1d <= -2.0:
        score -= 14
    score += min(limit_up_days * 8, 24)
    score -= min(limit_down_days * 10, 30)
    if drawdown <= -18:
        score -= 12
    if latest_turnover >= 12 and change_1d < 0:
        score -= 8
    score = clamp_score(score)
    confidence = clamp_float(0.45 + min(len(window), 30) / 80 + min(abs(score), 60) / 220, 0.35, 0.9)
    details = {
        "latest_trade_date": latest.get("date"),
        "change_1d": change_1d,
        "change_5d": change_5d,
        "change_20d": change_20d,
        "amount_ratio_20d": amount_ratio,
        "volume_ratio_20d": volume_ratio,
        "turnover_rate": latest_turnover,
        "limit_up_days": limit_up_days,
        "limit_down_days": limit_down_days,
        "max_drawdown": drawdown,
        "bar_count": len(window),
    }
    return {
        "symbol": symbol,
        "sentiment_type": "market",
        "source_table": "daily_bars",
        "source_id": f"{symbol}:{latest.get('date') or latest.get('trade_date')}",
        "source": str(latest.get("provider") or "daily_bars"),
        "event_date": str(latest.get("date") or ""),
        "title": "交易型情绪",
        "url": "",
        "category": "market_behavior",
        "sentiment_score": score,
        "sentiment_label": sentiment_label(score),
        "confidence": confidence,
        "impact_horizon": "1w",
        "keywords": market_keywords(details),
        "evidence": details,
        "model_provider": "local",
        "model_name": LOCAL_MODEL_NAME,
        "method_version": SENTIMENT_METHOD_VERSION,
        "analyzed_at": now_iso(),
    }


def upsert_sentiment_evidence(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    conn.execute(
        """
        insert into sentiment_evidence (
          symbol, sentiment_type, source_table, source_id, source, event_date, title, url,
          category, sentiment_score, sentiment_label, confidence, impact_horizon,
          keywords_json, evidence_json, model_provider, model_name, method_version, analyzed_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(sentiment_type, source_table, source_id, method_version) do update set
          source = excluded.source,
          event_date = excluded.event_date,
          title = excluded.title,
          url = excluded.url,
          category = excluded.category,
          sentiment_score = excluded.sentiment_score,
          sentiment_label = excluded.sentiment_label,
          confidence = excluded.confidence,
          impact_horizon = excluded.impact_horizon,
          keywords_json = excluded.keywords_json,
          evidence_json = excluded.evidence_json,
          model_provider = excluded.model_provider,
          model_name = excluded.model_name,
          analyzed_at = excluded.analyzed_at
        """,
        (
            str(item.get("symbol") or "").upper(),
            str(item.get("sentiment_type") or ""),
            str(item.get("source_table") or ""),
            str(item.get("source_id") or ""),
            str(item.get("source") or ""),
            str(item.get("event_date") or "")[:32],
            str(item.get("title") or "")[:500],
            str(item.get("url") or "")[:1000],
            str(item.get("category") or "")[:120],
            float(item.get("sentiment_score") or 0),
            sentiment_label(item.get("sentiment_score") or 0),
            clamp_float(item.get("confidence"), 0.0, 1.0),
            str(item.get("impact_horizon") or "")[:40],
            json.dumps(safe_string_list(item.get("keywords") or []), ensure_ascii=False),
            json.dumps(item.get("evidence") or {}, ensure_ascii=False, default=str),
            str(item.get("model_provider") or "local"),
            str(item.get("model_name") or LOCAL_MODEL_NAME),
            str(item.get("method_version") or SENTIMENT_METHOD_VERSION),
            str(item.get("analyzed_at") or now_iso()),
        ),
    )


def upsert_sentiment_snapshot(conn: sqlite3.Connection, symbol: str, days: int = 30) -> dict[str, Any]:
    window_days = clean_days(days)
    cutoff = cutoff_date(window_days)
    rows = conn.execute(
        """
        select *
        from sentiment_evidence
        where symbol = ?
          and method_version = ?
          and lower(source) not like '%mock%'
          and coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) >= ?
        order by coalesce(nullif(event_date, ''), analyzed_at) desc, id desc
        """,
        (symbol, SENTIMENT_METHOD_VERSION, cutoff),
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {"filing_news": [], "community": [], "market": []}
    for row in rows:
        item = row_to_dict(row)
        grouped.setdefault(item["sentiment_type"], []).append(item)

    type_scores = {key: weighted_score(items, window_days) for key, items in grouped.items() if items}
    available_weights = {
        "filing_news": 0.40 if "filing_news" in type_scores else 0.0,
        "community": 0.25 if "community" in type_scores else 0.0,
        "market": 0.35 if "market" in type_scores else 0.0,
    }
    weight_sum = sum(available_weights.values()) or 1.0
    composite = sum(type_scores[key]["score"] * available_weights.get(key, 0.0) for key in type_scores) / weight_sum
    confidence = sum(type_scores[key]["confidence"] * available_weights.get(key, 0.0) for key in type_scores) / weight_sum
    source_counts = {key: len(value) for key, value in grouped.items()}
    generated_at = now_iso()
    as_of = latest_as_of(rows) or generated_at[:10]
    raw = {
        "type_scores": type_scores,
        "source_counts": source_counts,
        "method": "weighted recency-adjusted evidence average",
    }
    conn.execute(
        """
        insert into sentiment_snapshots (
          symbol, as_of, window_days, filing_news_score, community_score, market_score,
          composite_score, sentiment_label, confidence, source_counts_json,
          raw_json, method_version, generated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol, as_of, window_days, method_version) do update set
          filing_news_score = excluded.filing_news_score,
          community_score = excluded.community_score,
          market_score = excluded.market_score,
          composite_score = excluded.composite_score,
          sentiment_label = excluded.sentiment_label,
          confidence = excluded.confidence,
          source_counts_json = excluded.source_counts_json,
          raw_json = excluded.raw_json,
          generated_at = excluded.generated_at
        """,
        (
            symbol,
            as_of,
            window_days,
            type_scores.get("filing_news", {}).get("score"),
            type_scores.get("community", {}).get("score"),
            type_scores.get("market", {}).get("score"),
            composite,
            sentiment_label(composite),
            clamp_float(confidence, 0.0, 1.0),
            json.dumps(source_counts, ensure_ascii=False),
            json.dumps(raw, ensure_ascii=False, default=str),
            SENTIMENT_METHOD_VERSION,
            generated_at,
        ),
    )
    return {
        "symbol": symbol,
        "as_of": as_of,
        "window_days": window_days,
        "filing_news_score": type_scores.get("filing_news", {}).get("score"),
        "community_score": type_scores.get("community", {}).get("score"),
        "market_score": type_scores.get("market", {}).get("score"),
        "composite_score": composite,
        "sentiment_label": sentiment_label(composite),
        "confidence": clamp_float(confidence, 0.0, 1.0),
        "source_counts": source_counts,
        "generated_at": generated_at,
    }


def weighted_score(items: list[dict[str, Any]], window_days: int) -> dict[str, float]:
    weighted_total = 0.0
    weight_total = 0.0
    confidence_total = 0.0
    for item in items:
        score = float(item.get("sentiment_score") or 0.0)
        confidence = clamp_float(item.get("confidence"), 0.0, 1.0)
        recency = recency_weight(str(item.get("event_date") or item.get("analyzed_at") or ""), window_days)
        weight = max(0.1, confidence) * recency
        weighted_total += score * weight
        confidence_total += confidence * weight
        weight_total += weight
    if weight_total <= 0:
        return {"score": 0.0, "confidence": 0.0}
    return {
        "score": clamp_score(weighted_total / weight_total),
        "confidence": clamp_float(confidence_total / weight_total, 0.0, 1.0),
    }


def sentiment_evidence_payload(conn: sqlite3.Connection, symbol: str, days: int = 30, limit: int = 30) -> dict[str, list[dict[str, Any]]]:
    cutoff = cutoff_date(days)
    rows = conn.execute(
        """
        select *
        from sentiment_evidence
        where symbol = ?
          and method_version = ?
          and lower(source) not like '%mock%'
          and coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) >= ?
        order by coalesce(nullif(event_date, ''), analyzed_at) desc, abs(sentiment_score) desc, id desc
        limit ?
        """,
        (symbol, SENTIMENT_METHOD_VERSION, cutoff, clean_limit(limit, 200)),
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {"filing_news": [], "community": [], "market": []}
    for row in rows:
        item = row_to_dict(row)
        item["keywords"] = parse_json(item.pop("keywords_json"), [])
        item["evidence"] = parse_json(item.pop("evidence_json"), {})
        grouped.setdefault(item["sentiment_type"], []).append(item)
    return grouped


def decode_snapshot(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["source_counts"] = parse_json(item.pop("source_counts_json"), {})
    item["raw"] = parse_json(item.pop("raw_json"), {})
    return item


def score_financial_metrics(item: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    revenue_growth = percentish(item.get("revenue_growth"))
    roe = percentish(item.get("roe"))
    gross_margin = percentish(item.get("gross_margin"))
    net_margin = percentish(item.get("net_margin"))
    debt_ratio = percentish(item.get("debt_ratio") if item.get("debt_ratio") is not None else item.get("liability_to_asset"))
    net_profit = number(item.get("net_profit"))
    score = 0.0
    details = {
        "revenue_growth": revenue_growth,
        "roe": roe,
        "gross_margin": gross_margin,
        "net_margin": net_margin,
        "debt_ratio": debt_ratio,
        "net_profit": net_profit,
    }
    if revenue_growth is not None:
        score += clamp_float(revenue_growth, -60, 80) * 0.35
    if roe is not None:
        score += (roe - 8) * 1.4
    if net_margin is not None:
        score += (net_margin - 5) * 0.8
    elif gross_margin is not None:
        score += (gross_margin - 20) * 0.35
    if debt_ratio is not None and debt_ratio > 70:
        score -= (debt_ratio - 70) * 0.8
    if net_profit is not None and net_profit < 0:
        score -= 24
    return clamp_score(score), details


def financial_metric_text(item: dict[str, Any]) -> str:
    score, details = score_financial_metrics(item)
    fields = [f"{key}={value}" for key, value in details.items() if value is not None]
    return f"{item.get('report_period')} {item.get('provider')} 基本面评分 {score:.1f}; " + "; ".join(fields)


def normalize_financial_event_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return "-".join(match.groups())
    match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    match = re.search(r"(\d{4})\s*[Qq]\s*([1-4])", text)
    if match:
        year = int(match.group(1))
        quarter = int(match.group(2))
        month = quarter * 3
        day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
        return date(year, month, day).isoformat()
    return text[:10] if parse_date(text) else ""


def llm_analyze_text(text: str, title: str = "", category: str = "", timeout: int = 25) -> dict[str, Any]:
    config = preferred_llm_config()
    if not config["configured"]:
        raise RuntimeError("No LLM API key configured")
    return chat_completion_analyze_text(
        endpoint=config["endpoint"],
        api_key=config["api_key"],
        model=config["model"],
        text=text,
        title=title,
        category=category,
        timeout=timeout,
    )


def llm_analyze_text_batch(items: list[dict[str, Any]], timeout: int = 45) -> list[dict[str, Any]]:
    config = preferred_llm_config()
    if not config["configured"]:
        raise RuntimeError("No LLM API key configured")
    return chat_completion_analyze_text_batch(
        endpoint=config["endpoint"],
        api_key=config["api_key"],
        model=config["model"],
        items=items,
        timeout=timeout,
    )


def glm_analyze_text(text: str, title: str = "", category: str = "", timeout: int = 25) -> dict[str, Any]:
    api_key = glm_api_key()
    if not api_key:
        raise RuntimeError("GLM_API_KEY is not configured")
    return chat_completion_analyze_text(
        endpoint=glm_endpoint(),
        api_key=api_key,
        model=glm_model(),
        text=text,
        title=title,
        category=category,
        timeout=timeout,
    )


def deepseek_analyze_text(text: str, title: str = "", category: str = "", timeout: int = 25) -> dict[str, Any]:
    api_key = deepseek_api_key()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    return chat_completion_analyze_text(
        endpoint=deepseek_endpoint(),
        api_key=api_key,
        model=deepseek_model(),
        text=text,
        title=title,
        category=category,
        timeout=timeout,
    )


def chat_completion_analyze_text(
    endpoint: str,
    api_key: str,
    model: str,
    text: str,
    title: str = "",
    category: str = "",
    timeout: int = 25,
) -> dict[str, Any]:
    compact_text = re.sub(r"\s+", " ", text or "").strip()[:3500]
    prompt = (
        "你是A股投研情绪分类器。请只返回JSON对象，字段包括："
        "sentiment_score(-100到100), confidence(0到1), category, impact_horizon(1d/1w/1m/1q), "
        "keywords数组, reason。不要给买卖建议。"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"title": title, "category_hint": category, "text": compact_text},
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc
    payload = json.loads(body)
    content = str(payload.get("choices", [{}])[0].get("message", {}).get("content") or "{}")
    return parse_json_object(content)


def chat_completion_analyze_text_batch(
    endpoint: str,
    api_key: str,
    model: str,
    items: list[dict[str, Any]],
    timeout: int = 45,
) -> list[dict[str, Any]]:
    compact_items = []
    for index, item in enumerate(items):
        compact_text = re.sub(r"\s+", " ", str(item.get("text") or item.get("title") or "")).strip()[:900]
        compact_items.append(
            {
                "index": index,
                "title": str(item.get("title") or "")[:220],
                "category_hint": str(item.get("category") or "")[:80],
                "source": str(item.get("source") or "")[:80],
                "text": compact_text,
            }
        )
    prompt = (
        "你是A股投研情绪分类器。请只返回JSON对象，格式为"
        "{\"items\":[{\"index\":0,\"sentiment_score\":0,\"confidence\":0.5,"
        "\"category\":\"neutral\",\"impact_horizon\":\"1w\",\"keywords\":[],\"reason\":\"\"}]}。"
        "sentiment_score范围-100到100，confidence范围0到1，不要给买卖建议。"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({"items": compact_items}, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"LLM batch request failed: {exc}") from exc
    payload = json.loads(body)
    content = str(payload.get("choices", [{}])[0].get("message", {}).get("content") or "{}")
    parsed = parse_json_object(content)
    rows = parsed.get("items") or parsed.get("results") or []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def deepseek_api_key() -> str:
    for name in DEEPSEEK_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    values = dotenv_values()
    for name in DEEPSEEK_ENV_NAMES:
        value = values.get(name, "").strip()
        if value:
            os.environ[name] = value
            return value
    return ""


def deepseek_model() -> str:
    return os.environ.get("DEEPSEEK_MODEL", "").strip() or dotenv_values().get("DEEPSEEK_MODEL", "").strip() or "deepseek-chat"


def deepseek_endpoint() -> str:
    return os.environ.get("DEEPSEEK_API_BASE", "").strip() or dotenv_values().get("DEEPSEEK_API_BASE", "").strip() or DEEPSEEK_ENDPOINT


def glm_api_key() -> str:
    for name in GLM_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    values = dotenv_values()
    for name in GLM_ENV_NAMES:
        value = values.get(name, "").strip()
        if value:
            os.environ[name] = value
            return value
    return ""


def glm_model() -> str:
    return os.environ.get("GLM_MODEL", "").strip() or dotenv_values().get("GLM_MODEL", "").strip() or "glm-4.5-air"


def glm_endpoint() -> str:
    return os.environ.get("GLM_API_BASE", "").strip() or dotenv_values().get("GLM_API_BASE", "").strip() or GLM_ENDPOINT


def preferred_llm_config() -> dict[str, Any]:
    glm_key = glm_api_key()
    if glm_key:
        return {
            "provider": "glm",
            "configured": True,
            "api_key": glm_key,
            "model": glm_model(),
            "endpoint": glm_endpoint(),
        }
    deepseek_key = deepseek_api_key()
    if deepseek_key:
        return {
            "provider": "deepseek",
            "configured": True,
            "api_key": deepseek_key,
            "model": deepseek_model(),
            "endpoint": deepseek_endpoint(),
        }
    return {"provider": "", "configured": False, "api_key": "", "model": "", "endpoint": ""}


def llm_config_status(mask: bool = True) -> dict[str, Any]:
    preferred = preferred_llm_config()
    return {
        "preferred_provider": preferred["provider"],
        "preferred_configured": bool(preferred["configured"]),
        "glm": glm_config_status(mask=mask),
        "deepseek": deepseek_config_status(mask=mask),
    }


def glm_config_status(mask: bool = True) -> dict[str, Any]:
    key = glm_api_key()
    return {
        "configured": bool(key),
        "credential_hint": mask_secret(key) if key and mask else "",
        "env_names": list(GLM_ENV_NAMES),
        "model": glm_model(),
        "endpoint": glm_endpoint(),
    }


def deepseek_config_status(mask: bool = True) -> dict[str, Any]:
    key = deepseek_api_key()
    return {
        "configured": bool(key),
        "credential_hint": mask_secret(key) if key and mask else "",
        "env_names": list(DEEPSEEK_ENV_NAMES),
        "model": deepseek_model(),
        "endpoint": deepseek_endpoint(),
    }


def dotenv_values(path: Path = ENV_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def normalize_symbols(conn: sqlite3.Connection, symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        symbol = normalize_symbol(conn, raw)
        if symbol and symbol not in seen:
            normalized.append(symbol)
            seen.add(symbol)
    return normalized


def normalize_symbol(conn: sqlite3.Connection, raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    resolved = resolve_symbol(conn, text, "all")
    if resolved:
        return str(resolved["symbol"]).upper()
    return (infer_symbol(text.upper()) or text.upper()).strip()


def sentiment_candidate_symbols(conn: sqlite3.Connection, limit: int = 80, days: int = 30) -> list[str]:
    cutoff = cutoff_date(days)
    rows = conn.execute(
        """
        select symbol, max(latest_at) as latest_at
        from (
          select symbol, max(published_at) as latest_at from filings_history where substr(published_at, 1, 10) >= ? group by symbol
          union all
          select symbol, max(fetched_at) as latest_at from community_posts where substr(fetched_at, 1, 10) >= ? group by symbol
          union all
          select symbol, max(trade_date) as latest_at from daily_bars where trade_date >= ? group by symbol
        )
        group by symbol
        order by latest_at desc
        limit ?
        """,
        (cutoff, cutoff, cutoff, clean_limit(limit, 500)),
    ).fetchall()
    return [str(row["symbol"]).upper() for row in rows]


def scalar_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"select count(*) as count from {table}").fetchone()["count"])


def clean_days(days: int) -> int:
    return max(1, min(int(days or 30), 365))


def clean_limit(limit: int, upper: int) -> int:
    return max(1, min(int(limit or upper), upper))


def llm_batch_size() -> int:
    value = os.environ.get("KEIKO_SENTIMENT_LLM_BATCH_SIZE", "").strip()
    try:
        parsed = int(value)
    except ValueError:
        parsed = LLM_BATCH_SIZE
    return max(1, min(parsed, 50))


def cutoff_date(days: int) -> str:
    return (date.today() - timedelta(days=clean_days(days))).isoformat()


def parse_json(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return fallback


def parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, flags=re.S)
        if not match:
            return {}
        return json.loads(match.group(0))


def sentiment_label(score: Any) -> str:
    value = float(score or 0.0)
    if value >= 35:
        return "positive"
    if value <= -35:
        return "negative"
    if value >= 12:
        return "mild_positive"
    if value <= -12:
        return "mild_negative"
    return "neutral"


def clamp_score(value: Any) -> float:
    return clamp_float(value, -100.0, 100.0)


def clamp_float(value: Any, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.0
    if math.isnan(parsed) or math.isinf(parsed):
        parsed = 0.0
    return max(low, min(high, parsed))


def number(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def percentish(value: Any) -> float | None:
    parsed = number(value)
    if parsed is None:
        return None
    if -1.5 <= parsed <= 1.5:
        return parsed * 100
    return parsed


def pct_change(latest: float | None, previous: float | None) -> float:
    if latest is None or previous in (None, 0):
        return 0.0
    return (latest / previous - 1) * 100


def latest_ratio(bars: list[dict[str, Any]], key: str, lookback: int = 20) -> float:
    latest = number(bars[-1].get(key), 0.0) or 0.0
    previous = [number(bar.get(key)) for bar in bars[-lookback - 1 : -1]]
    usable = [item for item in previous if item not in (None, 0)]
    if not usable:
        return 1.0
    average = sum(float(item) for item in usable) / len(usable)
    return latest / average if average else 1.0


def max_drawdown(bars: list[dict[str, Any]]) -> float:
    peak: float | None = None
    drawdown = 0.0
    for bar in bars:
        close = number(bar.get("close"))
        if close is None:
            continue
        peak = close if peak is None else max(peak, close)
        if peak:
            drawdown = min(drawdown, (close / peak - 1) * 100)
    return drawdown


def market_keywords(details: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    if details.get("change_1d", 0) >= 3:
        keywords.append("单日强势")
    if details.get("change_1d", 0) <= -3:
        keywords.append("单日走弱")
    if details.get("amount_ratio_20d", 1) >= 2:
        keywords.append("放量")
    if details.get("limit_up_days", 0):
        keywords.append("涨停")
    if details.get("limit_down_days", 0):
        keywords.append("跌停")
    if details.get("max_drawdown", 0) <= -18:
        keywords.append("回撤较大")
    return keywords


def recency_weight(value: str, window_days: int) -> float:
    parsed = parse_date(value)
    if not parsed:
        return 0.55
    days_ago = max(0, (date.today() - parsed).days)
    return max(0.35, 1.0 - days_ago / max(1, window_days * 1.3))


def parse_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def latest_as_of(rows: list[sqlite3.Row]) -> str:
    dates = [str(row["event_date"] or "")[:10] for row in rows if parse_date(str(row["event_date"] or ""))]
    return max(dates) if dates else ""


def safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()][:20]


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "********"
    return f"{value[:3]}...{value[-4:]}"
