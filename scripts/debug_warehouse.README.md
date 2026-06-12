# debug_warehouse 后台诊断说明

`scripts/debug_warehouse.py` 是本地 SQLite 历史数据仓库的只读诊断脚本，用来排查 BaoStock/AKShare/Tushare/Finnhub 写入情况、A 股宇宙覆盖率、K 线缺口、PE/PB 覆盖和后台 ingestion 任务状态。

字段字典和 provider 原始字段映射见 `docs/warehouse-schema.md`。

## 前置条件

在项目根目录执行：

```bash
python3 -m pip install -r requirements.txt
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8104
```

脚本默认读取 `backend.db.DB_PATH`，当前默认数据库是 `data/keiko_mock.db`。如需指定其它库：

```bash
python3 scripts/debug_warehouse.py --db /path/to/keiko_mock.db summary
```

## 常用命令

```bash
python3 scripts/debug_warehouse.py summary
python3 scripts/debug_warehouse.py providers
python3 scripts/debug_warehouse.py coverage
python3 scripts/debug_warehouse.py missing-bars --limit 50
python3 scripts/debug_warehouse.py pe
python3 scripts/debug_warehouse.py daily-symbol 600519.SH
python3 scripts/debug_warehouse.py financials
python3 scripts/debug_warehouse.py financial-symbol 600519.SH --quarters 8
python3 scripts/debug_warehouse.py symbol 中金黄金 --limit 20
python3 scripts/debug_warehouse.py runs --limit 20
```

输出 JSON：

```bash
python3 scripts/debug_warehouse.py --json coverage
```

执行只读 SQL：

```bash
python3 scripts/debug_warehouse.py sql "select provider, count(*) rows from daily_bars group by provider"
```

单列 raw 输出：

```bash
python3 scripts/debug_warehouse.py --raw sql "select raw_json from daily_bars where symbol = '600489.SH' order by trade_date desc limit 1" | python3 -m json.tool
```

`sql` 子命令只允许 `SELECT`、`WITH`、`PRAGMA`，用于 debug，不用于修改数据库。

## 看 BaoStock 后台回刷进度

启动后台回刷：

```bash
curl -sS http://127.0.0.1:8104/api/data/refresh \
  -H 'Content-Type: application/json' \
  -d '{"provider":"baostock","scope":"baostock","account_id":"acct-admin","refresh_universe":true}'
```

返回里会有 `run_id`。查询任务：

```bash
curl -sS http://127.0.0.1:8104/api/data/jobs/<run_id>
python3 scripts/debug_warehouse.py runs --limit 5
```

`/api/data/jobs/<run_id>` 默认只返回 `requested_symbol_count`、`updated_symbol_count` 和样本，避免后台任务跑久后轮询 JSON 过大。需要完整 symbol 列表时再显式请求：

```bash
curl -sS "http://127.0.0.1:8104/api/data/jobs/<run_id>?include_symbols=true&symbol_limit=500"
```

也可以绕过前端/接口，直接跑后台脚本：

```bash
python3 scripts/run_baostock_backfill.py --days 260 --batch-size 30
python3 scripts/run_baostock_backfill.py --days 260 --batch-size 30 --json
```

脚本会复用同一套 `ingestion_runs` 状态和 SQLite 历史仓库。空参数表示按数据库缺口继续全市场回刷；传入股票代码或名称时只回刷指定标的。

## 看 BaoStock 季频财务/公司报告回刷

季度财务源是 `cn-baostock-financial`，provider 为 `baostock-financial`。它使用 BaoStock 免费接口补：

- `financial_metrics_history`：季频指标，来自 `query_profit_data`、`query_operation_data`、`query_growth_data`、`query_balance_data`、`query_cash_flow_data`、`query_dupont_data`。
- `company_reports_history`：季频公司报告，来自 `query_performance_express_report` 和 `query_forecast_report`。

启动季度回刷：

```bash
python3 scripts/run_baostock_financial_backfill.py --quarters 12 --batch-size 10
```

先小批验证：

```bash
python3 scripts/run_baostock_financial_backfill.py 600519.SH --quarters 4 --batch-size 1 --max-batches 1 --no-universe-refresh --json
```

也可以走后端接口：

```bash
curl -sS http://127.0.0.1:8104/api/data/refresh \
  -H 'Content-Type: application/json' \
  -d '{"provider":"baostock-financial","scope":"quarterly-financials","account_id":"acct-admin","refresh_universe":true}'
```

诊断覆盖：

```bash
python3 scripts/debug_warehouse.py financials
python3 scripts/debug_warehouse.py financial-symbol 600519.SH --quarters 12
python3 scripts/debug_warehouse.py sql "select provider, count(*) rows, count(distinct symbol) symbols, max(report_period) latest from financial_metrics_history group by provider"
python3 scripts/debug_warehouse.py sql "select provider, report_type, count(*) rows, max(report_period) latest from company_reports_history group by provider, report_type"
```

季度候选使用成熟财报期，不会提前刷当前未披露季度。例如 2026-06-07 会从 `2026Q1` / `2026-03-31` 开始，不会写入未结束的 `2026Q2`。ETF/指数或无财报证券会写空指标占位，`raw_json.status = "no_data"`，避免全市场任务无限重复。

季频财务和公司报告查询在子进程中执行。BaoStock SDK 如果卡在网络接收，父进程会按批次规模超时并终止子进程，run 会正常收口为 `partial` 或 `failed`，后续再跑会按缺口继续。

调试时可以临时缩短超时：

```bash
KEIKO_BAOSTOCK_FINANCIAL_BATCH_TIMEOUT_SECONDS=8 \
KEIKO_BAOSTOCK_REPORT_BATCH_TIMEOUT_SECONDS=5 \
python3 scripts/run_baostock_financial_backfill.py 600519.SH --quarters 1 --batch-size 1 --max-batches 1 --no-universe-refresh --json
```

回刷前后可用 `financial-symbol` 检查单只股票：

- `warehouse_status = missing`：本地库没有该季度，需要回刷。
- `warehouse_status = no_data`：本地已经检查过，但 BaoStock 没有该季度数据；7 天后会自动重新进入缺口，防止迟披露漏掉。
- `warehouse_status = ok`：本地已有该季度指标，不会重复请求 BaoStock。
- `latest_ok_period`：该股票本地最近一个有实际指标的季度，用来确认单股分析应该读到的最近已有季度。

本机已提供 macOS LaunchAgent 配置：

```bash
launchctl print gui/501/com.keiko.baostock-nightly
launchctl print gui/501/com.keiko.baostock-financial-nightly
launchctl print gui/501/com.keiko.a-share-filings-nightly
launchctl print gui/501/com.keiko.ingestion-watchdog
```

已安装的 plist 位于 `/Users/wangwenhui/Library/LaunchAgents/com.keiko.baostock-nightly.plist`，项目内源文件是 `scripts/com.keiko.baostock-nightly.plist`。任务每天 00:00 运行 `scripts/run_baostock_backfill.py --days 260 --batch-size 30 --json`，日志写入：

- `logs/baostock-nightly.log`
- `logs/baostock-nightly.err.log`

季度任务 plist 位于 `/Users/wangwenhui/Library/LaunchAgents/com.keiko.baostock-financial-nightly.plist`，项目内源文件是 `scripts/com.keiko.baostock-financial-nightly.plist`。任务每天 02:30 运行 `scripts/run_baostock_financial_backfill.py --quarters 4 --batch-size 3 --json`，日志写入：

- `logs/baostock-financial-nightly.log`
- `logs/baostock-financial-nightly.err.log`

公告任务 plist 位于 `/Users/wangwenhui/Library/LaunchAgents/com.keiko.a-share-filings-nightly.plist`，项目内源文件是 `scripts/com.keiko.a-share-filings-nightly.plist`。任务每天 20:30 运行 `scripts/run_a_share_filings_backfill.py --source all --days 180 --batch-size 20 --json`，日志写入：

- `logs/a-share-filings-nightly.log`
- `logs/a-share-filings-nightly.err.log`

watchdog plist 位于 `/Users/wangwenhui/Library/LaunchAgents/com.keiko.ingestion-watchdog.plist`，项目内源文件是 `scripts/com.keiko.ingestion-watchdog.plist`。任务每 15 分钟检查一次 stale/incomplete 回刷，并且每轮最多启动一个续跑任务，日志写入：

- `logs/ingestion-watchdog.log`
- `logs/ingestion-watchdog.err.log`

任务进度写在 `ingestion_runs.counts_json`：

- `symbols`：本次 `query_all_stock` 写入的证券数量。
- `daily_bars`：本任务累计写入的 K 线行数。
- `market_snapshots`：本任务累计写入的最新行情快照数。
- `batches`：已完成批次数。
- `batch_size`：每批证券数，当前默认 30。
- `remaining_candidates`：仍需回刷的候选证券数，逻辑是 BaoStock 行数少于 120 或最新日线过期。
- `last_progress_at`：最近一次进度心跳。新任务启动前会把超过心跳窗口仍停在 `running` 的 BaoStock 任务标记为 `interrupted`，然后按缺口继续。

BaoStock 历史 K 线查询按单只证券自动重试：发生 `网络接收错误`、连接断开、socket 超时或临时登录失败时，会等待后重新登录并重试。重试后仍失败的证券会写进 `errors_json`，不会阻断其它证券和已成功批次。

## 关键指标解释

`coverage`：

- `a_universe`：本地 A 股/ETF/指数宇宙总量，来自 `symbols`。
- `with_baostock_bars`：已有 BaoStock K 线的证券数。
- `without_baostock_bars`：完全没有 BaoStock K 线的证券数。
- `target_end`：如果现在启动一个 BaoStock 日线任务，本轮要追到的目标交易日。
- `with_latest_target`：本地 BaoStock 最新日线已经达到 `target_end` 的证券数。
- `before_latest_target_or_none`：没有达到 `target_end` 或完全没有 BaoStock K 线的证券数。
- `with_120plus_bars`：已有至少 120 根 BaoStock 日线的证券数。
- `under_120_bars`：少于 120 根 BaoStock 日线的证券数；它包含新股和完全无 K 线标的，不等于“本轮失败数”。
- `planned_backfill_symbols`：按当前目标日期和缺口算法，下一次任务会选中的证券数。
- `latest_run_*`：最近一次 BaoStock 日线 run 的状态、写入数、批次、剩余候选和心跳。

判断一次回刷是否成功，优先看 `latest_run_status = ok` 且 `latest_run_remaining = 0`。如果 `latest_run_status = partial` 且 `latest_run_daily_bars = 0`，说明任务跑过但没有有效写入，不能算成功。

`daily-symbol`：

- 展示单只股票 BaoStock 日线的本地覆盖、目标日期和下一次实际请求区间。
- 如果本地最新是 `2026-06-05`，目标是 `2026-06-08`，则请求区间会是 `2026-06-06` 到 `2026-06-08`，不会重复请求 `2026-06-05` 之前的数据。
- 对完全没有日线的股票，请求区间使用初始化窗口，例如 `target_start` 到 `target_end`。
- 如果一只股票既缺最新几天、又缺旧历史，`request_ranges` 会显示多个区间，例如 `2026-06-06..2026-06-08,2025-09-21..2026-02-02`。这是为了不重复请求中间已经存在的数据。

`providers`：

- 按 `daily_bars.provider` 聚合行数、证券数、日期范围、正 PE/PB 行数。
- BaoStock 的 PE/PB/PS/PCF 来自 `query_history_k_data_plus` 字段 `peTTM`、`pbMRQ`、`psTTM`、`pcfNcfTTM`；`is_st` 来自 `isST`。
- 指数、债券、ETF 常见 `pe_ttm=0` 或 `pb=0`，这是源数据口径，不代表股票估值缺失。

`financials`：

- 按 `financial_metrics_history.provider` 聚合季频指标行数、证券数、报告期范围和关键字段覆盖。
- BaoStock 指标 provider 是 `baostock-financial`；业绩快报/预告在 `company_reports_history`，不计入 `financials` 输出。
- `financial-symbol <股票>` 会按当前成熟季度列表逐期显示是否缺口，并复用后台回刷的同一套日期检查逻辑。

`symbol`：

- 按股票代码、名称或别名查询单只证券的 `daily_bars`。
- 输出包含 `adjust`。同一 `symbol + trade_date + provider` 可能有未复权和 `qfq` 两种口径，不是重复脏数据；主键是 `symbol, trade_date, provider, adjust`。

## 当前实现边界

- BaoStock 前端触发仍使用进程内 FastAPI `BackgroundTasks`；`scripts/run_baostock_backfill.py` 可作为后台/定时任务入口。后端进程关闭后，正在跑的进程内任务会停止；下次再次触发会按缺口继续。
- 每批回刷后都会提交 SQLite，所以可以边跑边用脚本查差数。
- BaoStock 网络错误会写进 `errors_json`，不会阻断已成功批次。
- 当前筛选、回测和搜索优先使用历史数据仓库，仍会根据 provider 时效性和优先级选择最新可用数据。
