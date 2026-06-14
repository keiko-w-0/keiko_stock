from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sqlite3
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener, urlopen

from ..db import now_iso
from .xueqiu import (
    XueqiuClientError,
    fetch_xueqiu_status_payloads,
    xueqiu_browser_mode,
    xueqiu_cookie_header,
    xueqiu_discussion_configured,
    xueqiu_symbol,
)


EASTMONEY_GUBA_LIST_URL = "https://guba.eastmoney.com/list,{code}.html"
EASTMONEY_COOKIE_ENV_NAMES = (
    "KEIKO_EASTMONEY_COOKIE",
    "EASTMONEY_GUBA_COOKIE",
    "EASTMONEY_COOKIE",
)
EASTMONEY_PROXY_ENV_NAMES = (
    "KEIKO_EASTMONEY_PROXY",
    "EASTMONEY_GUBA_PROXY",
    "EASTMONEY_PROXY",
)
EASTMONEY_USER_AGENT_ENV_NAMES = (
    "KEIKO_EASTMONEY_USER_AGENT",
    "EASTMONEY_GUBA_USER_AGENT",
    "EASTMONEY_USER_AGENT",
)
DEFAULT_COMMUNITY_SOURCES = ("eastmoney_guba", "xueqiu")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


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
    if normalized_source == "eastmoney_guba":
        return fetch_eastmoney_guba_posts(symbol, limit=limit, timeout=timeout)
    if normalized_source == "xueqiu":
        return fetch_xueqiu_posts(symbol, limit=limit, timeout=timeout)
    raise CommunityCrawlerError(f"unsupported community source: {source}")


def fetch_eastmoney_guba_posts(symbol: str, limit: int = 50, timeout: int = 15) -> list[dict[str, Any]]:
    code = a_share_code(symbol)
    if not code:
        raise CommunityCrawlerError("eastmoney_guba only supports A-share 6-digit symbols")

    url = EASTMONEY_GUBA_LIST_URL.format(code=code)
    body = fetch_text(url, timeout=timeout)
    posts = parse_eastmoney_guba_list(body, code=code, limit=limit)
    fetched_at = now_iso()
    for post in posts:
        detail_error = ""
        try:
            detail_body = fetch_text(post["url"], timeout=timeout)
            if is_eastmoney_validation_page(detail_body):
                raise CommunityCrawlerError("eastmoney_guba detail returned identity verification page")
            content = parse_eastmoney_guba_detail_text(detail_body)
            if content:
                post["content"] = content
                post.setdefault("raw", {})["detail_text_length"] = len(content)
        except CommunityCrawlerError as exc:
            detail_error = str(exc)
        if detail_error:
            post.setdefault("raw", {})["detail_error"] = detail_error
        post["symbol"] = symbol.upper()
        post["source"] = "eastmoney_guba"
        post["fetched_at"] = fetched_at
    return posts


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


def dotenv_values() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    values: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def community_sources(source: str) -> list[str]:
    normalized = normalize_community_source(source)
    if normalized == "all":
        return list(DEFAULT_COMMUNITY_SOURCES)
    return [normalized]


def fetch_text(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": eastmoney_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://guba.eastmoney.com/",
    }
    cookie = eastmoney_cookie_header()
    if cookie:
        headers["Cookie"] = cookie
    request = Request(
        url,
        headers=headers,
    )
    try:
        proxy_url = eastmoney_proxy_url()
        opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url})) if proxy_url else None
        open_url = opener.open if opener else urlopen
        with open_url(request, timeout=timeout) as response:
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


def eastmoney_cookie_header() -> str:
    return eastmoney_env_value(EASTMONEY_COOKIE_ENV_NAMES)


def eastmoney_proxy_url() -> str:
    return eastmoney_env_value(EASTMONEY_PROXY_ENV_NAMES)


def eastmoney_user_agent() -> str:
    return eastmoney_env_value(EASTMONEY_USER_AGENT_ENV_NAMES) or DEFAULT_USER_AGENT


def eastmoney_env_value(names: tuple[str, ...]) -> str:
    env_values = dotenv_values()
    for name in names:
        value = os.getenv(name) or env_values.get(name)
        if value:
            return value.strip()
    return ""


def is_eastmoney_validation_page(body: str) -> bool:
    text = body or ""
    if "xeditor_content" in text:
        return False
    return "身份核实" in text or "fd_guba_validate" in text or "em_capt" in text


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


class EastmoneyGubaDetailTextParser(HTMLParser):
    VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "source"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._content_depth = 0
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        class_name = attr_map.get("class", "")
        if self._content_depth:
            if tag in {"br", "p", "div", "li"}:
                self._append_separator()
            if tag in self.VOID_TAGS:
                return
            self._content_depth += 1
            if tag in {"script", "style", "video", "audio", "svg"}:
                self._skip_depth += 1
            return
        if tag == "div" and "xeditor_content" in class_name.split():
            self._content_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self._content_depth:
            if tag in {"p", "div", "li"}:
                self._append_separator()
            if self._skip_depth:
                self._skip_depth -= 1
            self._content_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._content_depth or self._skip_depth:
            return
        text = normalize_html_text(data)
        if text:
            self._parts.append(text)

    def _append_separator(self) -> None:
        if self._parts and self._parts[-1] != "\n":
            self._parts.append("\n")

    def text(self) -> str:
        content = " ".join(part for part in self._parts if part != "\n")
        return re.sub(r"\s+", " ", content).strip()


def parse_eastmoney_guba_detail_text(body: str) -> str:
    parser = EastmoneyGubaDetailTextParser()
    parser.feed(body or "")
    return parser.text()


def upsert_community_posts(conn: sqlite3.Connection, posts: list[dict[str, Any]]) -> int:
    rows: list[dict[str, Any]] = []
    fetched_at = now_iso()
    for post in posts:
        symbol = str(post.get("symbol") or "").upper()
        source = normalize_community_source(str(post.get("source") or "eastmoney_guba"))
        if source == "all":
            source = "eastmoney_guba"
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
    if value in {"eastmoney", "eastmoney_guba", "guba", "dfcf_guba"}:
        return "eastmoney_guba"
    if value in {"xueqiu", "xq", "snowball"}:
        return "xueqiu"
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


def urljoin(base: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return base.rstrip("/") + href
    return f"{base.rstrip('/')}/{href.lstrip('/')}"
