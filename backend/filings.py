from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from .providers.filings import (
    DEFAULT_TIMEOUT,
    FILING_PROVIDERS,
    FilingFetchError,
    clamp_page_size,
    normalize_date_range,
    normalize_symbol,
    provider_source_notes,
)


def filing_sources_payload() -> dict[str, Any]:
    return {
        "mode": "live-official-filings",
        "sources": provider_source_notes(),
        "source_values": ["auto", "all", *FILING_PROVIDERS.keys()],
        "category_hint": "Use empty for all, or common values such as annual, semiannual, quarter, periodic, temporary.",
    }


def search_filing_documents(
    *,
    symbol: str,
    source: str = "auto",
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str = "",
    category: str = "",
    page: int = 1,
    page_size: int = 30,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    try:
        parsed = normalize_symbol(symbol)
        start, end = normalize_date_range(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    selected_sources = _selected_sources(parsed.exchange, source)
    page_size = clamp_page_size(page_size)

    source_results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    documents: list[dict[str, Any]] = []

    for source_name in selected_sources:
        provider = FILING_PROVIDERS[source_name]
        if not provider.supports(parsed):
            errors.append(
                {
                    "source": source_name,
                    "message": f"{source_name} does not support {parsed.exchange}",
                }
            )
            continue
        try:
            response = provider.search(
                parsed.normalized,
                start_date=start,
                end_date=end,
                keyword=keyword.strip(),
                category=category.strip(),
                page=page,
                page_size=page_size,
                timeout=timeout,
            )
        except FilingFetchError as exc:
            errors.append({"source": exc.source, "message": str(exc)})
            continue

        response_payload = response.to_dict()
        response_payload["documents"].sort(key=lambda item: published_at_sort_value(item.get("published_at")), reverse=True)
        source_results.append(response_payload)
        documents.extend(response_payload["documents"])

    documents.sort(key=lambda item: published_at_sort_value(item.get("published_at")), reverse=True)
    return {
        "mode": "live-official-filings",
        "query": {
            "symbol": parsed.normalized,
            "source": source,
            "sources_used": selected_sources,
            "start_date": start,
            "end_date": end,
            "keyword": keyword,
            "category": category,
            "page": page,
            "page_size": page_size,
        },
        "count": len(documents),
        "documents": documents,
        "source_results": source_results,
        "errors": errors,
        "source_notes": provider_source_notes(),
    }


def _selected_sources(exchange: str, source: str) -> list[str]:
    normalized_source = source.strip().lower() or "auto"
    if normalized_source in FILING_PROVIDERS:
        return [normalized_source]
    if normalized_source == "auto":
        return [_primary_source_for_exchange(exchange)]
    if normalized_source == "all":
        if exchange == "SH":
            return ["cninfo", "sse"]
        if exchange == "SZ":
            return ["cninfo", "szse"]
        if exchange == "HK":
            return ["hkexnews"]
        return ["cninfo"]
    raise HTTPException(
        status_code=400,
        detail=f"source must be one of auto, all, {', '.join(FILING_PROVIDERS.keys())}",
    )


def _primary_source_for_exchange(exchange: str) -> str:
    if exchange == "SH":
        return "sse"
    if exchange == "SZ":
        return "szse"
    if exchange == "HK":
        return "hkexnews"
    return "cninfo"


def published_at_sort_value(value: Any) -> datetime:
    if not value:
        return datetime.min
    text = str(value).strip()
    if not text:
        return datetime.min
    normalized = text.replace("/", "-").replace("Z", "+00:00")
    if len(normalized) == 8 and normalized.isdigit():
        normalized = f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:8]}"
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.replace(tzinfo=None)
    except ValueError:
        pass
    try:
        return datetime.strptime(normalized[:10], "%Y-%m-%d")
    except ValueError:
        return datetime.min
