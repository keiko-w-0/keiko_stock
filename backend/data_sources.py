from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from fastapi import HTTPException

from .db import now_iso, row_to_dict
from .providers.alpha_vantage import (
    alpha_vantage_api_key,
    clear_runtime_alpha_vantage_key,
    configure_runtime_alpha_vantage_key,
)
from .schemas import DataSourceUpdate


DEFAULT_ACCOUNT_ID = "acct-admin"


SOURCE_KIND_LABELS = {
    "market": "行情",
    "financial": "财务/估值",
    "filing": "公告/披露",
    "news": "新闻情绪",
}

PROVIDER_TOKEN_ENVS = {
    "alpha_vantage": ("ALPHA_VANTAGE_API_KEY", "ALPHAVANTAGE_API_KEY", "ALPHA_VANTAGE_KEY"),
    "tushare": ("KEIKO_TUSHARE_TOKEN", "TUSHARE_TOKEN"),
    "finnhub": ("KEIKO_FINNHUB_TOKEN", "FINNHUB_API_KEY"),
}

SHARED_CREDENTIAL_PROVIDERS = {"alpha_vantage", "tushare", "finnhub"}


def list_data_sources(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    credential_hints = credential_hint_map(conn, account_id)
    enabled_overrides = enabled_override_map(conn, account_id)
    reliability = data_source_reliability_map(conn)
    sources = [
        attach_source_reliability(normalize_source(row, credential_hints, enabled_overrides), reliability)
        for row in conn.execute("select * from data_source_configs order by market, source_kind, id")
    ]
    return {
        "mode": "provider-config",
        "account_id": account_id,
        "sources": sources,
        "summary": source_summary(sources),
        "reliability": reliability_summary(sources),
        "note": "配置会按账户控制 provider 是否进入分析；凭据只保存在本地账户私有表或环境变量中。",
    }


def update_data_source(
    conn: sqlite3.Connection,
    source_id: str,
    payload: DataSourceUpdate,
    account_id: str = DEFAULT_ACCOUNT_ID,
) -> dict[str, Any]:
    if not conn.execute("select 1 from accounts where id = ?", (account_id,)).fetchone():
        raise HTTPException(status_code=404, detail="account not found")

    row = conn.execute("select * from data_source_configs where id = ?", (source_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="data source not found")

    source = row_to_dict(row)
    credential = payload.credential.strip()
    scoped_source_ids = credential_scope_source_ids(conn, source)

    if payload.enabled is not None:
        conn.execute(
            """
            insert into data_source_account_settings (account_id, source_id, enabled, updated_at)
            values (?, ?, ?, ?)
            on conflict(account_id, source_id) do update set
              enabled = excluded.enabled,
              updated_at = excluded.updated_at
            """,
            (account_id, source_id, int(payload.enabled), now_iso()),
        )

    if payload.clear_credential:
        conn.executemany(
            "delete from data_source_credentials where account_id = ? and source_id = ?",
            [(account_id, item) for item in scoped_source_ids],
        )
        if source["provider"] == "alpha_vantage":
            clear_runtime_alpha_vantage_key()
    elif credential:
        if source["provider"] == "alpha_vantage":
            configure_runtime_alpha_vantage_key(credential)
        store_credential(conn, account_id, scoped_source_ids, credential)

    return list_data_sources(conn, account_id)


def active_source_kinds_by_market(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, set[str]]:
    active: dict[str, set[str]] = {}
    for source in list_data_sources(conn, account_id)["sources"]:
        if source["active"]:
            active.setdefault(source["market"], set()).add(source["source_kind"])
    return active


def active_source_ids(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> set[str]:
    return {source["id"] for source in list_data_sources(conn, account_id)["sources"] if source["active"]}


def credential_for_source(conn: sqlite3.Connection, source_id: str, account_id: str = DEFAULT_ACCOUNT_ID) -> str:
    row = conn.execute("select id, provider from data_source_configs where id = ?", (source_id,)).fetchone()
    if not row:
        return ""

    env_value = env_token_for_provider(row["provider"])
    if env_value:
        return env_value

    credential = conn.execute(
        "select credential_value from data_source_credentials where account_id = ? and source_id = ?",
        (account_id, source_id),
    ).fetchone()
    if credential:
        return str(credential["credential_value"])

    shared = conn.execute(
        """
        select credential_value
        from data_source_credentials
        where account_id = ?
          and source_id in (select id from data_source_configs where provider = ?)
        order by updated_at desc
        limit 1
        """,
        (account_id, row["provider"]),
    ).fetchone()
    return str(shared["credential_value"]) if shared else ""


def tushare_token(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> str:
    return credential_for_source(conn, "cn-tushare-market", account_id) or credential_for_source(
        conn, "cn-tushare-financial", account_id
    )


def finnhub_token(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> str:
    return (
        credential_for_source(conn, "us-finnhub-market", account_id)
        or credential_for_source(conn, "us-finnhub-financial", account_id)
        or credential_for_source(conn, "us-finnhub-news", account_id)
        or credential_for_source(conn, "hk-finnhub-market", account_id)
        or credential_for_source(conn, "hk-finnhub-financial", account_id)
    )


def alpha_vantage_token(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> str:
    return (
        credential_for_source(conn, "us-alpha-vantage-market", account_id)
        or credential_for_source(conn, "us-alpha-vantage-financial", account_id)
        or credential_for_source(conn, "us-alpha-vantage-news", account_id)
    )


def source_summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
    by_market: dict[str, dict[str, Any]] = {}
    for source in sources:
        market = source["market"]
        bucket = by_market.setdefault(market, {"total": 0, "active": 0, "missing_kinds": []})
        bucket["total"] += 1
        if source["active"]:
            bucket["active"] += 1

    for market, bucket in by_market.items():
        active_kinds = {
            source["source_kind"]
            for source in sources
            if source["market"] == market and source["active"]
        }
        bucket["missing_kinds"] = [
            kind for kind in ["market", "financial", "filing", "news"] if kind not in active_kinds
        ]
    return by_market


def attach_source_reliability(source: dict[str, Any], reliability: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source["reliability"] = reliability.get(source["id"], default_reliability(source))
    return source


def data_source_reliability_map(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    ingestion_groups = {
        "cn-akshare-market": ("akshare",),
        "cn-baostock-history": ("baostock",),
        "cn-baostock-financial": ("baostock",),
        "cn-tushare-market": ("tushare",),
        "cn-tushare-financial": ("tushare",),
        "cn-exchange-filings": ("cninfo_sse_szse", "cninfo", "sse", "szse"),
        "us-finnhub-market": ("finnhub",),
        "us-finnhub-financial": ("finnhub",),
        "us-finnhub-news": ("finnhub",),
        "hk-finnhub-market": ("finnhub",),
        "hk-finnhub-financial": ("finnhub",),
    }
    for source_id, providers in ingestion_groups.items():
        items[source_id] = ingestion_reliability(conn, source_id, providers)
    items["cn-xueqiu-community"] = community_reliability(conn, "cn-xueqiu-community", "xueqiu")
    return items


def ingestion_reliability(
    conn: sqlite3.Connection,
    source_id: str,
    providers: tuple[str, ...],
    limit: int = 20,
    scope_prefix: str = "",
) -> dict[str, Any]:
    placeholders = ", ".join("?" for _ in providers)
    params: list[Any] = [*providers]
    scope_filter = ""
    if scope_prefix:
        scope_filter = "and scope like ?"
        params.append(f"{scope_prefix}%")
    rows = conn.execute(
        f"""
        select provider, scope, status, started_at, finished_at, counts_json, errors_json
        from ingestion_runs
        where provider in ({placeholders})
          {scope_filter}
        order by coalesce(finished_at, started_at) desc, id desc
        limit ?
        """,
        (*params, limit),
    ).fetchall()
    if not rows:
        return default_reliability({"id": source_id})

    failures = 0
    latest_error = ""
    latest_at = ""
    for row in rows:
        status = str(row["status"] or "").lower()
        errors = parse_json(row["errors_json"], [])
        failed = status not in {"ok", "success"} or bool(errors)
        if failed:
            failures += 1
            latest_error = latest_error or first_error_text(errors) or status
        latest_at = latest_at or str(row["finished_at"] or row["started_at"] or "")

    total = len(rows)
    successes = max(0, total - failures)
    return reliability_payload(
        source_id,
        method="refresh_runs",
        total=total,
        successes=successes,
        failures=failures,
        latest_at=latest_at,
        latest_error=latest_error,
        note=f"最近 {total} 次刷新任务",
    )


def community_reliability(conn: sqlite3.Connection, source_id: str, source: str) -> dict[str, Any]:
    refresh_runs = ingestion_reliability(conn, source_id, (source,), scope_prefix="community-crawl")
    if refresh_runs.get("total"):
        if source == "xueqiu" and refresh_runs.get("failures") and not refresh_runs.get("latest_error"):
            refresh_runs["latest_error"] = "雪球评论最近没有成功入库记录，可能被 Cookie/WAF/浏览器会话阻断"
        return refresh_runs
    if source == "xueqiu":
        return reliability_payload(
            source_id,
            method="community_crawl_runs",
            total=1,
            successes=0,
            failures=1,
            latest_at="",
            latest_error="雪球评论还没有最近成功刷新任务，当前按 0% 成功率处理",
            note="雪球评论需最近刷新任务成功后才计入成功率",
        )

    row = conn.execute(
        """
        select count(*) as count, max(fetched_at) as latest_at
        from community_posts
        where source = ?
        """,
        (source,),
    ).fetchone()
    count = int(row["count"] or 0) if row else 0
    latest_at = str(row["latest_at"] or "") if row else ""
    if count > 0:
        return reliability_payload(
            source_id,
            method="community_posts",
            total=1,
            successes=1,
            failures=0,
            latest_at=latest_at,
            latest_error="",
            note=f"已成功入库 {count} 条评论",
        )
    error = "最近没有成功入库记录"
    if source == "xueqiu":
        error = "雪球评论最近没有成功入库记录，可能被 Cookie/WAF/浏览器会话阻断"
    return reliability_payload(
        source_id,
        method="community_posts",
        total=1,
        successes=0,
        failures=1,
        latest_at="",
        latest_error=error,
        note="社区源按最近是否有成功入库记录计算",
    )


def reliability_payload(
    source_id: str,
    *,
    method: str,
    total: int,
    successes: int,
    failures: int,
    latest_at: str,
    latest_error: str,
    note: str,
) -> dict[str, Any]:
    total = max(int(total or 0), 0)
    successes = max(int(successes or 0), 0)
    failures = max(int(failures or 0), 0)
    success_rate = round(successes / total * 100, 1) if total else None
    failure_rate = round(failures / total * 100, 1) if total else None
    return {
        "source_id": source_id,
        "method": method,
        "total": total,
        "successes": successes,
        "failures": failures,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "latest_at": latest_at,
        "latest_error": latest_error,
        "status": "warn" if failures else ("fresh" if total else "stale"),
        "note": note,
    }


def default_reliability(source: dict[str, Any]) -> dict[str, Any]:
    return reliability_payload(
        str(source.get("id") or ""),
        method="none",
        total=0,
        successes=0,
        failures=0,
        latest_at="",
        latest_error="暂无刷新记录",
        note="暂无刷新记录",
    )


def reliability_summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
    tracked = [source.get("reliability") or {} for source in sources if (source.get("reliability") or {}).get("total")]
    failures = [item for item in tracked if int_value(item.get("failures", 0)) > 0]
    success_total = sum(int_value(item.get("successes", 0)) for item in tracked)
    total = sum(int_value(item.get("total", 0)) for item in tracked)
    return {
        "tracked": len(tracked),
        "failure_sources": len(failures),
        "success_rate": round(success_total / total * 100, 1) if total else None,
        "failure_rate": round((total - success_total) / total * 100, 1) if total else None,
    }


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_json(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def first_error_text(errors: Any) -> str:
    if not isinstance(errors, list) or not errors:
        return ""
    first = errors[0]
    if isinstance(first, dict):
        return str(first.get("error") or first.get("message") or first)
    return str(first)


def normalize_source(
    row: sqlite3.Row,
    credential_hints: dict[str, str] | None = None,
    enabled_overrides: dict[str, bool] | None = None,
) -> dict[str, Any]:
    item = row_to_dict(row)
    hint = (credential_hints or {}).get(item["id"], "")
    if enabled_overrides and item["id"] in enabled_overrides:
        item["enabled"] = enabled_overrides[item["id"]]
    if hint:
        item["credential_hint"] = hint
        item["configured"] = True
    item["requires_key"] = bool(item["requires_key"])
    item["enabled"] = bool(item["enabled"])
    item["configured"] = bool(item["configured"]) if not item["requires_key"] else bool(hint)
    item["active"] = item["enabled"] and item["configured"]
    item["source_kind_label"] = SOURCE_KIND_LABELS.get(item["source_kind"], item["source_kind"])
    return item


def mask_credential(value: str) -> str:
    if len(value) <= 6:
        return "******"
    return f"{value[:3]}...{value[-3:]}"


def credential_hint_map(conn: sqlite3.Connection, account_id: str) -> dict[str, str]:
    hints = {
        row["source_id"]: row["credential_hint"]
        for row in conn.execute(
            "select source_id, credential_hint from data_source_credentials where account_id = ?",
            (account_id,),
        )
    }
    for row in conn.execute("select id, provider from data_source_configs"):
        env_value = env_token_for_provider(row["provider"])
        if env_value:
            hints[row["id"]] = mask_credential(env_value)
    return hints


def enabled_override_map(conn: sqlite3.Connection, account_id: str) -> dict[str, bool]:
    return {
        row["source_id"]: bool(row["enabled"])
        for row in conn.execute(
            "select source_id, enabled from data_source_account_settings where account_id = ?",
            (account_id,),
        )
    }


def source_has_credential(conn: sqlite3.Connection, source: dict[str, Any], account_id: str) -> bool:
    if not source["requires_key"]:
        return True
    if env_token_for_provider(source["provider"]):
        return True
    return bool(credential_for_source(conn, source["id"], account_id))


def store_credential(conn: sqlite3.Connection, account_id: str, source_ids: list[str], credential: str) -> None:
    hint = mask_credential(credential)
    updated_at = now_iso()
    conn.executemany(
        """
        insert into data_source_credentials (account_id, source_id, credential_value, credential_hint, updated_at)
        values (?, ?, ?, ?, ?)
        on conflict(account_id, source_id) do update set
          credential_value = excluded.credential_value,
          credential_hint = excluded.credential_hint,
          updated_at = excluded.updated_at
        """,
        [(account_id, source_id, credential, hint, updated_at) for source_id in source_ids],
    )


def credential_scope_source_ids(conn: sqlite3.Connection, source: dict[str, Any]) -> list[str]:
    if source["provider"] not in SHARED_CREDENTIAL_PROVIDERS:
        return [source["id"]]
    return [
        row["id"]
        for row in conn.execute(
            "select id from data_source_configs where provider = ? order by id",
            (source["provider"],),
        )
    ]


def env_token_for_provider(provider: str) -> str:
    if provider == "alpha_vantage":
        return alpha_vantage_api_key()
    env_names = PROVIDER_TOKEN_ENVS.get(provider, ())
    for env_name in env_names:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return ""
