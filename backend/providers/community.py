from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import time
from datetime import datetime
from typing import Any

from ..db import now_iso
from .xueqiu import (
    XueqiuClientError,
    fetch_xueqiu_status_payloads,
    xueqiu_browser_mode,
    xueqiu_cookie_header,
    xueqiu_discussion_configured,
    xueqiu_symbol,
)


DEFAULT_COMMUNITY_SOURCES = ("xueqiu",)


class CommunityCrawlerError(RuntimeError):
    pass


def crawl_community_posts(
    symbol: str,
    source: str = "all",
    limit: int = 50,
    timeout: int = 15,
    sleep_seconds: float = 0.0,
) -> dict[str, Any]:
    normalized_source = normalize_community_source(source)
    posts: list[dict[str, Any]] = []
    errors: list[str] = []
    sources = community_sources(normalized_source)
    for index, item_source in enumerate(sources):
        try:
            posts.extend(
                crawl_community_posts_for_source(
                    symbol,
                    source=item_source,
                    limit=limit,
                    timeout=timeout,
                )
            )
        except CommunityCrawlerError as exc:
            errors.append(f"{item_source}: {exc}")
        if sleep_seconds > 0 and index < len(sources) - 1:
            time.sleep(sleep_seconds)
    if not posts and errors:
        raise CommunityCrawlerError("; ".join(errors))
    return {
        "mode": "community-crawler",
        "source": "+".join(sources) if len(sources) > 1 else sources[0],
        "symbol": symbol.upper(),
        "posts": posts,
        "count": len(posts),
        "errors": errors,
        "fetched_at": now_iso(),
    }


def crawl_community_posts_for_source(
    symbol: str,
    *,
    source: str,
    limit: int = 50,
    timeout: int = 15,
) -> list[dict[str, Any]]:
    normalized_source = normalize_community_source(source)
    if normalized_source == "xueqiu":
        return fetch_xueqiu_posts(symbol, limit=limit, timeout=timeout)
    raise CommunityCrawlerError(f"unsupported community source: {source}")


def fetch_xueqiu_posts(symbol: str, limit: int = 50, timeout: int = 30) -> list[dict[str, Any]]:
    xq_symbol = xueqiu_symbol(symbol)
    if not xq_symbol:
        raise CommunityCrawlerError("xueqiu only supports A-share SH/SZ symbols")

    if not xueqiu_discussion_configured():
        raise CommunityCrawlerError(
            "xueqiu is not configured; set KEIKO_XUEQIU_COOKIE or install DrissionPage for browser fallback"
        )

    clean_limit = max(1, min(int(limit or 50), 200))
    page_size = min(20, clean_limit)
    posts: list[dict[str, Any]] = []
    fetched_at = now_iso()
    browser_mode = xueqiu_browser_mode()
    cookie = xueqiu_cookie_header()
    try:
        payloads = fetch_xueqiu_status_payloads(
            xq_symbol,
            limit=clean_limit,
            page_size=page_size,
            cookie=cookie,
            timeout=timeout,
            browser_mode=browser_mode,
        )
    except XueqiuClientError as exc:
        raise CommunityCrawlerError(str(exc)) from exc
    for payload in payloads:
        items = payload.get("list") or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            post = parse_xueqiu_status(item, symbol=symbol.upper(), xq_symbol=xq_symbol, fetched_at=fetched_at)
            if post:
                posts.append(post)
            if len(posts) >= clean_limit:
                break
        if len(posts) >= clean_limit:
            break
    if not posts:
        raise CommunityCrawlerError("xueqiu returned no discussion rows for this symbol")
    return posts[:clean_limit]


def parse_xueqiu_status(
    item: dict[str, Any],
    *,
    symbol: str,
    xq_symbol: str,
    fetched_at: str,
) -> dict[str, Any] | None:
    text = normalize_html_text(str(item.get("description") or item.get("text") or ""))
    if not text:
        return None
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    user_id = str(user.get("id") or user.get("user_id") or "").strip()
    status_id = str(item.get("id") or item.get("status_id") or stable_post_id(text)).strip()
    author = str(user.get("screen_name") or user.get("name") or "").strip()
    url = f"https://xueqiu.com/{user_id}/{status_id}" if user_id and status_id else f"https://xueqiu.com/S/{xq_symbol}"
    return {
        "source_post_id": status_id,
        "title": text[:120],
        "content": text,
        "author": author,
        "url": url,
        "published_at": xueqiu_timestamp(item.get("created_at") or item.get("timeBefore") or item.get("created_at_ms")),
        "metrics": {
            "reply_count": item.get("reply_count"),
            "retweet_count": item.get("retweet_count"),
            "like_count": item.get("like_count"),
            "comment_count": item.get("comment_count"),
        },
        "raw": {
            "xq_symbol": xq_symbol,
            "target": item.get("target"),
            "type": item.get("type"),
        },
        "symbol": symbol,
        "source": "xueqiu",
        "fetched_at": fetched_at,
    }


def xueqiu_timestamp(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value).strip()
    if text.isdigit():
        timestamp = int(text)
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        try:
            return datetime.fromtimestamp(timestamp).isoformat(timespec="minutes")
        except (OverflowError, OSError, ValueError):
            return ""
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2}))?", text)
    if match:
        year, month, day, hour, minute = match.groups()
        try:
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hour or 0),
                int(minute or 0),
            ).isoformat(timespec="minutes")
        except ValueError:
            return ""
    return text[:32]


def xueqiu_configured() -> bool:
    return xueqiu_discussion_configured()


def community_sources(source: str) -> list[str]:
    normalized = normalize_community_source(source)
    if normalized == "all":
        return list(DEFAULT_COMMUNITY_SOURCES)
    return [normalized]


def upsert_community_posts(conn: sqlite3.Connection, posts: list[dict[str, Any]]) -> int:
    rows: list[dict[str, Any]] = []
    fetched_at = now_iso()
    for post in posts:
        symbol = str(post.get("symbol") or "").upper()
        source = normalize_community_source(str(post.get("source") or "xueqiu"))
        if source == "all":
            source = "xueqiu"
        title = str(post.get("title") or "").strip()
        url = str(post.get("url") or "").strip()
        source_post_id = str(post.get("source_post_id") or stable_post_id(url or title))
        if not symbol or not title or not source_post_id:
            continue
        rows.append(
            {
                "symbol": symbol,
                "source": source,
                "source_post_id": source_post_id,
                "title": title,
                "content": str(post.get("content") or ""),
                "author": str(post.get("author") or ""),
                "url": url,
                "published_at": normalize_datetime_text(post.get("published_at")),
                "metrics_json": json.dumps(post.get("metrics") or {}, ensure_ascii=False, default=str),
                "raw_json": json.dumps(post.get("raw") or post, ensure_ascii=False, default=str),
                "fetched_at": str(post.get("fetched_at") or fetched_at),
            }
        )
    conn.executemany(
        """
        insert into community_posts (
          symbol, source, source_post_id, title, content, author, url,
          published_at, metrics_json, raw_json, fetched_at
        )
        values (
          :symbol, :source, :source_post_id, :title, :content, :author, :url,
          :published_at, :metrics_json, :raw_json, :fetched_at
        )
        on conflict(source, symbol, source_post_id) do update set
          title = excluded.title,
          content = excluded.content,
          author = excluded.author,
          url = excluded.url,
          published_at = excluded.published_at,
          metrics_json = excluded.metrics_json,
          raw_json = excluded.raw_json,
          fetched_at = excluded.fetched_at
        """,
        rows,
    )
    return len(rows)


def normalize_community_source(source: str) -> str:
    value = str(source or "").strip().lower().replace("-", "_")
    if value in {"", "all", "both", "community_all", "default"}:
        return "all"
    if value in {"xueqiu", "xq", "snowball"}:
        return "xueqiu"
    return value


def normalize_html_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_datetime_text(value: Any) -> str:
    text = str(value or "").strip()
    return text[:32]


def stable_post_id(value: str) -> str:
    return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:24]
