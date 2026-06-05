from __future__ import annotations


SYMBOLS = [
    {
        "symbol": "002594.SZ",
        "market": "A",
        "name": "比亚迪",
        "currency": "CNY",
        "exchange": "SZSE",
        "sector": "新能源",
        "industry": "汽车",
    },
    {
        "symbol": "0700.HK",
        "market": "HK",
        "name": "腾讯控股",
        "currency": "HKD",
        "exchange": "HKEX",
        "sector": "互联网",
        "industry": "平台与游戏",
    },
    {
        "symbol": "NVDA",
        "market": "US",
        "name": "NVIDIA",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "半导体",
        "industry": "AI 算力",
    },
    {
        "symbol": "600519.SH",
        "market": "A",
        "name": "贵州茅台",
        "currency": "CNY",
        "exchange": "SSE",
        "sector": "消费",
        "industry": "白酒",
    },
    {
        "symbol": "1810.HK",
        "market": "HK",
        "name": "小米集团",
        "currency": "HKD",
        "exchange": "HKEX",
        "sector": "智能硬件",
        "industry": "手机与汽车",
    },
    {
        "symbol": "AAPL",
        "market": "US",
        "name": "Apple",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "消费电子",
        "industry": "硬件与服务",
    },
]


USERS = [
    {"id": "user-demo", "email": "me@example.local", "display_name": "我的账户"},
    {"id": "user-colleague", "email": "colleague@example.local", "display_name": "同事账户"},
]


ACCOUNTS = [
    {"id": "acct-demo-a", "user_id": "user-demo", "name": "我的主账户", "base_currency": "CNY"},
    {"id": "acct-demo-b", "user_id": "user-colleague", "name": "同事观察账户", "base_currency": "CNY"},
]


FAVORITES = [
    {"account_id": "acct-demo-a", "symbol": "002594.SZ", "note": "新能源核心观察"},
    {"account_id": "acct-demo-a", "symbol": "0700.HK", "note": "港股稳健底仓候选"},
    {"account_id": "acct-demo-a", "symbol": "1810.HK", "note": "催化强但要查证"},
    {"account_id": "acct-demo-b", "symbol": "NVDA", "note": "AI 主线共享分析"},
    {"account_id": "acct-demo-b", "symbol": "AAPL", "note": "等待产品催化"},
]


TRADES = [
    {
        "id": 1,
        "account_id": "acct-demo-a",
        "symbol": "002594.SZ",
        "side": "BUY",
        "trade_date": "2026-05-27",
        "quantity": 300,
        "price": 201.4,
        "fee": 8,
        "currency": "CNY",
    },
    {
        "id": 2,
        "account_id": "acct-demo-a",
        "symbol": "002594.SZ",
        "side": "BUY",
        "trade_date": "2026-06-02",
        "quantity": 200,
        "price": 207.2,
        "fee": 6,
        "currency": "CNY",
    },
    {
        "id": 3,
        "account_id": "acct-demo-a",
        "symbol": "002594.SZ",
        "side": "SELL",
        "trade_date": "2026-06-04",
        "quantity": 100,
        "price": 213.8,
        "fee": 5,
        "currency": "CNY",
    },
    {
        "id": 4,
        "account_id": "acct-demo-a",
        "symbol": "0700.HK",
        "side": "BUY",
        "trade_date": "2026-05-29",
        "quantity": 200,
        "price": 378.4,
        "fee": 12,
        "currency": "HKD",
    },
    {
        "id": 5,
        "account_id": "acct-demo-a",
        "symbol": "NVDA",
        "side": "BUY",
        "trade_date": "2026-05-30",
        "quantity": 60,
        "price": 111.2,
        "fee": 1.2,
        "currency": "USD",
    },
    {
        "id": 6,
        "account_id": "acct-demo-a",
        "symbol": "NVDA",
        "side": "SELL",
        "trade_date": "2026-06-04",
        "quantity": 15,
        "price": 121.8,
        "fee": 1.1,
        "currency": "USD",
    },
    {
        "id": 7,
        "account_id": "acct-demo-b",
        "symbol": "AAPL",
        "side": "BUY",
        "trade_date": "2026-05-28",
        "quantity": 40,
        "price": 198.3,
        "fee": 1.0,
        "currency": "USD",
    },
    {
        "id": 8,
        "account_id": "acct-demo-b",
        "symbol": "600519.SH",
        "side": "BUY",
        "trade_date": "2026-06-03",
        "quantity": 20,
        "price": 1548.0,
        "fee": 5.0,
        "currency": "CNY",
    },
]


ANALYSIS_RUNS = [
    {
        "symbol": "002594.SZ",
        "conclusion": "趋势和催化同时偏强，适合进入观察池并等待成交量确认。",
        "action": "重点观察",
        "confidence": 0.82,
        "input_snapshot_hash": "mock-002594-20260605",
    },
    {
        "symbol": "0700.HK",
        "conclusion": "基本面稳健，短线价格接近压力区，等待回踩更稳。",
        "action": "等待回踩",
        "confidence": 0.78,
        "input_snapshot_hash": "mock-0700-20260605",
    },
    {
        "symbol": "NVDA",
        "conclusion": "基本面和催化强，但估值与波动风险突出，适合持有复核。",
        "action": "持有复核",
        "confidence": 0.80,
        "input_snapshot_hash": "mock-nvda-20260605",
    },
    {
        "symbol": "600519.SH",
        "conclusion": "质量仍强但技术和情绪转弱，持仓需复核核心假设。",
        "action": "减仓观察",
        "confidence": 0.61,
        "input_snapshot_hash": "mock-600519-20260605",
    },
    {
        "symbol": "1810.HK",
        "conclusion": "催化和技术面较强，但未证实信息比例偏高，只保留观察。",
        "action": "重点观察",
        "confidence": 0.76,
        "input_snapshot_hash": "mock-1810-20260605",
    },
    {
        "symbol": "AAPL",
        "conclusion": "质量稳定但短期催化不强，等待财报、产品或回购信息确认。",
        "action": "等待催化",
        "confidence": 0.69,
        "input_snapshot_hash": "mock-aapl-20260605",
    },
]


MEMORIES = [
    {
        "symbol": item["symbol"],
        "memory_version": "mock-v1",
        "reusable_json": {
            "entity": item["symbol"],
            "shared_with_accounts": True,
            "baseline": "公司画像、交易所代码、币种、行业标签和上次分析结论可复用。",
        },
        "must_refresh_json": {
            "market": "行情、K线、成交额、买卖价差必须重新拉取。",
            "news": "新公告和新闻情绪必须重新计算。",
        },
        "invalidated_by": ["new_filing", "large_price_move", "provider_conflict", "model_version_change"],
    }
    for item in SYMBOLS
]
