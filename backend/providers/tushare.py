from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


TUSHARE_ENDPOINT = "http://api.tushare.pro"


class TushareError(RuntimeError):
    pass


@dataclass(frozen=True)
class TushareResponse:
    api_name: str
    rows: list[dict[str, Any]]
    fields: list[str]
    message: str | None = None


class TushareClient:
    def __init__(self, token: str, endpoint: str = TUSHARE_ENDPOINT, timeout: float = 20) -> None:
        if not token.strip():
            raise TushareError("missing Tushare token")
        self.token = token.strip()
        self.endpoint = endpoint
        self.timeout = timeout

    def query(self, api_name: str, params: dict[str, Any] | None = None, fields: str = "") -> TushareResponse:
        body = {
            "api_name": api_name,
            "token": self.token,
            "params": params or {},
            "fields": fields,
        }
        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise TushareError(f"Tushare request failed: {exc}") from exc

        code = int(payload.get("code", -1))
        if code != 0:
            message = payload.get("msg") or f"Tushare returned code {code}"
            raise TushareError(str(message))

        data = payload.get("data") or {}
        response_fields = list(data.get("fields") or [])
        items = list(data.get("items") or [])
        rows = [dict(zip(response_fields, item)) for item in items]
        return TushareResponse(api_name=api_name, rows=rows, fields=response_fields, message=payload.get("msg"))

    def stock_basic(self) -> list[dict[str, Any]]:
        return self.query(
            "stock_basic",
            params={"exchange": "", "list_status": "L"},
            fields="ts_code,symbol,name,area,industry,market,exchange,curr_type,list_date",
        ).rows

    def daily(self, ts_code: str, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        params = {"ts_code": ts_code}
        params.update(date_window_params(start_date, end_date))
        return self.query(
            "daily",
            params=params,
            fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        ).rows

    def daily_basic(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {"ts_code": ts_code}
        params.update(date_window_params(start_date, end_date))
        return self.query(
            "daily_basic",
            params=params,
            fields=(
                "ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio,"
                "pe,pe_ttm,pb,ps,ps_ttm,total_share,float_share,total_mv,circ_mv"
            ),
        ).rows

    def income(self, ts_code: str, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        return self.query(
            "income",
            params={"ts_code": ts_code, **date_window_params(start_date, end_date)},
            fields="ts_code,ann_date,f_ann_date,end_date,total_revenue,revenue,n_income,n_income_attr_p,basic_eps",
        ).rows

    def fina_indicator(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.query(
            "fina_indicator",
            params={"ts_code": ts_code, **date_window_params(start_date, end_date)},
            fields=(
                "ts_code,ann_date,end_date,roe,roe_waa,roe_dt,netprofit_margin,"
                "grossprofit_margin,ocf_to_or,debt_to_assets,or_yoy,tr_yoy,netprofit_yoy,q_roe,rd_exp"
            ),
        ).rows


def latest_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    clean_rows = [row for row in rows if row.get(key)]
    if not clean_rows:
        return None
    return sorted(clean_rows, key=lambda row: str(row.get(key) or ""), reverse=True)[0]


def recent_tushare_date_window(days: int = 14) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def financial_date_window(days: int = 760) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def date_window_params(start_date: str | None, end_date: str | None) -> dict[str, str]:
    params: dict[str, str] = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    return params
