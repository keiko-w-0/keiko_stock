from __future__ import annotations

from typing import Any

from .db import now_iso


def health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "sqlite-provider-cache",
        "database": "provider-cache",
        "checked_at": now_iso(),
        "freshness_gate": "provider_cache_pass",
    }


def refresh_payload() -> dict[str, Any]:
    return {
        "status": "queued",
        "mode": "provider-refresh",
        "refreshed_at": now_iso(),
        "note": "刷新会优先进入已配置 provider；未配置 provider 时只刷新本地缓存价格。",
    }
