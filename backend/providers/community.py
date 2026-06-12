from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import time
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from ..db import now_iso


EASTMONEY_GUBA_LIST_URL = "https://guba.eastmoney.com/list,{code}.html"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


class CommunityCrawlerError(RuntimeError):
    pass


def crawl_community_posts(
    symbol: str,
    source: str = "eastmoney_guba",
    limit: int = 50,
    timeout: int = 15,
    sleep_seconds: float = 0.0,
) -> dict[str, Any]:
    normalized_source = normalize_community_source(source)
    if normalized_source != "eastmoney_guba":
        raise CommunityCrawlerError(f"unsupported community source: {source}")

    posts = fetch_eastmoney_guba_posts(symbol, limit=limit, timeout=timeout)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return {
        "mode": "community-crawler",
        "source": normalized_source,
        "symbol": symbol.upper(),
        "posts": posts,
        "count": len(posts),
        "fetched_at": now_iso(),
    }


def fetch_eastmoney_guba_posts(symbol: str, limit: int = 50, timeout: int = 15) -> list[dict[str, Any]]:
    code = a_share_code(symbol)
    if not code:
        raise CommunityCrawlerError("eastmoney_guba only supports A-share 6-digit symbols")

    url = EASTMONEY_GUBA_LIST_URL.format(code=code)
    body = fetch_text(url, timeout=timeout)
    posts = parse_eastmoney_guba_list(body, code=code, limit=limit)
    fetched_at = now_iso()
    for post in posts:
        post["symbol"] = symbol.upper()
        post["source"] = "eastmoney_guba"
        post["fetched_at"] = fetched_at
    return posts


def fetch_text(url: str, timeout: int = 15) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://guba.eastmoney.com/",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CommunityCrawlerError(f"eastmoney_guba request failed: {exc}") from exc

    encoding = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, flags=re.I)
    if match:
        encoding = match.group(1)
    try:
        return body.decode(encoding, errors="ignore")
    except LookupError:
        return body.decode("utf-8", errors="ignore")


def parse_eastmoney_guba_list(body: str, code: str, limit: int = 50) -> list[dict[str, Any]]:
    clean_limit = max(1, min(int(limit or 50), 200))
    pattern = re.compile(
        rf"<a\b[^>]*href=[\"'](?P<href>[^\"']*news,{re.escape(code)},(?P<post_id>\d+)\.html[^\"']*)[\"'][^>]*>"
        r"(?P<title>.*?)</a>",
        flags=re.I | re.S,
    )
    posts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in pattern.finditer(body):
        href = html.unescape(match.group("href"))
        title = normalize_html_text(match.group("title"))
        if not title or title in seen:
            continue
        seen.add(title)
        post_id = match.group("post_id") or stable_post_id(href or title)
        nearby = body[match.end() : match.end() + 500]
        published_at = parse_nearby_datetime(nearby)
        posts.append(
            {
                "source_post_id": post_id,
                "title": title,
                "content": "",
                "author": "",
                "url": urljoin("https://guba.eastmoney.com/", href),
                "published_at": published_at,
                "metrics": parse_nearby_metrics(nearby),
                "raw": {"href": href},
            }
        )
        if len(posts) >= clean_limit:
            break
    return posts


def upsert_community_posts(conn: sqlite3.Connection, posts: list[dict[str, Any]]) -> int:
    rows: list[dict[str, Any]] = []
    fetched_at = now_iso()
    for post in posts:
        symbol = str(post.get("symbol") or "").upper()
        source = normalize_community_source(str(post.get("source") or "eastmoney_guba"))
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
    if value in {"", "eastmoney", "eastmoney_guba", "guba", "dfcf_guba"}:
        return "eastmoney_guba"
    return value


def a_share_code(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    match = re.search(r"(\d{6})", text)
    return match.group(1) if match else ""


def normalize_html_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_nearby_datetime(value: str) -> str:
    text = normalize_html_text(value)
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2}))?", text)
    if match:
        year, month, day, hour, minute = match.groups()
        hour = hour or "00"
        minute = minute or "00"
        try:
            return datetime(int(year), int(month), int(day), int(hour), int(minute)).isoformat(timespec="minutes")
        except ValueError:
            return ""
    match = re.search(r"(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{1,2})", text)
    if match:
        month, day, hour, minute = match.groups()
        today = datetime.now()
        try:
            return datetime(today.year, int(month), int(day), int(hour), int(minute)).isoformat(timespec="minutes")
        except ValueError:
            return ""
    return ""


def parse_nearby_metrics(value: str) -> dict[str, Any]:
    text = normalize_html_text(value)
    metrics: dict[str, Any] = {}
    numbers = [int(item) for item in re.findall(r"(?<!\d)(\d{1,8})(?!\d)", text[:120])]
    if numbers:
        metrics["nearby_numbers"] = numbers[:4]
    return metrics


def normalize_datetime_text(value: Any) -> str:
    text = str(value or "").strip()
    return text[:32]


def stable_post_id(value: str) -> str:
    return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:24]
