from __future__ import annotations

from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .accounts import add_account_trade, fetch_account, favorites_for_account, list_accounts, set_account_favorite, trades_for_account
from .analysis import create_anomaly_run, latest_stock_analysis, shared_cache_summary
from .data_quality import health_payload, refresh_payload
from .db import ROOT_DIR, get_db, init_db
from .portfolio import account_portfolio, refresh_mock_prices, symbols_for_account
from .schemas import AnomalyInput, FavoriteToggle, TradeInput


app = FastAPI(title="Keiko Stock AI Mock Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    return health_payload()


@app.get("/api/bootstrap")
def bootstrap(account_id: str = "acct-demo-a") -> dict[str, Any]:
    with get_db() as conn:
        account = fetch_account(conn, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="account not found")

        portfolio = account_portfolio(conn, account_id)
        return {
            "account": account,
            "accounts": list_accounts(conn),
            "favorites": favorites_for_account(conn, account_id),
            "trades": trades_for_account(conn, account_id),
            "portfolio": portfolio,
            "shared_cache": shared_cache_summary(conn),
            "data_boundary": {
                "shared": ["symbols", "stock_analysis_runs", "anomaly_runs", "stock_memories"],
                "private": ["account_favorites", "account_trades", "account_positions_cache"],
            },
        }


@app.get("/api/analysis/stocks/{symbol}")
def stock_analysis(symbol: str) -> dict[str, Any]:
    with get_db() as conn:
        return latest_stock_analysis(conn, symbol)


@app.post("/api/analysis/anomalies")
def create_anomaly(payload: AnomalyInput) -> dict[str, Any]:
    with get_db() as conn:
        return create_anomaly_run(conn, payload)


@app.get("/api/accounts/{account_id}/portfolio")
def portfolio(account_id: str) -> dict[str, Any]:
    with get_db() as conn:
        return account_portfolio(conn, account_id)


@app.put("/api/accounts/{account_id}/favorites/{symbol}")
def set_favorite(account_id: str, symbol: str, payload: FavoriteToggle) -> dict[str, Any]:
    with get_db() as conn:
        favorites = set_account_favorite(conn, account_id, symbol.upper(), payload.favorite, payload.note)
    return {"account_id": account_id, "favorites": favorites}


@app.post("/api/accounts/{account_id}/trades")
def add_trade(account_id: str, payload: TradeInput) -> dict[str, Any]:
    with get_db() as conn:
        trade = add_account_trade(conn, account_id, payload)
        portfolio = account_portfolio(conn, account_id)
    return {"account_id": account_id, "trade": trade, "portfolio": portfolio}


@app.post("/api/data/refresh")
def refresh_data(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    response = refresh_payload()
    account_id = (payload or {}).get("account_id")
    scope = (payload or {}).get("scope")
    if scope == "portfolio" and account_id:
        with get_db() as conn:
            updated_prices = refresh_mock_prices(symbols_for_account(conn, account_id))
            response["updated_prices"] = updated_prices
            response["portfolio"] = account_portfolio(conn, account_id)
    return response


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")


@app.get("/index.html")
def index_html() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")


@app.get("/styles.css")
def styles() -> FileResponse:
    return FileResponse(ROOT_DIR / "styles.css")


@app.get("/app.js")
def app_js() -> FileResponse:
    return FileResponse(ROOT_DIR / "app.js")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return FileResponse(ROOT_DIR / "manifest.webmanifest")


@app.get("/service-worker.js")
def service_worker() -> FileResponse:
    return FileResponse(ROOT_DIR / "service-worker.js")


@app.get("/assets/app-icon.svg")
def app_icon() -> FileResponse:
    return FileResponse(ROOT_DIR / "assets" / "app-icon.svg")
