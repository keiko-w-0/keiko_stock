# 历史数据仓库字段说明

本文说明本地 SQLite 历史数据仓库的主要表、字段含义和 provider 原始字段映射。当前默认数据库路径是 `data/keiko_mock.db`，schema 初始化入口在 `backend/db.py`。

## 设计原则

- 规范列用于筛选、回测、分析和搜索，尽量统一不同 provider 的字段名。
- `raw_json` 保留 provider 原始返回，便于审计、补字段和排查口径差异。
- 同一股票、日期、provider 可以有不同 `adjust` 口径；`daily_bars` 主键是 `symbol, trade_date, provider, adjust`。
- 筛选和回测默认应显式选择一个复权口径，不能把未复权和前复权混在同一次计算里。

## symbols

| 字段 | 含义 |
| --- | --- |
| `symbol` | 标准化证券代码，例如 `600489.SH`、`002594.SZ`、`AAPL`。 |
| `market` | 市场分类，例如 `A`、`HK`、`US`。 |
| `name` | 证券名称。 |
| `currency` | 交易币种，例如 `CNY`、`HKD`、`USD`。 |
| `exchange` | 交易所或市场来源，例如 `SSE`、`SZSE`、`NASDAQ`。 |
| `sector` | 行业/板块大类，当前部分 provider 可能为空或为默认值。 |
| `industry` | 细分行业，当前部分 provider 可能为空或为默认值。 |

## symbol_aliases

| 字段 | 含义 |
| --- | --- |
| `alias` | 可搜索别名，例如中文名、原始代码、标准代码。 |
| `normalized_alias` | 归一化后的别名，用于搜索匹配。 |
| `symbol` | 指向 `symbols.symbol`。 |
| `source` | 别名来源，例如 `baostock`、`seed`。 |
| `updated_at` | 最近写入时间。 |

## daily_bars

| 字段 | 含义 |
| --- | --- |
| `symbol` | 标准化证券代码。 |
| `trade_date` | 交易日，格式 `YYYY-MM-DD`。 |
| `provider` | 数据来源，例如 `baostock-market`、`tushare-market`、`akshare-market`。 |
| `adjust` | 复权口径。`qfq` 为前复权，`hfq` 为后复权，空字符串为未复权或 provider 未标明。 |
| `open` | 开盘价。 |
| `high` | 最高价。 |
| `low` | 最低价。 |
| `close` | 收盘价。 |
| `pre_close` | 前收盘价。 |
| `change_pct` | 涨跌幅百分比，BaoStock 对应 `pctChg`。 |
| `volume` | 成交量。A 股 BaoStock 原始口径为股数。 |
| `amount` | 成交额。A 股 BaoStock 原始口径为人民币元。 |
| `turnover_rate` | 换手率，BaoStock 对应 `turn`。 |
| `pe_ttm` | 滚动市盈率，BaoStock 对应 `peTTM`。 |
| `pb` | 市净率，BaoStock 对应 `pbMRQ`。 |
| `ps_ttm` | 滚动市销率，BaoStock 对应 `psTTM`；Tushare 对应 `daily_basic.ps_ttm`。 |
| `pcf_ncf_ttm` | 滚动市现率，BaoStock 对应 `pcfNcfTTM`。 |
| `is_st` | 是否 ST，BaoStock 对应 `isST`，通常 `1` 表示 ST，`0` 表示非 ST。 |
| `trade_status` | 交易状态，BaoStock 对应 `tradestatus`。当前停牌等非交易行仍会在写入前过滤。 |
| `raw_json` | provider 原始行 JSON 字符串。 |
| `fetched_at` | 本地抓取/写入时间。 |

### BaoStock daily_bars 映射

| BaoStock 字段 | 规范列 | 说明 |
| --- | --- | --- |
| `date` | `trade_date` | 交易日。 |
| `code` | `symbol` | `sh.600489` 会标准化为 `600489.SH`。 |
| `open` | `open` | 开盘价。 |
| `high` | `high` | 最高价。 |
| `low` | `low` | 最低价。 |
| `close` | `close` | 收盘价。 |
| `preclose` | `pre_close` | 前收盘价。 |
| `volume` | `volume` | 成交量。 |
| `amount` | `amount` | 成交额。 |
| `adjustflag` | `adjust` | `1 -> hfq`，`2 -> qfq`，`3 -> 空字符串`。 |
| `turn` | `turnover_rate` | 换手率。 |
| `pctChg` | `change_pct` | 涨跌幅百分比。 |
| `peTTM` | `pe_ttm` | 滚动市盈率。 |
| `pbMRQ` | `pb` | 市净率。 |
| `tradestatus` | `trade_status` | `1` 表示交易；停牌等非交易行当前会被过滤。 |
| `psTTM` | `ps_ttm` | 滚动市销率。 |
| `pcfNcfTTM` | `pcf_ncf_ttm` | 滚动市现率。 |
| `isST` | `is_st` | 是否 ST。 |

## market_snapshots

| 字段 | 含义 |
| --- | --- |
| `id` | 自增主键。 |
| `symbol` | 标准化证券代码。 |
| `provider` | 数据来源。 |
| `as_of` | 数据时间。 |
| `fetched_at` | 本地抓取/写入时间。 |
| `price` | 最新价或最近可用收盘价。 |
| `volume` | 成交量。 |
| `amount` | 成交额。 |
| `turnover_rate` | 换手率。 |
| `spread_bps` | 买卖价差，单位 bp；没有盘口数据时为空。 |
| `raw_json` | provider 原始快照 JSON。 |
| `freshness_status` | 新鲜度标记，例如 `fresh`、`stale`。 |

## financial_metrics_history

| 字段 | 含义 |
| --- | --- |
| `symbol` | 标准化证券代码。 |
| `report_period` | 报告期。 |
| `provider` | 数据来源。 |
| `announce_date` | 披露日期。 |
| `revenue_growth` | 收入增速。 |
| `roe` | 净资产收益率。 |
| `fcf_margin` | 自由现金流率。 |
| `debt_ratio` | 资产负债率。 |
| `gross_margin` | 毛利率。 |
| `net_margin` | 净利率。 |
| `net_profit` | 净利润，BaoStock `profit.netProfit`。 |
| `eps_ttm` | 每股收益 TTM，BaoStock `profit.epsTTM`。 |
| `mb_revenue` | 主营业务收入，BaoStock `profit.MBRevenue`。 |
| `total_share` | 总股本，BaoStock `profit.totalShare`。 |
| `liqa_share` | 流通股本，BaoStock `profit.liqaShare`。 |
| `nr_turn_ratio` | 应收账款周转率，BaoStock `operation.NRTurnRatio`。 |
| `nr_turn_days` | 应收账款周转天数，BaoStock `operation.NRTurnDays`。 |
| `inv_turn_ratio` | 存货周转率，BaoStock `operation.INVTurnRatio`。 |
| `inv_turn_days` | 存货周转天数，BaoStock `operation.INVTurnDays`。 |
| `ca_turn_ratio` | 流动资产周转率，BaoStock `operation.CATurnRatio`。 |
| `asset_turn_ratio` | 总资产周转率，BaoStock `operation.AssetTurnRatio`。 |
| `yoy_equity` | 净资产同比增长率，BaoStock `growth.YOYEquity`。 |
| `yoy_asset` | 总资产同比增长率，BaoStock `growth.YOYAsset`。 |
| `yoy_ni` | 净利润同比增长率，BaoStock `growth.YOYNI`。 |
| `yoy_eps_basic` | 基本每股收益同比增长率，BaoStock `growth.YOYEPSBasic`。 |
| `yoy_pni` | 归母净利润同比增长率，BaoStock `growth.YOYPNI`。 |
| `current_ratio` | 流动比率，BaoStock `balance.currentRatio`。 |
| `quick_ratio` | 速动比率，BaoStock `balance.quickRatio`。 |
| `cash_ratio` | 现金比率，BaoStock `balance.cashRatio`。 |
| `yoy_liability` | 负债同比增长率，BaoStock `balance.YOYLiability`。 |
| `liability_to_asset` | 资产负债率，BaoStock `balance.liabilityToAsset`；同时写入 `debt_ratio`。 |
| `asset_to_equity` | 权益乘数，BaoStock `balance.assetToEquity`。 |
| `ca_to_asset` | 流动资产占比，BaoStock `cash_flow.CAToAsset`。 |
| `tangible_asset_to_asset` | 有形资产占比，BaoStock `cash_flow.tangibleAssetToAsset`。 |
| `ebit_to_interest` | 已获利息倍数，BaoStock `cash_flow.ebitToInterest`。 |
| `operating_cash_flow_to_asset` | 经营现金流/资产，BaoStock `cash_flow.operatingCashFlowToAsset`。 |
| `operating_cash_flow_to_debt` | 经营现金流/负债，BaoStock `cash_flow.operatingCashFlowToDebt`。 |
| `dupont_roe` | 杜邦 ROE，BaoStock `dupont.dupontROE`。 |
| `dupont_asset_to_equity` | 杜邦权益乘数，BaoStock `dupont.dupontAssetStoEquity`。 |
| `dupont_asset_turn` | 杜邦总资产周转率，BaoStock `dupont.dupontAssetTurn`。 |
| `dupont_pnitoni` | 归母净利润/净利润，BaoStock `dupont.dupontPnitoni`。 |
| `dupont_nitogr` | 净利润/营业总收入，BaoStock `dupont.dupontNitogr`。 |
| `dupont_tax_burden` | 税负因子，BaoStock `dupont.dupontTaxBurden`。 |
| `dupont_int_burden` | 利息负担因子，BaoStock `dupont.dupontIntburden`。 |
| `dupont_ebit_to_gr` | EBIT/营业总收入，BaoStock `dupont.dupontEbittogr`。 |
| `raw_json` | provider 原始财务 JSON。 |
| `fetched_at` | 本地抓取/写入时间。 |

BaoStock 季频财务使用 `baostock-financial` provider，按 `query_profit_data`、`query_operation_data`、`query_growth_data`、`query_balance_data`、`query_cash_flow_data`、`query_dupont_data` 聚合成一行。`report_period` 使用季度期末日期，例如 `2026-03-31`；`raw_json.period_key` 保留 `2026Q1` 这种查询 key。

如果某个成熟季度对某只证券没有财务数据，回刷会写入一行空指标占位，`raw_json.status = "no_data"`。这样 ETF/指数或无财报证券不会让全市场回刷无限重复；筛选条件仍然不会命中这些空指标。`no_data` 占位只在 7 天内视为已检查，超过 7 天会重新进入缺口队列，防止公司迟披露导致漏刷。

季度回刷会先按股票和季度检查本地库，只请求缺失或过期 `no_data` 的季度。已有 `ok` 季度不会重复请求 BaoStock；单只股票可用 `python3 scripts/debug_warehouse.py financial-symbol 600519.SH --quarters 12` 查看最近已有季度和缺口列表。

## company_reports_history

| 字段 | 含义 |
| --- | --- |
| `id` | 自增主键。 |
| `symbol` | 标准化证券代码。 |
| `report_period` | 报告期，尽量标准化为 `YYYY-MM-DD`。 |
| `provider` | 数据来源，BaoStock 使用 `baostock-report`。 |
| `report_type` | 报告类型，例如 `performance_express`、`forecast`。 |
| `report_key` | 去重 key，由类型、报告期、发布日期和摘要拼接。 |
| `published_at` | 披露/更新日期。 |
| `title` | 本地生成标题，例如 BaoStock 业绩快报、BaoStock 业绩预告。 |
| `summary` | 关键摘要字段拼接。 |
| `raw_json` | provider 原始公司报告 JSON。 |
| `fetched_at` | 本地抓取/写入时间。 |

BaoStock 公司报告目前写入 `query_performance_express_report` 和 `query_forecast_report` 的结果，不替代 CNINFO/SSE/SZSE 原文公告链接；它用于补充季频业绩快报、业绩预告等结构化报告。

## filings_history

| 字段 | 含义 |
| --- | --- |
| `id` | 自增主键。 |
| `symbol` | 标准化证券代码。 |
| `source` | 公告来源，例如 `cninfo`、`sse`、`szse`。 |
| `published_at` | 公告发布时间。 |
| `title` | 公告标题。 |
| `url` | 原文链接。 |
| `category` | 公告分类。 |
| `source_tier` | 来源等级。 |
| `raw_json` | provider 原始公告 JSON。 |
| `fetched_at` | 本地抓取/写入时间。 |

## ingestion_runs

| 字段 | 含义 |
| --- | --- |
| `id` | 自增任务 ID。 |
| `provider` | 任务来源，例如 `baostock`、`akshare`。 |
| `scope` | 任务范围，例如 `a-share-history-background:universe`。 |
| `status` | `running`、`ok`、`partial`、`failed`、`interrupted`。 |
| `started_at` | 开始时间。 |
| `finished_at` | 结束时间。 |
| `requested_symbols` | 请求回刷的证券列表 JSON。为空表示按全市场缺口回刷。 |
| `updated_symbols` | 已写入数据的证券列表 JSON。 |
| `counts_json` | 进度计数 JSON，例如 `daily_bars`、`batches`、`remaining_candidates`、`last_progress_at`。 |
| `errors_json` | 错误列表 JSON。 |

## 调试 raw_json

表格输出会截断长字段，所以不要直接把默认 `sql` 表格输出 pipe 给 `json.tool`。使用 `--raw`：

```bash
python3 scripts/debug_warehouse.py --raw sql "select raw_json from daily_bars where symbol = '600489.SH' order by trade_date desc limit 1" | python3 -m json.tool
```

验证 JSON 是否有效：

```bash
python3 scripts/debug_warehouse.py sql "select symbol, trade_date, provider, adjust, json_valid(raw_json) raw_valid from daily_bars where symbol = '600489.SH' order by trade_date desc limit 3"
```


去重
```bash
# 只扫描，不删
python3 scripts/dedupe_warehouse.py --scan-only

# 全量去重（公告标题 + 快照 + daily_bars 冗余未复权）
python3 scripts/dedupe_warehouse.py

# 分项控制
python3 scripts/dedupe_warehouse.py --no-filings
python3 scripts/dedupe_warehouse.py --no-daily-bars

# debug 工具
python3 scripts/debug_warehouse.py dedupe-scan
```



# agent写入明细查询
每轮 30 分钟 agent 写入 ingestion_runs（provider=community-sentiment-agent），完整用量在 counts_json。

Agent 日志示例：

community-cycle run_id=42 ... llm_requests=3 llm_items=24 cache_hits=18 uncached=6 accounting_ok=

```bash
python3 scripts/debug_warehouse.py sql "
select id, status, started_at,
       json_extract(counts_json,'$.cache_hits') cache_hits,
       json_extract(counts_json,'$.llm_requests') llm_requests,
       json_extract(counts_json,'$.llm_request_items') llm_items
from ingestion_runs
where provider='community-sentiment-agent'
order by id desc limit 10"
```