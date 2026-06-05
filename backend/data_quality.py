from __future__ import annotations

from typing import Any

from .db import DB_PATH, now_iso


def health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "mock-sqlite",
        "database": str(DB_PATH),
        "checked_at": now_iso(),
        "freshness_gate": "mock_pass",
    }


def refresh_payload() -> dict[str, Any]:
    return {
        "status": "queued",
        "mode": "mock",
        "refreshed_at": now_iso(),
        "note": "真实版本会进入 provider refresh queue；当前只通知前端刷新本地 mock 价格。",
    }
