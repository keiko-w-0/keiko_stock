# 聚宝盆 Handoff

更新时间：2026-06-07

这份文档用于换电脑或开启新 Codex 会话时快速接手。新会话优先阅读：

1. `README.md`
2. `scripts/debug_warehouse.README.md`
3. `docs/warehouse-schema.md`
4. `docs/engineering-todo.md`
5. `docs/research-report.md`
6. 本文件

## 当前产品状态

当前已从纯 mock 进入“本地 SQLite 历史数据仓库 + 真实/缓存数据源”阶段；仍不调用真实 LLM，不直接给交易建议。已接入账户级数据源配置、Finnhub 美股、Tushare A 股、AKShare 探索、BaoStock 历史日线/代码宇宙回刷、BaoStock 季频财务/公司报告回刷、官方公告测试入口、数据库筛选和数据库回测。当前优先开发网页版；macOS 和 iPhoneOS 打包暂缓。

已完成：

- 静态前端：`index.html`、`styles.css`、`app.js`
- FastAPI 后端：`backend/app.py`
- SQLite schema 和种子数据：`backend/db.py`、`backend/seed_data.py`
- Web 版命名已改为“聚宝盆”；左侧“股票池过滤”已改为“筛选股票”。
- 左侧导览已改成独立 tab：切换后只显示当前 tab 内容，不再连续滚动串在一起。
- 设置页已加入数据源配置：按 A/HK/US 市场配置行情、财务、公告、新闻情绪源，未启用或未配置成功的数据源不会进入后续分析。
- 已新增 `acct-admin` 管理账户；数据源开关和 API key 按账户隔离保存，当前 Finnhub key 已写入本地 admin 账户。
- Finnhub 已可刷新 AAPL/NVDA 等美股的行情快照、基本面快照和公司新闻，并写入共享缓存表。
- Tushare 已可刷新 A 股行情/财务指标，并在搜索、分析和估值中优先使用新鲜缓存。
- BaoStock 已接入 `query_all_stock` 和 `query_history_k_data_plus`；A 股/ETF/指数代码宇宙写入 `symbols`/`symbol_aliases`，日线写入 `daily_bars`，PE/PB 来自 `peTTM`/`pbMRQ`。
- BaoStock 季频财务已接入 `query_profit_data`、`query_operation_data`、`query_growth_data`、`query_balance_data`、`query_cash_flow_data`、`query_dupont_data`；写入 `financial_metrics_history`，报告期用期末日期。
- BaoStock 公司报告已接入 `query_performance_express_report` 和 `query_forecast_report`；写入 `company_reports_history`，用于业绩快报/业绩预告等结构化补充。
- BaoStock 全量回刷已改为后台长任务：`POST /api/data/refresh` 返回 `run_id`，`GET /api/data/jobs/{run_id}` 查询进度；前端设置页会轮询显示批次、日线和剩余候选。BaoStock 网络接收错误会按单只证券等待、重新登录并重试；旧 `running` 任务超过心跳窗口会标记为 `interrupted`，新任务按缺口继续。
- BaoStock 季频财务/公司报告批次增加子进程超时保护；SDK 卡住时会终止子进程并让 run 收口，不会无限保持 `running`。
- BaoStock 后台/定时入口已新增：`scripts/run_baostock_backfill.py --days 260 --batch-size 30`，不依赖浏览器或前端。
- BaoStock 季频财务后台入口已新增：`scripts/run_baostock_financial_backfill.py --quarters 12 --batch-size 10`。接口入口是 `/api/data/refresh` body `{"provider":"baostock-financial","scope":"quarterly-financials"}`。
- A 股公告缺口后台入口已新增：`scripts/run_a_share_filings_backfill.py --source all --days 180 --batch-size 20`。接口入口是 `/api/data/refresh` body `{"provider":"cninfo_sse_szse","scope":"cninfo_sse_szse","refresh_universe":true}`，默认覆盖 CNINFO + 对应交易所公告。
- 本机已安装 LaunchAgent `com.keiko.baostock-nightly`，每天 00:00 运行 BaoStock 日线回刷脚本；项目内源文件是 `scripts/com.keiko.baostock-nightly.plist`，日志在 `logs/baostock-nightly.log`。
- 本机已安装 LaunchAgent `com.keiko.baostock-financial-nightly`，每天 02:30 运行 BaoStock 季频财务/公司报告回刷脚本；项目内源文件是 `scripts/com.keiko.baostock-financial-nightly.plist`，日志在 `logs/baostock-financial-nightly.log`。
- 本机已安装 LaunchAgent `com.keiko.a-share-filings-nightly`，每天 20:30 运行 A 股公告缺口回刷脚本；项目内源文件是 `scripts/com.keiko.a-share-filings-nightly.plist`，日志在 `logs/a-share-filings-nightly.log`。
- 历史数据仓库诊断脚本已新增：`scripts/debug_warehouse.py`，单独说明见 `scripts/debug_warehouse.README.md`。
- 筛选股票已改为数据库筛选：未勾选时不再默认启用过滤；自然语言 `PE<10` 等作为独立 SQL 条件，不会自动勾选“PE分位 <= 70”。
- 回测平台已优先使用 `daily_bars`；数据库数据不足时才退回研究 mock。
- 回测平台已加入左侧导览：优先使用数据库历史日线，支持策略模板、市场、区间、持仓数、调仓频率、手续费和滑点参数。
- Phase 1E 已完成起点：新增 `providers/` provider、共享快照表、数据源配置表、`/api/stocks/search`、`/api/screeners/run`、`/api/memory/stocks/{symbol}`、`/api/data-sources`、`/api/backtests/run`。
- 多账户 mock：账户 A/B 可切换；股票分析、异动分析、记忆共享；关注列表、交易流水、持仓按账户隔离。
- 持仓收益：支持 Buy/Sell 流水、持仓数量、成本、盈利金额、收益率、刷新 mock 最新价。
- 单股分析浮层：点击“查看分析”打开，左上角关闭，含低置信原因、claim 详情、因子详情、记忆、最多 3 轮反思。
- 异动分析：左侧入口，可从今日观察 + 关注列表 + 持仓列表选股，也支持自然语言问大盘/板块异动。
- iPhone/PWA mock：manifest、service worker、mobile meta、底部导航、安全区适配。
- Mac mock 包：已做 Universal binary，最低 macOS 12.0。

## 本地启动

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

Mac 本机预览：

```bash
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8100
```

访问：

```text
http://localhost:8100
```

iPhone 同 Wi-Fi 预览：

```bash
python3 -B -m uvicorn backend.app:app --host 0.0.0.0 --port 8101
```

手机访问：

```text
http://<Mac 局域网 IP>:8101
```

如果端口被占用，换到 `8102`、`8103` 等后续端口即可。iPhone 不能访问 Mac 的 `localhost`。

## 关键源码

- `app.js`：当前主要前端交互逻辑和 mock fallback 数据。
- `styles.css`：桌面、浮层、移动端和 iPhone/PWA 样式。
- `index.html`：单页应用入口。
- `backend/app.py`：FastAPI 路由入口。
- `backend/db.py`：SQLite schema 初始化。
- `backend/seed_data.py`：mock 种子数据。
- `backend/accounts.py`：账户私有关注和交易流水。
- `backend/portfolio.py`：账户级持仓与收益计算。
- `backend/analysis.py`：共享单股分析、共享异动分析和缓存统计。
- `backend/data_quality.py`：mock 数据健康检查与刷新。
- `backend/history.py`：历史数据仓库、BaoStock/AKShare/Tushare fallback、BaoStock 后台回刷、数据库筛选、回测日线读取。
- `backend/providers/baostock_provider.py`：BaoStock 适配器。
- `scripts/run_baostock_backfill.py`：BaoStock 后台/定时回刷脚本入口，复用 `ingestion_runs` 状态。
- `scripts/run_baostock_financial_backfill.py`：BaoStock 季频财务指标和公司报告后台回刷脚本入口。
- `scripts/run_a_share_filings_backfill.py`：A 股公告/披露缺口后台回刷脚本入口，复用 `ingestion_runs` 和 `filing_refresh_state`。
- `scripts/com.keiko.baostock-nightly.plist`：macOS LaunchAgent 源配置，每天 00:00 执行 BaoStock 日线回刷。
- `scripts/com.keiko.baostock-financial-nightly.plist`：macOS LaunchAgent 源配置，每天 02:30 执行 BaoStock 季频财务/公司报告回刷。
- `scripts/com.keiko.a-share-filings-nightly.plist`：macOS LaunchAgent 源配置，每天 20:30 执行 A 股公告缺口回刷。
- `scripts/debug_warehouse.py`：只读诊断 SQLite 历史仓库和后台 ingestion 任务。
- `scripts/debug_warehouse.README.md`：debug 脚本和 BaoStock 后台任务说明。
- `docs/warehouse-schema.md`：历史数据仓库字段字典和 provider 原始字段映射。
- `packaging/mac/KeikoStockAI.m`：会启动本地 FastAPI 的 Mac WKWebView 壳。
- `packaging/mac/KeikoStockAIOffline.m`：离线 mock 演示 Mac WKWebView 壳。
- `scripts/package_mac_app.sh`：生成本地后端版 Mac mock 包。
- `scripts/package_mac_offline_app.sh`：生成离线 Universal Mac mock 包。
- `scripts/package_ios_mock_source.sh`：生成 iPhone SwiftUI/WKWebView mock 源码包。

## 生成物和分发状态

推荐发给别人试用：

- `dist/macos-offline/KeikoStockAI-mac-mock-offline-universal.zip`

这个包不依赖对方电脑安装 Python/uvicorn，适合 mock 演示和团队内测。

开发调试包：

- `dist/macos/KeikoStockAI-mac-mock.zip`

这个包会启动本地 FastAPI 后端，更适合本机调试；发给别人时可能受 Python 环境影响。

iPhone 源码包：

- `dist/iphone/KeikoStockAI-iPhone-Mock-Source.zip`

当前机器只有 Command Line Tools，没有完整 Xcode/iOS SDK/签名环境，所以没有直接生成可安装 `.ipa`。

注意：`dist/` 是生成物。源文件变化后要重新运行对应 `scripts/package_*` 脚本再交付 zip。

## 正式发布边界

现在的 zip 是 ad-hoc 签名，不能当正式上架包。

Mac 官网下载正式版需要：

- Developer ID Application 证书签名
- Hardened Runtime
- notarization
- stapling
- `.dmg` 或 `.pkg`
- Gatekeeper 首次打开验证

Mac App Store 需要：

- App Sandbox
- 正式 Bundle ID 和 entitlement
- App Store Connect
- 隐私标签、截图、审核说明、测试账号
- App Review

iPhone 上架需要：

- 完整 Xcode
- Apple Developer Team
- Bundle ID、证书和 provisioning profile
- Archive 上传 App Store Connect
- TestFlight
- App Review

正式 iPhone 版不能依赖用户 Mac 的本地 Python/FastAPI 服务，应改成原生壳或 WebView 调云端 API。

## 下一阶段建议

下一阶段继续补 Web 版真实数据闭环：

1. 将 BaoStock 后台回刷从 FastAPI 进程内 `BackgroundTasks` 升级为可恢复队列或独立 worker，支持暂停/恢复/失败重试。
2. 梳理 `daily_bars` 复权口径：筛选/回测默认使用一种口径，避免未复权和 `qfq` 同时参与同一结果。
3. 把大批量历史数据迁到 DuckDB/Parquet 或至少增加索引/分页，避免 SQLite 查询和 UI 一次性返回过大。
4. 为股票搜索、筛选、分析、回测补自动化测试，重点覆盖新股票输入、自然语言过滤、BaoStock 缺口、PE/PB 查询。
5. 让单股分析、异动分析进一步读取后端 claims/factor_runs，而不是只用前端本地 fallback。
6. 继续把当前 `app.js` 中的大块 fallback 数据迁到后端 seed/provider，前端只调用 API。
7. 再考虑把静态前端迁移到 React + TypeScript + Vite。

不要优先做：

- 不要直接接真实交易或券商。
- 不要让 AI 直接给“必买/必卖”结论。
- 不要把账户私有持仓写入共享分析缓存。
- 不要把当前 ad-hoc zip 当正式发布物。

## 记忆和多账户原则

共享资产：

- 股票主数据
- 行情/财务/新闻快照
- claim 和因子计算
- 单股分析
- 异动分析
- 股票分析记忆

账户私有资产：

- 关注列表
- Buy/Sell 交易流水
- 持仓和收益缓存
- 用户偏好、风险等级、提醒设置

分析如果引用了持仓，必须拆成两段：

- 共享分析：不包含任何用户私有持仓。
- 账户个性化建议：只对当前账户可见。

## 已知注意点

- `packaging/mac/KeikoStockAI.swift` 是早期尝试，当前实际打包脚本使用 Objective-C 文件。
- Mac mock 包目前最低系统版本设置为 macOS 12.0，架构包含 `arm64` 和 `x86_64`。
- 发送给朋友时优先用离线包，不要优先发后端包。
- Codex 新会话如果看到 `dist/` 有改动，先判断是否是生成物；源码应以根目录、`backend/`、`packaging/`、`ios/`、`scripts/` 为准。
- 每次改动后，用户希望启动网页预览。
- BaoStock 前端触发仍是进程内任务；如果 uvicorn 进程停止，任务会停止。再次触发 BaoStock 刷新或运行 `scripts/run_baostock_backfill.py` / `scripts/run_baostock_financial_backfill.py` 会按缺口继续补。午夜调度优先使用脚本入口。
- BaoStock 季频任务按财报披露截止日选择成熟季度。例如 2026-06-07 从 2026Q1 开始，不提前写 2026Q2。ETF/指数等无季报标的会写 `raw_json.status = "no_data"` 占位，避免全市场候选无限重复。
- BaoStock 季频任务现在按 `symbol + report_period` 做缺口计划，只请求本地缺失或超过 7 天的 `no_data` 季度；已有 `ok` 季度不会重复请求。单股检查用 `python3 scripts/debug_warehouse.py financial-symbol 600519.SH --quarters 12`。
- `daily_bars` 主键包含 `adjust`；同一股票同一天出现未复权和 `qfq` 两行不是重复脏数据。查询时要显式考虑复权口径。
- 调试数据仓库优先用 `python3 scripts/debug_warehouse.py coverage/providers/runs`，不要直接猜测写库结果。
