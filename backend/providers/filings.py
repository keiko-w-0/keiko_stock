from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Any


CNINFO_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_TOP_SEARCH_URL = "https://www.cninfo.com.cn/new/information/topSearch/query"
CNINFO_STATIC_BASE_URL = "https://static.cninfo.com.cn/"
CNINFO_REFERER = "https://www.cninfo.com.cn/new/disclosure"

SSE_QUERY_URL = "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do"
SSE_BASE_URL = "https://www.sse.com.cn"
SSE_REFERER = "https://www.sse.com.cn/disclosure/listedinfo/announcement/"

SZSE_QUERY_URL = "https://www.szse.cn/api/disc/announcement/annList"
SZSE_DETAIL_URL = "https://www.szse.cn/api/disc/announcement/bulletin_detail/{announcement_id}"
SZSE_DOWNLOAD_BASE_URL = "https://disc.static.szse.cn/download"
SZSE_REFERER = "https://www.szse.cn/disclosure/listed/notice/index.html"

HKEX_PREFIX_URL = "https://www1.hkexnews.hk/search/prefix.do"
HKEX_TITLE_SEARCH_URL = "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh"
HKEX_BASE_URL = "https://www1.hkexnews.hk"

CN_TZ = timezone(timedelta(hours=8))
DEFAULT_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36 "
    "KeikoStockAI/0.1"
)


class FilingFetchError(RuntimeError):
    def __init__(self, source: str, message: str) -> None:
        self.source = source
        super().__init__(message)


@dataclass
class ParsedSymbol:
    original: str
    code: str
    exchange: str
    normalized: str


@dataclass
class FilingDocument:
    source: str
    symbol: str
    stock_code: str
    company: str
    title: str
    published_at: str
    url: str
    file_type: str = ""
    category: str = ""
    source_tier: str = "S"
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FilingSearchResponse:
    source: str
    page: int
    page_size: int
    total: int | None
    documents: list[FilingDocument]
    raw_meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "page": self.page,
            "page_size": self.page_size,
            "total": self.total,
            "count": len(self.documents),
            "documents": [item.to_dict() for item in self.documents],
            "raw_meta": self.raw_meta,
        }


@dataclass
class CninfoSecurity:
    code: str
    org_id: str
    column: str
    plate: str
    company: str = ""


def normalize_symbol(symbol: str) -> ParsedSymbol:
    raw = symbol.strip().upper().replace(" ", "")
    if not raw:
        raise ValueError("symbol is required")

    if "." in raw:
        code, exchange = raw.rsplit(".", 1)
    elif raw.isdigit() and len(raw) == 5:
        code, exchange = raw, "HK"
    elif raw.isdigit() and len(raw) <= 4:
        code, exchange = raw.zfill(5), "HK"
    elif raw.isdigit() and len(raw) == 6:
        exchange = "SH" if raw.startswith(("5", "6", "9")) else "SZ"
        code = raw
    else:
        raise ValueError("symbol must look like 600519.SH, 002594.SZ or 0700.HK")

    if exchange == "HK":
        code = code.zfill(5)
    normalized = f"{code}.{exchange}"
    return ParsedSymbol(original=symbol, code=code, exchange=exchange, normalized=normalized)


def normalize_date_range(start_date: str | None, end_date: str | None) -> tuple[str, str]:
    today = date.today()
    end_value = _parse_date(end_date, today)
    start_value = _parse_date(start_date, end_value - timedelta(days=90))
    if start_value > end_value:
        raise ValueError("start_date must be earlier than or equal to end_date")
    return start_value.isoformat(), end_value.isoformat()


def clamp_page_size(page_size: int, maximum: int = 100) -> int:
    return max(1, min(page_size, maximum))


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    cleaned = value.strip().replace("/", "-")
    return datetime.strptime(cleaned, "%Y-%m-%d").date()


def _http_text(
    source: str,
    url: str,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    form: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"

    data: bytes | None = None
    request_headers = {
        "Accept": "application/json, text/javascript, text/html, */*",
        "Accept-Encoding": "identity",
        "User-Agent": USER_AGENT,
    }
    request_headers.update(headers or {})

    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    elif form is not None:
        data = urllib.parse.urlencode(form, doseq=True).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")

    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise FilingFetchError(source, f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise FilingFetchError(source, str(exc.reason)) from exc


def _http_json(source: str, url: str, **kwargs: Any) -> Any:
    text = _http_text(source, url, **kwargs)
    try:
        return json.loads(_strip_jsonp(text))
    except json.JSONDecodeError as exc:
        raise FilingFetchError(source, f"invalid JSON response: {text[:160]}") from exc


def _strip_jsonp(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped
    match = re.search(r"^[^(]+\((.*)\)\s*;?\s*$", stripped, flags=re.S)
    if match:
        return match.group(1)
    first_brace = min([index for index in [stripped.find("{"), stripped.find("[")] if index >= 0], default=-1)
    last_brace = max(stripped.rfind("}"), stripped.rfind("]"))
    if first_brace >= 0 and last_brace > first_brace:
        return stripped[first_brace : last_brace + 1]
    return stripped


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item is not None)
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return ""


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _cninfo_timestamp(value: Any) -> str:
    timestamp = _safe_int(value)
    if timestamp is None:
        return _clean_text(value)
    return datetime.fromtimestamp(timestamp / 1000, tz=CN_TZ).isoformat(timespec="seconds")


def _format_hkex_date(value: str) -> str:
    return value.replace("-", "")


def _absolute_url(base: str, path: str) -> str:
    if not path:
        return ""
    return urllib.parse.urljoin(base, path)


def _cninfo_column_plate(exchange: str) -> tuple[str, str]:
    if exchange == "SH":
        return "sse", "sh"
    if exchange == "BJ":
        return "bj", "bj"
    return "szse", "sz"


def _fallback_cninfo_org_id(code: str, exchange: str) -> str:
    prefix = {"SH": "gssh", "BJ": "gsbj"}.get(exchange, "gssz")
    return f"{prefix}{code.zfill(7)}"


class CninfoFilingProvider:
    source = "cninfo"
    source_label = "CNINFO"

    def supports(self, symbol: ParsedSymbol) -> bool:
        return symbol.exchange in {"SH", "SZ", "BJ"}

    def search(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        keyword: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 30,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> FilingSearchResponse:
        parsed = normalize_symbol(symbol)
        if not self.supports(parsed):
            raise FilingFetchError(self.source, f"CNINFO does not support {parsed.exchange}")

        security = self.resolve_security(parsed, timeout=timeout)
        payload = {
            "stock": f"{security.code},{security.org_id}" if security.org_id else security.code,
            "tabName": "fulltext",
            "pageSize": str(page_size),
            "pageNum": str(page),
            "column": security.column,
            "category": category,
            "plate": security.plate,
            "seDate": f"{start_date}~{end_date}",
            "searchkey": keyword,
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        data = _http_json(
            self.source,
            CNINFO_QUERY_URL,
            method="POST",
            form=payload,
            headers={
                "Origin": "https://www.cninfo.com.cn",
                "Referer": CNINFO_REFERER,
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=timeout,
        )
        announcements = data.get("announcements") or []
        documents = [
            self._document_from_item(item, parsed.normalized, security.company)
            for item in announcements
            if isinstance(item, dict)
        ]
        return FilingSearchResponse(
            source=self.source,
            page=page,
            page_size=page_size,
            total=_safe_int(data.get("totalRecordNum") or data.get("totalAnnouncement")),
            documents=documents,
            raw_meta={
                "has_more": bool(data.get("hasMore")),
                "total_securities": data.get("totalSecurities"),
                "org_id": security.org_id,
            },
        )

    def resolve_security(self, parsed: ParsedSymbol, *, timeout: int = DEFAULT_TIMEOUT) -> CninfoSecurity:
        column, plate = _cninfo_column_plate(parsed.exchange)
        fallback = CninfoSecurity(
            code=parsed.code,
            org_id=_fallback_cninfo_org_id(parsed.code, parsed.exchange),
            column=column,
            plate=plate,
        )
        try:
            data = _http_json(
                self.source,
                CNINFO_TOP_SEARCH_URL,
                method="POST",
                form={"keyWord": parsed.code, "maxNum": "10"},
                headers={"Origin": "https://www.cninfo.com.cn", "Referer": CNINFO_REFERER},
                timeout=timeout,
            )
        except FilingFetchError:
            return fallback

        rows = data if isinstance(data, list) else data.get("keyBoardList", []) if isinstance(data, dict) else []
        for item in rows:
            if not isinstance(item, dict) or str(item.get("code", "")).strip() != parsed.code:
                continue
            return CninfoSecurity(
                code=parsed.code,
                org_id=_clean_text(item.get("orgId")) or fallback.org_id,
                column=_clean_text(item.get("column")) or column,
                plate=_clean_text(item.get("plate")) or plate,
                company=_clean_text(item.get("zwjc") or item.get("name") or item.get("secName")),
            )
        return fallback

    def _document_from_item(self, item: dict[str, Any], symbol: str, company_fallback: str) -> FilingDocument:
        adjunct_url = _clean_text(item.get("adjunctUrl"))
        return FilingDocument(
            source=self.source,
            symbol=symbol,
            stock_code=_clean_text(item.get("secCode")),
            company=_clean_text(item.get("secName")) or company_fallback,
            title=_clean_text(item.get("announcementTitle")),
            published_at=_cninfo_timestamp(item.get("announcementTime")),
            url=_absolute_url(CNINFO_STATIC_BASE_URL, adjunct_url),
            file_type=_clean_text(item.get("adjunctType")) or adjunct_url.rsplit(".", 1)[-1].upper(),
            category=_clean_text(item.get("announcementTypeName") or item.get("columnName")),
            raw=item,
        )


class SseFilingProvider:
    source = "sse"
    source_label = "SSE"

    def supports(self, symbol: ParsedSymbol) -> bool:
        return symbol.exchange == "SH"

    def search(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        keyword: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 25,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> FilingSearchResponse:
        parsed = normalize_symbol(symbol)
        if not self.supports(parsed):
            raise FilingFetchError(self.source, f"SSE only supports .SH symbols")

        timestamp = int(time.time() * 1000)
        report_type, report_type2 = _sse_report_type(category)
        params = {
            "jsonCallBack": f"jsonpCallback{timestamp}",
            "isPagination": "true",
            "productId": parsed.code,
            "keyWord": keyword,
            "securityType": "0101,120100,020100,020200,120200",
            "reportType": report_type,
            "reportType2": report_type2,
            "beginDate": start_date,
            "endDate": end_date,
            "pageHelp.pageSize": str(page_size),
            "pageHelp.pageNo": str(page),
            "pageHelp.beginPage": str(page),
            "pageHelp.cacheSize": "1",
            "pageHelp.endPage": str(page),
            "_": str(timestamp),
        }
        data = _http_json(
            self.source,
            SSE_QUERY_URL,
            params=params,
            headers={"Referer": SSE_REFERER, "X-Requested-With": "XMLHttpRequest"},
            timeout=timeout,
        )
        rows = data.get("result") or data.get("pageHelp", {}).get("data") or []
        documents = [
            self._document_from_item(item, parsed.normalized)
            for item in rows
            if isinstance(item, dict)
        ]
        page_help = data.get("pageHelp", {}) if isinstance(data.get("pageHelp"), dict) else {}
        return FilingSearchResponse(
            source=self.source,
            page=page,
            page_size=page_size,
            total=_safe_int(page_help.get("total") or page_help.get("totalCount") or data.get("total")),
            documents=documents,
            raw_meta={"report_type": report_type, "report_type2": report_type2},
        )

    def _document_from_item(self, item: dict[str, Any], symbol: str) -> FilingDocument:
        url_path = _clean_text(_first(item, "URL", "url"))
        return FilingDocument(
            source=self.source,
            symbol=symbol,
            stock_code=_clean_text(_first(item, "SECURITY_CODE", "securityCode")),
            company=_clean_text(_first(item, "SECURITY_NAME", "SECURITY_NAME_CN", "securityName")),
            title=_clean_text(_first(item, "TITLE", "title")),
            published_at=_clean_text(_first(item, "SSEDATE", "BULLETIN_DATE", "BULLETIN_PUBLISH_DATE", "ADDDATE", "CREATE_TIME", "date")),
            url=_absolute_url(SSE_BASE_URL, url_path),
            file_type=url_path.rsplit(".", 1)[-1].upper() if "." in url_path else "",
            category=_clean_text(_first(item, "BULLETIN_TYPE", "BULLETIN_TYPE_DESC", "type")),
            raw=item,
        )


def _sse_report_type(category: str) -> tuple[str, str]:
    category = category.strip().lower()
    mapping = {
        "annual": ("YEARLY", "DQBG"),
        "yearly": ("YEARLY", "DQBG"),
        "semiannual": ("QUATER2", "DQBG"),
        "quarter1": ("QUATER1", "DQBG"),
        "quarter3": ("QUATER3", "DQBG"),
        "periodic": ("ALL", "DQBG"),
        "temporary": ("ALL", "LSGG"),
    }
    return mapping.get(category, ("ALL", ""))


class SzseFilingProvider:
    source = "szse"
    source_label = "SZSE"

    def supports(self, symbol: ParsedSymbol) -> bool:
        return symbol.exchange == "SZ"

    def search(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        keyword: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 30,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> FilingSearchResponse:
        parsed = normalize_symbol(symbol)
        if not self.supports(parsed):
            raise FilingFetchError(self.source, f"SZSE only supports .SZ symbols")

        body: dict[str, Any] = {
            "seDate": [start_date, end_date],
            "stock": [parsed.code],
            "channelCode": ["listedNotice_disc"],
            "pageSize": page_size,
            "pageNum": page,
        }
        if keyword:
            body["keyword"] = keyword
        category_id = _szse_category_id(category)
        if category_id:
            body["bigCategoryId"] = [category_id]

        data = _http_json(
            self.source,
            f"{SZSE_QUERY_URL}?random={time.time()}",
            method="POST",
            json_body=body,
            headers={
                "Origin": "https://www.szse.cn",
                "Referer": SZSE_REFERER,
                "X-Request-Type": "ajax",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=timeout,
        )
        rows = data.get("data") or []
        documents = [
            self._document_from_item(item, parsed.normalized, timeout=timeout)
            for item in rows
            if isinstance(item, dict)
        ]
        return FilingSearchResponse(
            source=self.source,
            page=page,
            page_size=page_size,
            total=_safe_int(data.get("announceCount")),
            documents=documents,
            raw_meta={"category_id": category_id},
        )

    def _document_from_item(self, item: dict[str, Any], symbol: str, *, timeout: int) -> FilingDocument:
        attach_path = _clean_text(item.get("attachPath"))
        raw = dict(item)
        if not attach_path and item.get("id"):
            detail = self._fetch_detail(str(item["id"]), timeout=timeout)
            raw["detail"] = detail
            attach_path = _clean_text(detail.get("attachPath"))

        stock_code = _clean_text(item.get("secCode") or item.get("stockCode"))
        company = _clean_text(item.get("secName") or item.get("stockName"))
        return FilingDocument(
            source=self.source,
            symbol=symbol,
            stock_code=stock_code,
            company=company,
            title=_clean_text(item.get("title")),
            published_at=_clean_text(item.get("publishTime") or item.get("publishDate")),
            url=_szse_download_url(attach_path),
            file_type=attach_path.rsplit(".", 1)[-1].upper() if "." in attach_path else "",
            category=_clean_text(item.get("bigCategoryName") or item.get("categoryName") or item.get("channelName")),
            raw=raw,
        )

    def _fetch_detail(self, announcement_id: str, *, timeout: int) -> dict[str, Any]:
        try:
            detail = _http_json(
                self.source,
                SZSE_DETAIL_URL.format(announcement_id=urllib.parse.quote(announcement_id)),
                headers={"Referer": SZSE_REFERER},
                timeout=timeout,
            )
        except FilingFetchError:
            return {}
        return detail if isinstance(detail, dict) else {}


def _szse_download_url(attach_path: str) -> str:
    if not attach_path:
        return ""
    if attach_path.startswith("http://") or attach_path.startswith("https://"):
        return attach_path
    return f"{SZSE_DOWNLOAD_BASE_URL}{attach_path if attach_path.startswith('/') else '/' + attach_path}"


def _szse_category_id(category: str) -> str:
    category = category.strip().lower()
    mapping = {
        "annual": "010301",
        "yearly": "010301",
        "semiannual": "010303",
        "quarter": "010305",
        "temporary": "0101",
    }
    return mapping.get(category, category if category.startswith("01") else "")


class HkexTitleTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[dict[str, str]]] = []
        self._row: list[dict[str, str]] | None = None
        self._cell: dict[str, str] | None = None
        self._href: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = {"text": "", "href": ""}
        elif tag == "a" and self._cell is not None:
            self._href = attrs_dict.get("href", "")
            if self._href and not self._cell["href"]:
                self._cell["href"] = self._href

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._cell["text"] = _clean_text(self._cell["text"])
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(cell.get("text") or cell.get("href") for cell in self._row):
                self.rows.append(self._row)
            self._row = None


class HkexnewsFilingProvider:
    source = "hkexnews"
    source_label = "HKEXnews"

    def supports(self, symbol: ParsedSymbol) -> bool:
        return symbol.exchange == "HK"

    def search(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        keyword: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 50,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> FilingSearchResponse:
        parsed = normalize_symbol(symbol)
        if not self.supports(parsed):
            raise FilingFetchError(self.source, "HKEXnews only supports .HK symbols")

        stock_id, company = self.resolve_stock_id(parsed.code, timeout=timeout)
        if not stock_id:
            raise FilingFetchError(self.source, f"failed to resolve HKEX stockId for {parsed.code}")

        form = {
            "lang": "ZH",
            "category": category or "0",
            "market": "SEHK",
            "searchType": "0",
            "documentType": "",
            "t1code": "",
            "t2Gcode": "",
            "t2code": "",
            "stockId": stock_id,
            "from": _format_hkex_date(start_date),
            "to": _format_hkex_date(end_date),
            "MB-Daterange": "0",
        }
        if keyword:
            form["keyword"] = keyword

        html = _http_text(
            self.source,
            HKEX_TITLE_SEARCH_URL,
            method="POST",
            form=form,
            headers={"Referer": "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh"},
            timeout=timeout,
        )
        documents = self._documents_from_html(html, parsed.normalized, parsed.code, company)
        if page > 1 or page_size:
            start_index = max(0, (page - 1) * page_size)
            documents = documents[start_index : start_index + page_size]
        return FilingSearchResponse(
            source=self.source,
            page=page,
            page_size=page_size,
            total=None,
            documents=documents,
            raw_meta={"stock_id": stock_id, "company": company},
        )

    def resolve_stock_id(self, hk_code: str, *, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
        data = _http_json(
            self.source,
            HKEX_PREFIX_URL,
            params={
                "callback": "callback",
                "lang": "ZH",
                "type": "A",
                "name": hk_code,
                "market": "SEHK",
            },
            headers={"Referer": "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh"},
            timeout=timeout,
        )
        rows = data.get("stockInfo") or []
        for item in rows:
            if not isinstance(item, dict):
                continue
            code = _clean_text(item.get("stockCode") or item.get("code"))
            if code and code.zfill(5) != hk_code:
                continue
            return _clean_text(item.get("stockId")), _clean_text(item.get("stockName") or item.get("name"))
        return "", ""

    def _documents_from_html(
        self,
        html: str,
        symbol: str,
        stock_code: str,
        company: str,
    ) -> list[FilingDocument]:
        parser = HkexTitleTableParser()
        parser.feed(html)
        documents: list[FilingDocument] = []
        for row in parser.rows:
            href_cell = next((cell for cell in row if cell.get("href")), None)
            if not href_cell:
                continue
            href = href_cell["href"]
            if "titlesearch.xhtml" in href:
                continue
            texts = [cell["text"] for cell in row if cell["text"]]
            title = _strip_hkex_label(href_cell["text"] or _guess_hkex_title(texts))
            if not title or title.lower() in {"headline", "title"}:
                continue
            documents.append(
                FilingDocument(
                    source=self.source,
                    symbol=symbol,
                    stock_code=stock_code,
                    company=company or _guess_hkex_company(texts),
                    title=title,
                    published_at=_guess_hkex_datetime(texts),
                    url=_absolute_url(HKEX_BASE_URL, href),
                    file_type=href.rsplit(".", 1)[-1].upper() if "." in href else "",
                    category=_guess_hkex_category(texts, title),
                    raw={"row": texts, "href": href},
                )
            )
        return documents


def _guess_hkex_datetime(texts: list[str]) -> str:
    text = " ".join(texts)
    patterns = [
        (r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", "%d/%m/%Y %H:%M"),
        (r"(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2})", "%Y/%m/%d %H:%M"),
        (r"(\d{8})", "%Y%m%d"),
    ]
    for pattern, date_format in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = " ".join(match.groups()) if len(match.groups()) > 1 else match.group(1)
        try:
            parsed = datetime.strptime(value, date_format).replace(tzinfo=CN_TZ)
            return parsed.isoformat(timespec="seconds")
        except ValueError:
            continue
    return ""


def _guess_hkex_title(texts: list[str]) -> str:
    pdf_like = [text for text in texts if len(text) > 8 and not re.fullmatch(r"\d{5}", text)]
    return pdf_like[-1] if pdf_like else ""


def _strip_hkex_label(text: str) -> str:
    return re.sub(r"^(文件|File|Document)\s*:\s*", "", text, flags=re.I).strip()


def _guess_hkex_company(texts: list[str]) -> str:
    for text in texts:
        if re.fullmatch(r"[A-Z0-9 .,&'-]{3,}", text) and not re.fullmatch(r"\d+", text):
            return text
    return ""


def _guess_hkex_category(texts: list[str], title: str) -> str:
    for text in reversed(texts):
        cleaned = _strip_hkex_label(text)
        if cleaned == title:
            continue
        if re.match(r"^(發放時間|发放时间|股份代號|股份代码|股份簡稱|股份简称|文件|File|Document)\s*:", text, re.I):
            continue
        if len(cleaned) <= 80 and not re.search(r"\d{2}/\d{2}/\d{4}|\d{5}", cleaned):
            return cleaned
    return ""


FILING_PROVIDERS = {
    "cninfo": CninfoFilingProvider(),
    "sse": SseFilingProvider(),
    "szse": SzseFilingProvider(),
    "hkexnews": HkexnewsFilingProvider(),
}


def provider_source_notes() -> list[dict[str, str]]:
    return [
        {
            "source": "cninfo",
            "label": "CNINFO",
            "markets": "SH/SZ/BJ",
            "entry_url": "https://www.cninfo.com.cn/new/disclosure",
            "notes": "POST form endpoint. Use topSearch/query to resolve orgId before querying hisAnnouncement/query.",
        },
        {
            "source": "sse",
            "label": "Shanghai Stock Exchange",
            "markets": "SH",
            "entry_url": SSE_REFERER,
            "notes": "JSONP endpoint. Referer is required by the exchange web service.",
        },
        {
            "source": "szse",
            "label": "Shenzhen Stock Exchange",
            "markets": "SZ",
            "entry_url": SZSE_REFERER,
            "notes": "JSON POST endpoint. PDF URL is usually disc.static.szse.cn/download + attachPath.",
        },
        {
            "source": "hkexnews",
            "label": "HKEXnews",
            "markets": "HK",
            "entry_url": "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh",
            "notes": "Resolve stockId with prefix.do, then POST the title search form.",
        },
    ]
