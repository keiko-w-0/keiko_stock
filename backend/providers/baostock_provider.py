from __future__ import annotations

import multiprocessing as mp
import queue
import socket
import time
from contextlib import contextmanager
from typing import Any


BAOSTOCK_DAILY_FIELDS = (
    "date,code,open,high,low,close,preclose,volume,amount,adjustflag,"
    "turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
)


class BaostockError(RuntimeError):
    pass


DEFAULT_HISTORY_RETRIES = 3
DEFAULT_HISTORY_RETRY_DELAYS = (3.0, 8.0, 20.0)
DEFAULT_HISTORY_SOCKET_TIMEOUT = 20.0
DEFAULT_FINANCIAL_BATCH_TIMEOUT = 300.0
DEFAULT_REPORT_BATCH_TIMEOUT = 180.0
BAOSTOCK_FINANCIAL_SECTIONS = {
    "profit": "query_profit_data",
    "operation": "query_operation_data",
    "growth": "query_growth_data",
    "balance": "query_balance_data",
    "cash_flow": "query_cash_flow_data",
    "dupont": "query_dupont_data",
}
BAOSTOCK_REPORT_SECTIONS = {
    "performance_express": "query_performance_express_report",
    "forecast": "query_forecast_report",
}


def baostock_symbol(symbol: str) -> str:
    clean = symbol.strip().lower()
    if clean.startswith(("sh.", "sz.", "bj.")):
        return clean
    upper = symbol.strip().upper()
    code = upper.split(".")[0]
    suffix = upper.split(".")[-1] if "." in upper else ""
    if suffix == "SH" or code.startswith(("5", "6", "9")):
        return f"sh.{code}"
    if suffix == "BJ" or code.startswith(("4", "8")):
        return f"bj.{code}"
    return f"sz.{code}"


def standard_symbol(code: str) -> str:
    clean = code.strip().lower()
    if "." not in clean:
        return clean.upper()
    exchange, raw_code = clean.split(".", 1)
    suffix = {"sh": "SH", "sz": "SZ", "bj": "BJ"}.get(exchange, exchange.upper())
    return f"{raw_code.upper()}.{suffix}"


def query_baostock_history(
    symbol: str,
    start_date: str,
    end_date: str,
    adjustflag: str = "2",
) -> list[dict[str, Any]]:
    results, errors = query_baostock_history_batch([symbol], start_date, end_date, adjustflag=adjustflag)
    if errors and symbol not in results:
        raise BaostockError(errors[0]["error"])
    return results.get(symbol, [])


def query_baostock_history_batch(
    symbols: list[str],
    start_date: str,
    end_date: str,
    date_ranges_by_symbol: dict[str, list[tuple[str, str]] | tuple[str, str]] | None = None,
    adjustflag: str = "2",
    retries: int = DEFAULT_HISTORY_RETRIES,
    socket_timeout: float = DEFAULT_HISTORY_SOCKET_TIMEOUT,
    per_symbol_sleep: float = 0.1,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, str]]]:
    import baostock as bs

    with baostock_socket_timeout(socket_timeout):
        login_baostock_with_retries(bs, retries)
        results: dict[str, list[dict[str, Any]]] = {}
        errors: list[dict[str, str]] = []
        try:
            for symbol in symbols:
                symbol_ranges = normalize_symbol_date_ranges(
                    date_ranges_by_symbol.get(symbol, (start_date, end_date))
                    if date_ranges_by_symbol
                    else (start_date, end_date)
                )
                symbol_rows: list[dict[str, Any]] = []
                if not symbol_ranges:
                    results[symbol] = []
                    continue
                range_failed = False
                for symbol_start, symbol_end in symbol_ranges:
                    success = False
                    last_error: Exception | None = None
                    for attempt in range(retries + 1):
                        if attempt:
                            time.sleep(retry_delay(attempt))
                            safe_logout(bs)
                            try:
                                login_baostock(bs)
                            except Exception as exc:
                                last_error = exc
                                continue
                        try:
                            result = bs.query_history_k_data_plus(
                                baostock_symbol(symbol),
                                BAOSTOCK_DAILY_FIELDS,
                                start_date=symbol_start,
                                end_date=symbol_end,
                                frequency="d",
                                adjustflag=adjustflag,
                            )
                            symbol_rows.extend(result_rows(result, "query_history_k_data_plus"))
                            success = True
                            break
                        except Exception as exc:
                            last_error = exc
                    if not success:
                        range_failed = True
                        errors.append(
                            {
                                "symbol": symbol,
                                "start_date": symbol_start,
                                "end_date": symbol_end,
                                "error": str(last_error) if last_error else "BaoStock query failed",
                                "attempts": str(retries + 1),
                            }
                        )
                if symbol_rows or not range_failed:
                    results[symbol] = symbol_rows
                if per_symbol_sleep > 0:
                    time.sleep(per_symbol_sleep)
            return results, errors
        finally:
            safe_logout(bs)


def normalize_symbol_date_ranges(value: list[tuple[str, str]] | tuple[str, str]) -> list[tuple[str, str]]:
    if isinstance(value, tuple):
        ranges = [value]
    else:
        ranges = value
    return [(start, end) for start, end in ranges if start <= end]


def query_baostock_basic(code: str = "", code_name: str = "") -> list[dict[str, Any]]:
    import baostock as bs

    def query() -> list[dict[str, Any]]:
        result = bs.query_stock_basic(code=baostock_symbol(code) if code else "", code_name=code_name)
        return result_rows(result, "query_stock_basic")

    return run_baostock_operation(bs, query, "query_stock_basic")


def query_baostock_all_stock(day: str) -> list[dict[str, Any]]:
    import baostock as bs

    def query() -> list[dict[str, Any]]:
        result = bs.query_all_stock(day=day)
        return result_rows(result, "query_all_stock")

    return run_baostock_operation(bs, query, "query_all_stock")


def query_baostock_quarterly_financials_batch(
    symbols: list[str],
    periods: list[tuple[int, int]],
    periods_by_symbol: dict[str, list[tuple[int, int]]] | None = None,
    retries: int = DEFAULT_HISTORY_RETRIES,
    socket_timeout: float = DEFAULT_HISTORY_SOCKET_TIMEOUT,
    per_call_sleep: float = 0.05,
) -> tuple[dict[str, dict[str, dict[str, list[dict[str, Any]]]]], list[dict[str, str]]]:
    import baostock as bs

    with baostock_socket_timeout(socket_timeout):
        login_baostock_with_retries(bs, retries)
        results: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
        errors: list[dict[str, str]] = []
        try:
            for symbol in symbols:
                code = baostock_symbol(symbol)
                symbol_periods = periods_by_symbol.get(symbol, periods) if periods_by_symbol else periods
                for year, quarter in symbol_periods:
                    period_key = f"{year}Q{quarter}"
                    for section, function_name in BAOSTOCK_FINANCIAL_SECTIONS.items():
                        try:
                            rows = query_baostock_result_with_retries(
                                bs,
                                function_name,
                                f"{function_name}:{symbol}:{period_key}",
                                retries,
                                code=code,
                                year=year,
                                quarter=quarter,
                            )
                            if rows:
                                results.setdefault(symbol, {}).setdefault(period_key, {})[section] = rows
                        except Exception as exc:
                            errors.append({"symbol": symbol, "period": period_key, "section": section, "error": str(exc)})
                        if per_call_sleep > 0:
                            time.sleep(per_call_sleep)
            return results, errors
        finally:
            safe_logout(bs)


def query_baostock_company_reports_batch(
    symbols: list[str],
    start_date: str,
    end_date: str,
    retries: int = DEFAULT_HISTORY_RETRIES,
    socket_timeout: float = DEFAULT_HISTORY_SOCKET_TIMEOUT,
    per_call_sleep: float = 0.05,
) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], list[dict[str, str]]]:
    import baostock as bs

    with baostock_socket_timeout(socket_timeout):
        login_baostock_with_retries(bs, retries)
        results: dict[str, dict[str, list[dict[str, Any]]]] = {}
        errors: list[dict[str, str]] = []
        try:
            for symbol in symbols:
                code = baostock_symbol(symbol)
                for section, function_name in BAOSTOCK_REPORT_SECTIONS.items():
                    try:
                        rows = query_baostock_result_with_retries(
                            bs,
                            function_name,
                            f"{function_name}:{symbol}",
                            retries,
                            code=code,
                            start_date=start_date,
                            end_date=end_date,
                        )
                        if rows:
                            results.setdefault(symbol, {})[section] = rows
                    except Exception as exc:
                        errors.append({"symbol": symbol, "section": section, "error": str(exc)})
                    if per_call_sleep > 0:
                        time.sleep(per_call_sleep)
            return results, errors
        finally:
            safe_logout(bs)


def query_baostock_quarterly_financials_batch_guarded(
    symbols: list[str],
    periods: list[tuple[int, int]],
    periods_by_symbol: dict[str, list[tuple[int, int]]] | None = None,
    timeout_seconds: float = DEFAULT_FINANCIAL_BATCH_TIMEOUT,
) -> tuple[dict[str, dict[str, dict[str, list[dict[str, Any]]]]], list[dict[str, str]]]:
    return run_baostock_child_with_timeout(
        query_baostock_quarterly_financials_batch,
        (symbols, periods),
        {"periods_by_symbol": periods_by_symbol},
        timeout_seconds,
        "BaoStock quarterly financials",
    )


def query_baostock_company_reports_batch_guarded(
    symbols: list[str],
    start_date: str,
    end_date: str,
    timeout_seconds: float = DEFAULT_REPORT_BATCH_TIMEOUT,
) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], list[dict[str, str]]]:
    return run_baostock_child_with_timeout(
        query_baostock_company_reports_batch,
        (symbols, start_date, end_date),
        {},
        timeout_seconds,
        "BaoStock company reports",
    )


def run_baostock_child_with_timeout(
    target: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    timeout_seconds: float,
    label: str,
) -> Any:
    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue(maxsize=1)
    process = ctx.Process(target=baostock_child_entry, args=(result_queue, target, args, kwargs))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join(5)
        raise BaostockError(f"{label} timed out after {timeout_seconds:.0f}s")
    try:
        kind, payload = result_queue.get_nowait()
    except queue.Empty as exc:
        raise BaostockError(f"{label} exited without returning a result") from exc
    if kind == "ok":
        return payload
    raise BaostockError(str(payload))


def baostock_child_entry(result_queue: Any, target: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    try:
        result_queue.put(("ok", target(*args, **kwargs)))
    except Exception as exc:
        result_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def result_rows(result: Any, label: str) -> list[dict[str, Any]]:
    if result.error_code != "0":
        raise BaostockError(f"BaoStock {label} failed: {result.error_msg}")
    rows = []
    while result.next():
        rows.append(dict(zip(result.fields, result.get_row_data())))
    return rows


def login_baostock(bs: Any) -> None:
    login = bs.login()
    if login.error_code != "0":
        raise BaostockError(f"BaoStock login failed: {login.error_msg}")


def login_baostock_with_retries(bs: Any, retries: int = DEFAULT_HISTORY_RETRIES) -> None:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(retry_delay(attempt))
            safe_logout(bs)
        try:
            login_baostock(bs)
            return
        except Exception as exc:
            last_error = exc
    raise BaostockError(f"BaoStock login failed after {retries + 1} attempts: {last_error}")


def safe_logout(bs: Any) -> None:
    try:
        bs.logout()
    except Exception:
        pass


def retry_delay(attempt: int) -> float:
    index = max(0, min(attempt - 1, len(DEFAULT_HISTORY_RETRY_DELAYS) - 1))
    return DEFAULT_HISTORY_RETRY_DELAYS[index]


def query_baostock_result_with_retries(
    bs: Any,
    function_name: str,
    label: str,
    retries: int,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if attempt:
                time.sleep(retry_delay(attempt))
                safe_logout(bs)
                login_baostock(bs)
            result = getattr(bs, function_name)(**kwargs)
            return result_rows(result, function_name)
        except Exception as exc:
            last_error = exc
    raise BaostockError(f"BaoStock {label} failed after {retries + 1} attempts: {last_error}")


def run_baostock_operation(
    bs: Any,
    callback: Any,
    label: str,
    retries: int = DEFAULT_HISTORY_RETRIES,
    socket_timeout: float = DEFAULT_HISTORY_SOCKET_TIMEOUT,
) -> Any:
    last_error: Exception | None = None
    with baostock_socket_timeout(socket_timeout):
        for attempt in range(retries + 1):
            if attempt:
                time.sleep(retry_delay(attempt))
            try:
                login_baostock(bs)
                return callback()
            except Exception as exc:
                last_error = exc
            finally:
                safe_logout(bs)
    raise BaostockError(f"BaoStock {label} failed after {retries + 1} attempts: {last_error}")


@contextmanager
def baostock_socket_timeout(seconds: float):
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(seconds)
    try:
        yield
    finally:
        socket.setdefaulttimeout(previous_timeout)
