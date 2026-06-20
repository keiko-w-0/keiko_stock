from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime with a clear message.
    requests = None  # type: ignore[assignment]

from ..db import DATA_DIR, configure_sqlite_connection, now_iso


IWENCAI_PROFILE_DB_PATH = DATA_DIR / "iwencai_profile.db"
IWENCAI_HEXIN_JS_URL = "https://raw.githubusercontent.com/zsrl/pywencai/main/pywencai/hexin-v.bundle.js"
IWENCAI_ROBOT_DATA_URL = "https://www.iwencai.com/unifiedwap/unified-wap/v2/result/get-robot-data"
IWENCAI_REFERER = "https://www.iwencai.com/screener/result?querytype=stock"
IWENCAI_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def get_iwencai_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or IWENCAI_PROFILE_DB_PATH).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    configure_sqlite_connection(conn)
    return conn


def init_iwencai_profile_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists iwencai_profiles (
          symbol text primary key,
          name text not null default '',
          market text not null default '',
          target_type text not null default '',
          question text not null default '',
          resolved_code text not null default '',
          summary text not null default '',
          highlights_json text not null default '[]',
          raw_sections_json text not null default '{}',
          status text not null,
          error text not null default '',
          fetched_at text not null,
          updated_at text not null
        );

        create table if not exists iwencai_profile_highlights (
          id integer primary key autoincrement,
          symbol text not null,
          label text not null default '',
          effect text not null default '',
          label_type text not null default '',
          row_hash text not null unique,
          raw_json text not null default '{}',
          fetched_at text not null
        );

        create table if not exists iwencai_important_events (
          id integer primary key autoincrement,
          symbol text not null,
          announcement_date text not null default '',
          event_name text not null default '',
          content text not null default '',
          row_hash text not null unique,
          raw_json text not null default '{}',
          fetched_at text not null
        );

        create table if not exists iwencai_concepts (
          id integer primary key autoincrement,
          symbol text not null,
          concept_name text not null default '',
          included_date text not null default '',
          concept_content text not null default '',
          generated_date text not null default '',
          row_hash text not null unique,
          raw_json text not null default '{}',
          fetched_at text not null
        );

        create table if not exists iwencai_crawl_state (
          symbol text primary key,
          name text not null default '',
          market text not null default '',
          target_type text not null default '',
          status text not null,
          attempts integer not null default 0,
          last_error text not null default '',
          fetched_at text not null default '',
          updated_at text not null
        );

        create table if not exists iwencai_crawl_runs (
          id integer primary key autoincrement,
          scope text not null,
          tier_order_json text not null default '[]',
          status text not null,
          started_at text not null,
          finished_at text,
          requested_count integer not null default 0,
          updated_count integer not null default 0,
          skipped_count integer not null default 0,
          failed_count integer not null default 0,
          counts_json text not null default '{}',
          errors_json text not null default '[]'
        );

        create index if not exists idx_iwencai_profiles_status
        on iwencai_profiles(status, fetched_at desc);

        create index if not exists idx_iwencai_events_symbol_date
        on iwencai_important_events(symbol, announcement_date desc);

        create index if not exists idx_iwencai_concepts_symbol_date
        on iwencai_concepts(symbol, included_date desc);

        create index if not exists idx_iwencai_state_status
        on iwencai_crawl_state(status, updated_at desc);
        """
    )


def read_iwencai_profile(
    symbol: str,
    *,
    db_path: str | Path | None = None,
    event_limit: int = 8,
    concept_limit: int = 12,
) -> dict[str, Any]:
    path = Path(db_path or IWENCAI_PROFILE_DB_PATH).expanduser()
    normalized = str(symbol or "").upper()
    if not normalized:
        return {"status": "missing", "error": "symbol is empty", "source": "iwencai_profile.db"}
    if not path.exists():
        return {
            "status": "missing",
            "symbol": normalized,
            "source": "iwencai_profile.db",
            "db_path": str(path),
            "error": "iwencai profile db not found",
        }

    try:
        conn = open_iwencai_readonly_db(path)
    except sqlite3.Error as exc:
        return {
            "status": "error",
            "symbol": normalized,
            "source": "iwencai_profile.db",
            "db_path": str(path),
            "error": str(exc),
        }

    try:
        profile = conn.execute(
            """
            select symbol, name, market, target_type, question, resolved_code,
                   summary, highlights_json, status, error, fetched_at, updated_at
            from iwencai_profiles
            where symbol = ?
            """,
            (normalized,),
        ).fetchone()
        if not profile:
            return {
                "status": "missing",
                "symbol": normalized,
                "source": "iwencai_profile.db",
                "db_path": str(path),
                "error": "iwencai profile not crawled yet",
            }

        events = [
            dict(row)
            for row in conn.execute(
                """
                select announcement_date, event_name, content, raw_json, fetched_at
                from iwencai_important_events
                where symbol = ?
                order by announcement_date desc, id desc
                limit ?
                """,
                (normalized, max(1, event_limit)),
            )
        ]
        concepts = [
            dict(row)
            for row in conn.execute(
                """
                select concept_name, included_date, concept_content, generated_date, raw_json, fetched_at
                from iwencai_concepts
                where symbol = ?
                order by included_date desc, id desc
                limit ?
                """,
                (normalized, max(1, concept_limit)),
            )
        ]
        highlights = [
            dict(row)
            for row in conn.execute(
                """
                select label, effect, label_type, raw_json, fetched_at
                from iwencai_profile_highlights
                where symbol = ?
                order by id
                """,
                (normalized,),
            )
        ]
        profile_dict = dict(profile)
        if not highlights:
            parsed_highlights = parse_json_list(profile_dict.get("highlights_json"))
            highlights = [
                {
                    "label": clean_text(item.get("看点") or item.get("label") or ""),
                    "effect": clean_text(item.get("影响") or item.get("effect") or ""),
                    "label_type": clean_text(item.get("类型") or item.get("type") or ""),
                    "raw_json": json_text(item),
                    "fetched_at": profile_dict.get("fetched_at") or "",
                }
                for item in parsed_highlights
                if isinstance(item, dict)
            ]
        return {
            "status": profile_dict.get("status") or "ok",
            "symbol": profile_dict.get("symbol") or normalized,
            "name": profile_dict.get("name") or "",
            "market": profile_dict.get("market") or "",
            "target_type": profile_dict.get("target_type") or "",
            "question": profile_dict.get("question") or "",
            "resolved_code": profile_dict.get("resolved_code") or "",
            "summary": profile_dict.get("summary") or "",
            "highlights": highlights,
            "important_events": events,
            "concepts": concepts,
            "error": profile_dict.get("error") or "",
            "fetched_at": profile_dict.get("fetched_at") or "",
            "updated_at": profile_dict.get("updated_at") or "",
            "source": "iwencai_profile.db",
            "db_path": str(path),
        }
    except sqlite3.Error as exc:
        return {
            "status": "error",
            "symbol": normalized,
            "source": "iwencai_profile.db",
            "db_path": str(path),
            "error": str(exc),
        }
    finally:
        conn.close()


def open_iwencai_readonly_db(path: Path) -> sqlite3.Connection:
    errors: list[str] = []
    candidates: list[tuple[str, bool]] = [
        (path.as_uri() + "?mode=ro", True),
        (f"file:{path}?mode=ro", True),
        (str(path), False),
    ]
    for target, is_uri in candidates:
        try:
            conn = sqlite3.connect(target, uri=is_uri, timeout=5)
            conn.row_factory = sqlite3.Row
            if not is_uri:
                conn.execute("pragma query_only = on")
            return conn
        except sqlite3.Error as exc:
            errors.append(str(exc))
    raise sqlite3.OperationalError("; ".join(errors) or "unable to open database file")


def start_iwencai_run(
    conn: sqlite3.Connection,
    scope: str,
    tier_order: list[str],
    requested_count: int,
) -> int:
    cursor = conn.execute(
        """
        insert into iwencai_crawl_runs (
          scope, tier_order_json, status, started_at, requested_count
        )
        values (?, ?, 'running', ?, ?)
        """,
        (scope, json_text(tier_order), now_iso(), requested_count),
    )
    return int(cursor.lastrowid)


def finish_iwencai_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    updated_count: int,
    skipped_count: int,
    failed_count: int,
    counts: dict[str, Any],
    errors: list[dict[str, Any]],
) -> None:
    conn.execute(
        """
        update iwencai_crawl_runs
        set status = ?,
            finished_at = ?,
            updated_count = ?,
            skipped_count = ?,
            failed_count = ?,
            counts_json = ?,
            errors_json = ?
        where id = ?
        """,
        (
            status,
            now_iso(),
            updated_count,
            skipped_count,
            failed_count,
            json_text(counts),
            json_text(errors[-200:]),
            run_id,
        ),
    )


def iwencai_profile_is_fresh(
    conn: sqlite3.Connection,
    symbol: str,
    stale_hours: float,
) -> bool:
    if stale_hours <= 0:
        return False
    row = conn.execute(
        """
        select status, fetched_at
        from iwencai_profiles
        where symbol = ?
        """,
        (symbol,),
    ).fetchone()
    if not row or row["status"] not in {"ok", "no_sections"}:
        return False
    try:
        fetched_at = datetime.fromisoformat(str(row["fetched_at"]))
    except ValueError:
        return False
    age_hours = (datetime.now() - fetched_at).total_seconds() / 3600
    return age_hours < stale_hours


def mark_iwencai_state(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    name: str,
    market: str,
    target_type: str,
    status: str,
    error: str = "",
    fetched_at: str = "",
) -> None:
    current = conn.execute(
        "select attempts from iwencai_crawl_state where symbol = ?",
        (symbol,),
    ).fetchone()
    attempts = int(current["attempts"] or 0) + 1 if current else 1
    conn.execute(
        """
        insert into iwencai_crawl_state (
          symbol, name, market, target_type, status, attempts, last_error, fetched_at, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol) do update set
          name = excluded.name,
          market = excluded.market,
          target_type = excluded.target_type,
          status = excluded.status,
          attempts = excluded.attempts,
          last_error = excluded.last_error,
          fetched_at = excluded.fetched_at,
          updated_at = excluded.updated_at
        """,
        (
            symbol,
            name,
            market,
            target_type,
            status,
            attempts,
            error[:1000],
            fetched_at,
            now_iso(),
        ),
    )


def upsert_iwencai_profile(conn: sqlite3.Connection, extracted: dict[str, Any]) -> dict[str, int]:
    fetched_at = str(extracted["fetched_at"])
    symbol = str(extracted["symbol"])
    highlights = list(extracted.get("highlights") or [])
    events = list(extracted.get("important_events") or [])
    concepts = list(extracted.get("concepts") or [])
    raw_sections = {
        "profile": extracted.get("profile_component") or {},
        "summary": extracted.get("summary_component") or {},
        "highlights": extracted.get("highlights_component") or {},
        "important_events": extracted.get("important_events_component") or {},
        "concepts": extracted.get("concepts_component") or {},
    }

    conn.execute(
        """
        insert into iwencai_profiles (
          symbol, name, market, target_type, question, resolved_code, summary,
          highlights_json, raw_sections_json, status, error, fetched_at, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol) do update set
          name = excluded.name,
          market = excluded.market,
          target_type = excluded.target_type,
          question = excluded.question,
          resolved_code = excluded.resolved_code,
          summary = excluded.summary,
          highlights_json = excluded.highlights_json,
          raw_sections_json = excluded.raw_sections_json,
          status = excluded.status,
          error = excluded.error,
          fetched_at = excluded.fetched_at,
          updated_at = excluded.updated_at
        """,
        (
            symbol,
            str(extracted.get("name") or ""),
            str(extracted.get("market") or ""),
            str(extracted.get("target_type") or ""),
            str(extracted.get("question") or ""),
            str(extracted.get("resolved_code") or ""),
            str(extracted.get("summary") or ""),
            json_text(highlights),
            json_text(raw_sections),
            str(extracted.get("status") or "ok"),
            str(extracted.get("error") or "")[:1000],
            fetched_at,
            now_iso(),
        ),
    )

    for table in ("iwencai_profile_highlights", "iwencai_important_events", "iwencai_concepts"):
        conn.execute(f"delete from {table} where symbol = ?", (symbol,))

    for item in highlights:
        label = clean_text(item.get("看点") or item.get("label") or "")
        effect = clean_text(item.get("影响") or item.get("effect") or "")
        label_type = clean_text(item.get("类型") or item.get("type") or "")
        conn.execute(
            """
            insert or replace into iwencai_profile_highlights (
              symbol, label, effect, label_type, row_hash, raw_json, fetched_at
            )
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                label,
                effect,
                label_type,
                row_hash(symbol, label, effect, label_type),
                json_text(item),
                fetched_at,
            ),
        )

    for item in events:
        event_date = clean_text(item.get("重要事件公告时间") or item.get("announcement_date") or "")
        event_name = clean_text(item.get("重要事件名称") or item.get("event_name") or "")
        content = clean_text(item.get("重要事件内容") or item.get("content") or "")
        conn.execute(
            """
            insert or replace into iwencai_important_events (
              symbol, announcement_date, event_name, content, row_hash, raw_json, fetched_at
            )
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                event_date,
                event_name,
                content,
                row_hash(symbol, event_date, event_name, content),
                json_text(item),
                fetched_at,
            ),
        )

    for item in concepts:
        concept_name = clean_text(item.get("诊股概念分类名称") or item.get("concept_name") or "")
        included_date = clean_text(item.get("诊股概念分类纳入日期") or item.get("included_date") or "")
        content = clean_text(item.get("诊股概念分类内容") or item.get("concept_content") or "")
        generated_date = clean_text(item.get("概念生成时间") or item.get("generated_date") or "")
        conn.execute(
            """
            insert or replace into iwencai_concepts (
              symbol, concept_name, included_date, concept_content, generated_date,
              row_hash, raw_json, fetched_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                concept_name,
                included_date,
                content,
                generated_date,
                row_hash(symbol, concept_name, included_date, content, generated_date),
                json_text(item),
                fetched_at,
            ),
        )

    mark_iwencai_state(
        conn,
        symbol=symbol,
        name=str(extracted.get("name") or ""),
        market=str(extracted.get("market") or ""),
        target_type=str(extracted.get("target_type") or ""),
        status=str(extracted.get("status") or "ok"),
        error=str(extracted.get("error") or ""),
        fetched_at=fetched_at,
    )
    return {"profiles": 1, "highlights": len(highlights), "important_events": len(events), "concepts": len(concepts)}


def refresh_iwencai_profile_for_symbol(
    symbol_row: dict[str, Any] | sqlite3.Row,
    *,
    target_type: str = "stock",
    timeout: float = 25,
    max_retries: int = 2,
) -> dict[str, Any]:
    symbol_data = dict(symbol_row)
    symbol = str(symbol_data.get("symbol") or "").upper()
    name = str(symbol_data.get("name") or "").strip()
    market = str(symbol_data.get("market") or "").strip()
    if not symbol:
        raise ValueError("symbol is empty")

    question = name or (symbol.split(".", 1)[0] if "." in symbol else symbol)
    client = IwencaiProfileClient(timeout=timeout, max_retries=max_retries)
    try:
        payload = client.fetch_robot_data(question)
        extracted = extract_iwencai_profile(
            payload,
            symbol=symbol,
            name=name,
            market=market,
            target_type=target_type,
            question=question,
        )
        with get_iwencai_db() as conn:
            init_iwencai_profile_db(conn)
            counts = upsert_iwencai_profile(conn, extracted)
            conn.commit()
        return {
            "mode": "iwencai-profile-refresh",
            "symbol": symbol,
            "name": name,
            "question": question,
            "status": str(extracted.get("status") or "ok"),
            "counts": counts,
            "profile": read_iwencai_profile(symbol),
        }
    except Exception as exc:
        error = str(exc)
        with get_iwencai_db() as conn:
            init_iwencai_profile_db(conn)
            mark_iwencai_state(
                conn,
                symbol=symbol,
                name=name,
                market=market,
                target_type=target_type,
                status="failed",
                error=error,
            )
            conn.commit()
        raise


class IwencaiProfileClient:
    def __init__(
        self,
        *,
        hexin_js_path: str | Path | None = None,
        hexin_js_url: str = IWENCAI_HEXIN_JS_URL,
        node_path: str | Path | None = None,
        timeout: float = 25,
        max_retries: int = 3,
        token_ttl_requests: int = 120,
    ) -> None:
        if requests is None:
            raise RuntimeError("requests is required. Install project requirements before crawling iWenCai.")
        self.hexin_js_path = ensure_hexin_script(hexin_js_path, hexin_js_url)
        self.node_path = find_node(node_path)
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.token_ttl_requests = max(1, token_ttl_requests)
        self.session = requests.Session()
        self._hexin_v = ""
        self._token_uses = 0

    def fetch_robot_data(self, question: str) -> dict[str, Any]:
        payload = iwencai_robot_payload(question)
        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(
                    IWENCAI_ROBOT_DATA_URL,
                    data=payload,
                    headers=self.headers(refresh=attempt > 1),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = response.json()
                status_code = result.get("status_code")
                if status_code == 0:
                    return result
                last_error = f"status_code={status_code} status_msg={result.get('status_msg')}"
                if status_code in {-302, "-302"}:
                    break
            except Exception as exc:  # noqa: BLE001 - crawler should continue per symbol.
                last_error = str(exc)
            time.sleep(min(0.8 * attempt, 3.0))
        raise RuntimeError(last_error or "iwencai request failed")

    def headers(self, *, refresh: bool = False) -> dict[str, str]:
        if refresh or not self._hexin_v or self._token_uses >= self.token_ttl_requests:
            self._hexin_v = generate_hexin_v(self.node_path, self.hexin_js_path)
            self._token_uses = 0
        self._token_uses += 1
        return {
            "User-Agent": IWENCAI_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.iwencai.com",
            "Referer": IWENCAI_REFERER,
            "hexin-v": self._hexin_v,
        }


def iwencai_robot_payload(question: str) -> dict[str, Any]:
    return {
        "add_info": json.dumps(
            {"urp": {"scene": 1, "company": 1, "business": 1}, "contentType": "json", "searchInfo": True},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "perpage": "10",
        "page": 1,
        "source": "Ths_iwencai_Xuangu",
        "log_info": json.dumps({"input_type": "click"}, ensure_ascii=False, separators=(",", ":")),
        "version": "2.0",
        "secondary_intent": "stock",
        "question": question,
    }


def ensure_hexin_script(
    hexin_js_path: str | Path | None,
    hexin_js_url: str = IWENCAI_HEXIN_JS_URL,
) -> Path:
    if hexin_js_path:
        path = Path(hexin_js_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"hexin-v script not found: {path}")
        return path

    cache_dir = DATA_DIR / "iwencai_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / "hexin-v.bundle.js"
    if path.exists() and path.stat().st_size > 100_000:
        return path

    request = urllib.request.Request(
        hexin_js_url,
        headers={"User-Agent": IWENCAI_USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - user-controlled URL is explicit CLI config.
        payload = response.read()
    if len(payload) < 100_000:
        raise RuntimeError(f"downloaded hexin-v script is unexpectedly small: {len(payload)} bytes")
    path.write_bytes(payload)
    return path


def find_node(node_path: str | Path | None = None) -> Path:
    candidates: list[str | Path] = []
    if node_path:
        candidates.append(node_path)
    if os.environ.get("IWENCAI_NODE"):
        candidates.append(os.environ["IWENCAI_NODE"])
    path_node = shutil.which("node")
    if path_node:
        candidates.append(path_node)
    candidates.extend(
        [
            Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
            "/opt/homebrew/bin/node",
            "/usr/local/bin/node",
        ]
    )
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.exists() and os.access(path, os.X_OK):
            return path
    raise RuntimeError("Node.js not found. Install node or pass --node /path/to/node.")


def generate_hexin_v(node_path: Path, hexin_js_path: Path) -> str:
    completed = subprocess.run(
        [str(node_path), str(hexin_js_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=15,
        check=True,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("hexin-v generator returned empty output")
    return lines[-1]


def extract_iwencai_profile(
    payload: dict[str, Any],
    *,
    symbol: str,
    name: str,
    market: str,
    target_type: str,
    question: str,
) -> dict[str, Any]:
    components = payload_components(payload)
    components_by_uuid = {str(comp.get("uuid") or ""): comp for comp in components if comp.get("uuid")}
    profile_component = find_component_by_title(components, "简介和看点")
    summary_component: dict[str, Any] | None = None
    highlights_component: dict[str, Any] | None = None
    if profile_component:
        for child_uuid in (profile_component.get("config") or {}).get("children") or []:
            child = components_by_uuid.get(str(child_uuid))
            if not child:
                continue
            if child.get("show_type") == "txt1" and summary_component is None:
                summary_component = child
            elif child.get("show_type") == "impressionLabel" and highlights_component is None:
                highlights_component = child

    summary_component = summary_component or find_component_by_show_type(components, "txt1")
    highlights_component = highlights_component or find_component_by_show_type(components, "impressionLabel")
    events_component = find_component_by_title(components, "近期重要事件")
    concepts_component = find_component_by_title(components, "所属概念列表")

    summary = clean_text((summary_component or {}).get("data", {}).get("content", ""))
    highlights = table_datas(highlights_component)
    events = table_datas(events_component)
    concepts = table_datas(concepts_component)
    parser_data = (payload.get("data") or {}).get("parser_data") or {}
    resolved_code = str(parser_data.get("default_code") or "")
    fetched_at = now_iso()
    status = "ok" if any([summary, highlights, events, concepts]) else "no_sections"
    error = "" if status == "ok" else "问财返回成功，但没有简介和看点/近期重要事件/所属概念列表组件"
    return {
        "symbol": symbol,
        "name": name,
        "market": market,
        "target_type": target_type,
        "question": question,
        "resolved_code": resolved_code,
        "summary": summary,
        "highlights": highlights,
        "important_events": events,
        "concepts": concepts,
        "profile_component": profile_component,
        "summary_component": summary_component,
        "highlights_component": highlights_component,
        "important_events_component": events_component,
        "concepts_component": concepts_component,
        "status": status,
        "error": error,
        "fetched_at": fetched_at,
    }


def payload_components(payload: dict[str, Any]) -> list[dict[str, Any]]:
    answer = ((payload.get("data") or {}).get("answer") or [])
    if not answer:
        return []
    txt = answer[0].get("txt") or []
    if not txt:
        return []
    content = txt[0].get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return []
    if not isinstance(content, dict):
        return []
    components = content.get("components") or []
    return [component for component in components if isinstance(component, dict)]


def find_component_by_title(components: list[dict[str, Any]], expected_title: str) -> dict[str, Any] | None:
    for component in components:
        if component_title(component) == expected_title:
            return component
    return None


def find_component_by_show_type(components: list[dict[str, Any]], show_type: str) -> dict[str, Any] | None:
    for component in components:
        if component.get("show_type") == show_type:
            return component
    return None


def component_title(component: dict[str, Any]) -> str:
    title_config = component.get("title_config") or {}
    title_data = title_config.get("data") or {}
    config = component.get("config") or {}
    return str(title_data.get("h1") or config.get("title") or component.get("show_type") or "")


def table_datas(component: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not component:
        return []
    datas = ((component.get("data") or {}).get("datas") or [])
    return [row for row in datas if isinstance(row, dict)]


def clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def row_hash(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


def parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
