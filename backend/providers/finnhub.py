from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FINNHUB_ENDPOINT = "https://finnhub.io/api/v1"


class FinnhubError(RuntimeError):
    pass


@dataclass(frozen=True)
class FinnhubResponse:
    path: str
    payload: dict[str, Any] | list[dict[str, Any]]


class FinnhubClient:
    def __init__(self, token: str, endpoint: str = FINNHUB_ENDPOINT, timeout: float = 20) -> None:
        if not token.strip():
            raise FinnhubError("missing Finnhub token")
        self.token = token.strip()
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, params: dict[str, Any] | None = None) -> FinnhubResponse:
        query = {key: value for key, value in (params or {}).items() if value not in (None, "")}
        query["token"] = self.token
        url = f"{self.endpoint}/{path.lstrip('/')}?{urlencode(query)}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "KeikoStockAI/0.1"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise FinnhubError(f"Finnhub HTTP {exc.code}: {detail or exc.reason}") from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise FinnhubError(f"Finnhub request failed: {exc}") from exc

        if isinstance(payload, dict) and payload.get("error"):
            raise FinnhubError(str(payload["error"]))
        return FinnhubResponse(path=path, payload=payload)

    def quote(self, symbol: str) -> dict[str, Any]:
        payload = self.get("quote", {"symbol": symbol}).payload
        return payload if isinstance(payload, dict) else {}

    def company_profile(self, symbol: str) -> dict[str, Any]:
        payload = self.get("stock/profile2", {"symbol": symbol}).payload
        return payload if isinstance(payload, dict) else {}

    def basic_financials(self, symbol: str, metric: str = "all") -> dict[str, Any]:
        payload = self.get("stock/metric", {"symbol": symbol, "metric": metric}).payload
        return payload if isinstance(payload, dict) else {}

    def company_news(self, symbol: str, from_date: date, to_date: date) -> list[dict[str, Any]]:
        payload = self.get(
            "company-news",
            {"symbol": symbol, "from": from_date.isoformat(), "to": to_date.isoformat()},
        ).payload
        return payload if isinstance(payload, list) else []
