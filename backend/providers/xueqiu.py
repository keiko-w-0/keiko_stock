from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..db import now_iso


XUEQIU_QUOTE_URL = "https://stock.xueqiu.com/v5/stock/quote.json"
XUEQIU_STATUS_URL = "https://xueqiu.com/query/v1/symbol/search/status.json"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
XUEQIU_COOKIE_ENV_NAMES = ("KEIKO_XUEQIU_COOKIE", "XUEQIU_COOKIE")
XUEQIU_TOKEN_ENV_NAMES = ("KEIKO_XUEQIU_TOKEN", "XUEQIU_TOKEN", "XQ_A_TOKEN")


class XueqiuClientError(RuntimeError):
    pass


def fetch_xueqiu_quote(symbol: str, timeout: int = 15) -> dict[str, Any] | None:
    """Return live quote fields from stock.xueqiu.com (needs KEIKO_XUEQIU_COOKIE)."""
    xq_symbol = xueqiu_symbol(symbol)
    if not xq_symbol:
        return None
    cookie = xueqiu_cookie_header()
    if not cookie:
        return None
    try:
        payload = fetch_xueqiu_http_json(
            XUEQIU_QUOTE_URL,
            params={"symbol": xq_symbol, "extend": "detail"},
            referer=f"https://xueqiu.com/S/{xq_symbol}",
            cookie=cookie,
            timeout=timeout,
        )
    except XueqiuClientError:
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None
    quote = data.get("quote") if isinstance(data.get("quote"), dict) else {}
    market = data.get("market") if isinstance(data.get("market"), dict) else {}
    if quote.get("current") is None and quote.get("last_close") is None:
        return None
    current = quote.get("current")
    if current is None:
        current = quote.get("last_close")
    result: dict[str, Any] = {
        "symbol": str(symbol or "").upper(),
        "xq_symbol": xq_symbol,
        "name": str(quote.get("name") or "").strip(),
        "current_price": round(float(current), 4),
        "change_pct": round(float(quote.get("percent") or 0), 4) if quote.get("percent") is not None else None,
        "currency": str(quote.get("currency") or "CNY"),
        "market_status": str(market.get("status") or ""),
        "price_source": "xueqiu",
        "fetched_at": now_iso(),
    }
    timestamp = quote.get("timestamp") or quote.get("time")
    if timestamp not in (None, ""):
        try:
            ts = int(timestamp)
            if ts > 10_000_000_000:
                ts //= 1000
            result["price_as_of"] = datetime.fromtimestamp(ts).isoformat(timespec="minutes")
        except (OverflowError, OSError, TypeError, ValueError):
            pass
    return result


def fetch_xueqiu_status_payloads(
    xq_symbol: str,
    *,
    limit: int = 50,
    page_size: int = 20,
    cookie: str = "",
    timeout: int = 30,
    browser_mode: str = "auto",
) -> list[dict[str, Any]]:
    mode = normalize_browser_mode(browser_mode)
    clean_limit = max(1, min(int(limit or 50), 200))
    clean_page_size = max(1, min(int(page_size or 20), 20))
    if mode == "always":
        return _fetch_status_payloads_via_browser_session(
            xq_symbol,
            limit=clean_limit,
            page_size=clean_page_size,
            timeout=timeout,
        )

    payloads: list[dict[str, Any]] = []
    page = 1
    while sum(len(item.get("list") or []) for item in payloads if isinstance(item, dict)) < clean_limit:
        try:
            payload = fetch_xueqiu_http_json(
                XUEQIU_STATUS_URL,
                params=_status_params(xq_symbol, page=page, count=clean_page_size),
                referer=f"https://xueqiu.com/S/{xq_symbol}",
                cookie=cookie or xueqiu_cookie_header(),
                timeout=timeout,
            )
        except XueqiuClientError:
            if mode == "never" or not drission_available():
                raise
            return _fetch_status_payloads_via_browser_session(
                xq_symbol,
                limit=clean_limit,
                page_size=clean_page_size,
                timeout=timeout,
            )
        items = payload.get("list") or []
        payloads.append(payload)
        if not isinstance(items, list) or not items or len(items) < clean_page_size:
            break
        page += 1
    return payloads


def _status_params(xq_symbol: str, *, page: int, count: int) -> dict[str, Any]:
    return {
        "symbol": xq_symbol,
        "count": count,
        "page": page,
        "comment": 0,
        "hl": 0,
        "source": "all",
        "sort": "time",
        "type": 11,
        "_": int(time.time() * 1000),
    }


def _fetch_status_payloads_via_browser_session(
    xq_symbol: str,
    *,
    limit: int,
    page_size: int,
    timeout: int,
) -> list[dict[str, Any]]:
    session = _open_xueqiu_browser_session(xq_symbol, timeout=timeout)
    payloads: list[dict[str, Any]] = []
    try:
        page = 1
        while sum(len(item.get("list") or []) for item in payloads) < limit:
            payload = _browser_fetch_status_json(session, xq_symbol, page=page, count=page_size)
            items = payload.get("list") or []
            payloads.append(payload)
            if not isinstance(items, list) or not items or len(items) < page_size:
                break
            page += 1
        return payloads
    finally:
        session.close()


class _XueqiuBrowserSession:
    def __init__(self, browser: Any, profile_dir: str):
        self.browser = browser
        self.profile_dir = profile_dir

    def close(self) -> None:
        try:
            self.browser.quit()
        except Exception:
            pass
        shutil.rmtree(self.profile_dir, ignore_errors=True)


def _open_xueqiu_browser_session(xq_symbol: str, *, timeout: int) -> _XueqiuBrowserSession:
    if not drission_available():
        raise XueqiuClientError("DrissionPage is not installed; pip install DrissionPage")

    from DrissionPage import ChromiumOptions, ChromiumPage

    profile_dir = tempfile.mkdtemp(prefix="keiko_xueqiu_")
    options = ChromiumOptions()
    options.headless(True)
    options.set_argument("--no-sandbox")
    options.set_argument("--window-size=1920,1080")
    options.set_argument("--disable-dev-shm-usage")
    options.set_argument("--disable-blink-features=AutomationControlled")
    options.set_argument("--lang=zh-CN")
    options.set_argument(f"--user-data-dir={profile_dir}")
    browser = ChromiumPage(options)
    try:
        browser.run_js("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    except Exception:
        pass
    browser.get(f"https://xueqiu.com/S/{xq_symbol}")
    time.sleep(min(8, max(4, timeout // 4)))
    html = browser.html or ""
    if "aliyun_waf" in html.lower() or ("renderData" in html[:800] and "timeline" not in html[:5000].lower()):
        browser.quit()
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise XueqiuClientError("xueqiu browser session did not pass WAF challenge")
    return _XueqiuBrowserSession(browser, profile_dir)


def _browser_fetch_status_json(
    session: _XueqiuBrowserSession,
    xq_symbol: str,
    *,
    page: int,
    count: int,
) -> dict[str, Any]:
    query = urlencode(_status_params(xq_symbol, page=page, count=count))
    api_url = f"{XUEQIU_STATUS_URL}?{query}"
    js = f"""
    return fetch({json.dumps(api_url)}, {{
        credentials: "include",
        headers: {{"Accept": "application/json, text/plain, */*"}}
    }}).then(response => response.text());
    """
    body = session.browser.run_js(js, as_expr=False)
    if not isinstance(body, str) or not body.lstrip().startswith("{"):
        raise XueqiuClientError("xueqiu browser fetch returned non-JSON payload")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise XueqiuClientError("xueqiu browser fetch returned unexpected payload")
    return payload


def fetch_xueqiu_status_payload(
    xq_symbol: str,
    *,
    page: int = 1,
    count: int = 20,
    cookie: str = "",
    timeout: int = 30,
    browser_mode: str = "auto",
) -> dict[str, Any]:
    params = _status_params(xq_symbol, page=page, count=count)
    referer = f"https://xueqiu.com/S/{xq_symbol}"
    mode = normalize_browser_mode(browser_mode)
    if mode == "never":
        return fetch_xueqiu_http_json(
            XUEQIU_STATUS_URL,
            params=params,
            referer=referer,
            cookie=cookie or xueqiu_cookie_header(),
            timeout=timeout,
        )
    if mode == "always":
        session = _open_xueqiu_browser_session(xq_symbol, timeout=timeout)
        try:
            return _browser_fetch_status_json(session, xq_symbol, page=page, count=count)
        finally:
            session.close()
    try:
        return fetch_xueqiu_http_json(
            XUEQIU_STATUS_URL,
            params=params,
            referer=referer,
            cookie=cookie or xueqiu_cookie_header(),
            timeout=timeout,
        )
    except XueqiuClientError as exc:
        if not drission_available():
            raise exc
        session = _open_xueqiu_browser_session(xq_symbol, timeout=timeout)
        try:
            return _browser_fetch_status_json(session, xq_symbol, page=page, count=count)
        finally:
            session.close()


def fetch_xueqiu_http_json(
    url: str,
    *,
    params: dict[str, Any],
    referer: str,
    cookie: str,
    timeout: int = 15,
) -> dict[str, Any]:
    query = urlencode(params)
    full_url = f"{url}?{query}"
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": referer,
        "Origin": "https://xueqiu.com",
        "X-Requested-With": "XMLHttpRequest",
    }
    if cookie:
        headers["Cookie"] = cookie

    body = ""
    if curl_cffi_available():
        try:
            from curl_cffi import requests as creq

            response = creq.get(
                url,
                params=params,
                headers=headers,
                impersonate="chrome124",
                timeout=timeout,
            )
            body = response.text
        except Exception as exc:
            raise XueqiuClientError(f"xueqiu request failed: {exc}") from exc
    else:
        request = Request(full_url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="ignore")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise XueqiuClientError(f"xueqiu request failed: {exc}") from exc

    if body.lstrip().startswith("<"):
        raise XueqiuClientError("xueqiu blocked the request (WAF/login); refresh KEIKO_XUEQIU_COOKIE")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise XueqiuClientError(f"xueqiu returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise XueqiuClientError("xueqiu returned unexpected payload")
    if payload.get("error_code") not in (None, 0, "0"):
        message = str(payload.get("error_description") or payload.get("error_code") or "xueqiu error")
        raise XueqiuClientError(message)
    return payload


def xueqiu_symbol(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    match = re.match(r"(\d{6})\.(SH|SZ|BJ)", text)
    if match:
        return f"{match.group(2)}{match.group(1)}"
    digits = re.sub(r"\D", "", text)
    if len(digits) != 6:
        return ""
    if digits.startswith(("5", "6", "9")):
        return f"SH{digits}"
    return f"SZ{digits}"


def xueqiu_cookie_header() -> str:
    for name in XUEQIU_COOKIE_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    for name in XUEQIU_TOKEN_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return f"xq_a_token={value}"
    values = dotenv_values()
    for name in XUEQIU_COOKIE_ENV_NAMES:
        value = values.get(name, "").strip()
        if value:
            os.environ[name] = value
            return value
    for name in XUEQIU_TOKEN_ENV_NAMES:
        value = values.get(name, "").strip()
        if value:
            os.environ[name] = value
            return f"xq_a_token={value}"
    return ""


def xueqiu_quote_configured() -> bool:
    return bool(xueqiu_cookie_header())


def xueqiu_discussion_configured() -> bool:
    return bool(xueqiu_cookie_header()) or drission_available()


def xueqiu_browser_mode() -> str:
    return normalize_browser_mode(os.environ.get("KEIKO_XUEQIU_BROWSER", "auto"))


def normalize_browser_mode(value: str) -> str:
    text = str(value or "auto").strip().lower()
    if text in {"1", "true", "yes", "always", "browser", "on"}:
        return "always"
    if text in {"0", "false", "no", "never", "off"}:
        return "never"
    return "auto"


def curl_cffi_available() -> bool:
    try:
        import curl_cffi  # noqa: F401

        return True
    except ImportError:
        return False


def drission_available() -> bool:
    try:
        import DrissionPage  # noqa: F401

        return True
    except ImportError:
        return False


def dotenv_values() -> dict[str, str]:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if not os.path.exists(env_path):
        return {}
    values: dict[str, str] = {}
    with open(env_path, encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values
