from __future__ import annotations

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
    sources = [
        normalize_source(row, credential_hints, enabled_overrides)
        for row in conn.execute("select * from data_source_configs order by market, source_kind, id")
    ]
    return {
        "mode": "provider-config",
        "account_id": account_id,
        "sources": sources,
        "summary": source_summary(sources),
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
