# 聚宝盆工程 TODO

更新时间：2026-06-13

目标：把当前本地网页版打磨成数据库驱动的股票研究软件，支持多账户、真实/缓存数据源配置、历史数据仓库、共享分析记忆、独立持仓/关注、**社区情绪（股吧+雪球+GLM）**；macOS 和 iPhoneOS 打包暂缓。

换电脑或开启新 Codex 会话时，先读 `docs/handoff.md` 和 **`docs/sentiment.README.md`**，再按本 TODO 继续推进。

## 0. 当前 Demo 已验证

- 筛选股票：显式规则 + 自然语言规则，左侧导览切换后各 tab 独立显示。
- 数据健康检查：数据新鲜度、证据可信、刷新入口。
- 今日观察：A 股、港股、美股候选卡片。
- 关注列表：独立页面，卡片展示，支持查看单股分析。
- 持仓列表：独立页面，支持 Buy/Sell、收益率、盈利金额、刷新股价、折叠流水、K 线 B/S 标记。
- 单股分析：较轻量浮动界面，左上关闭按钮，含结论、低置信原因、claim 详情、因子详情、记忆、最多 3 轮反思。
- 异动分析：股票池来自今日观察 + 关注列表 + 持仓列表；支持股票异动报告和自然语言大盘/板块异动解释。
- Mock 后端：FastAPI + SQLite 已建立本地种子库，支持 `/api/bootstrap`、账户关注、账户交易、共享单股分析、共享异动分析。
- 多账户边界：账户 A/B 可切换；股票分析、异动分析、记忆共享；关注列表和交易流水按账户隔离。
- Phase 1B 模块化：后端已拆分为 `db/accounts/analysis/portfolio/data_quality/schemas`。
- 后端持仓计算：`/api/accounts/{account_id}/portfolio` 已返回持仓、盈亏、收益率、币种汇总，并写入 `account_positions_cache`。
- 后端刷新盈利：`/api/data/refresh` 支持账户级 portfolio mock 价格刷新和重算。
- Phase 1C iPhone 原型：已加入 PWA manifest、service worker、mobile web app meta、手机底部导航和 iOS 安全区适配。
- Phase 1C 局域网预览：可用 `--host 0.0.0.0 --port 8101` 让同一 Wi-Fi 的 iPhone 访问。
- Phase 1D 打包：已生成 Mac 后端 mock `.app`、Mac 离线 Universal mock `.app`、Mac zip、iPhone SwiftUI/WKWebView mock 源码包和 iPhone zip。
- Phase 1D 兼容性：Mac mock 包已设置最低 macOS 12.0，并同时包含 Apple Silicon 与 Intel 架构。
- Phase 1E Web：已加入 mock provider 抽象、共享快照表、`/api/stocks/search`、`/api/screeners/run`、`/api/memory/stocks/{symbol}` 和数据源设置 API。
- Phase 1E Web：左侧新增“设置”，可按 A/HK/US 市场勾选行情、财务、公告、新闻情绪数据源并输入 mock API key；未生效的数据源不会进入后续 mock 分析。
- Phase 1E Web：已新增 `acct-admin` 管理账户、账户级数据源开关/key 隔离，以及 Finnhub 美股行情、基本面、公司新闻刷新。
- Phase 1E Web：左侧新增“回测平台”，支持 mock 研究回测，输出收益曲线、最大回撤、胜率、换手、调仓记录、归因和研究限制。
- Phase 1F Web：已接入 Tushare A 股行情/财务缓存、Alpha Vantage 数据探索、官方公告数据源测试和公告标题链接。
- Phase 1G Web：已接入 SQLite 历史数据仓库，新增 `symbol_aliases`、`daily_bars`、`financial_metrics_history`、`filings_history`、`ingestion_runs`。
- Phase 1G Web：BaoStock 已接入 `query_all_stock` 和 `query_history_k_data_plus`，支持 A 股/ETF/指数代码宇宙、日线、成交额、换手率、`peTTM`、`pbMRQ`。
- Phase 1G Web：BaoStock 已接入季频财务和公司报告回刷；`financial_metrics_history` 支持利润、营运、成长、偿债、现金流、杜邦指标，`company_reports_history` 支持业绩快报/业绩预告。
- Phase 1G Web：BaoStock 全量回刷已改为后台长任务，设置页点击刷新后返回 `run_id` 并轮询 `/api/data/jobs/{run_id}`。
- Phase 1G Web：BaoStock 历史回刷已加入单只证券等待重试、重新登录、批次心跳和卡住任务 `interrupted` 释放；新增 `scripts/run_baostock_backfill.py` 作为后台/定时入口。
- Phase 1G Web：BaoStock 季频财务/公司报告批次已加入子进程超时保护，并新增 `scripts/test_warehouse_guards.py` 覆盖任务防回写、增量区间、季度 no_data 重试和超时收口。
- Phase 1G Ops：本机已安装 LaunchAgent `com.keiko.baostock-nightly`，每天 00:00 回刷 BaoStock 最近日线，日志写入 `logs/baostock-nightly.*.log`。
- Phase 1G Ops：本机已安装 LaunchAgent `com.keiko.baostock-financial-nightly`，每天 02:30 回刷 BaoStock 季频财务/公司报告，日志写入 `logs/baostock-financial-nightly.*.log`。
- Phase 1G Web：筛选股票已改为数据库查询；自然语言 `PE<10` 等作为独立 SQL 条件，不再自动勾选复选框。
- Phase 1G Web：回测平台优先使用 `daily_bars`，数据不足时才退回研究 mock。
- Phase 1G Debug：已新增 `scripts/debug_warehouse.py` 和 `scripts/debug_warehouse.README.md`，用于 SQL 差数、provider 覆盖、PE/PB、缺口和任务状态。
- Phase 1H Sentiment（2026-06-13）：社区情绪面已接入 GLM/DeepSeek；股吧 + 雪球双源爬虫；雪球 quote 补实时价；DrissionPage 过 WAF 抓雪球评论；自选股优先刷新；详情页「刷新」与 A 股红涨绿跌 UI。详见 `docs/sentiment.README.md`。

## 1. 技术架构 TODO

### 前端

- [ ] 把当前 `index.html` / `styles.css` / `app.js` 迁移到 React + TypeScript + Vite。
- [x] 当前静态前端加入 PWA/iPhone app shell。
- [ ] 拆组件：`StockCard`、`SingleStockDrawer`、`PortfolioTable`、`AnomalyReport`、`DataHealthPanel`、`MemoryPanel`。
- [ ] 建立前端状态层：用户会话、当前账户、筛选股票、关注列表、持仓、分析报告、异动报告、数据源设置。
- [ ] 所有按钮和表单增加 loading、error、empty、stale 状态。
- [x] BaoStock 数据源刷新按钮改成后台任务并显示轮询进度。
- [x] BaoStock 季频财务/公司报告数据源刷新按钮改成后台任务并显示季度指标/报告进度。
- [x] BaoStock 回刷加入网络错误自动等待/重试和心跳失效释放。
- [ ] 为关键交互写 Playwright 测试：查看分析、关注/取消关注、录入 Buy/Sell、刷新股价、生成异动报告。
- [ ] 生成正式 iOS app icon PNG/icon set，替换当前 SVG 原型图标。

### 后端

- [x] 使用 FastAPI 做本地 API 服务。
- [ ] 建立模块：
  - `providers/`：行情、财务、公告、新闻、情绪供应商适配器。当前已有 mock、Tushare、AKShare、Alpha Vantage、Finnhub、BaoStock、**community（股吧）、xueqiu（雪球 quote/评论）**。
  - `ingestion/`：拉取、去重、标准化、缓存。当前 BaoStock 仍在 `backend/history.py` 内，后续应拆出独立 worker/queue。
  - `data_quality/`：新鲜度、字段完整性、异常值、跨源一致性。当前已有 mock 模块。
  - `claims/`：claim 抽取、证据绑定、真实性评分。
  - `strategy/`：过滤、因子评分、候选生成、持仓复核。
  - `memory/`：结构化分析记忆读写和版本管理。
  - `llm/`：RAG、反思 rubrics、最多 3 轮反思。**社区/公告情绪分类当前在 `backend/sentiment.py` 内直连 GLM/DeepSeek。**
  - `accounts/`：多账户、权限、账户级持仓/关注。当前已有 mock 模块。
  - `portfolio/`：账户级持仓、收益率、盈利金额、币种汇总。当前已有 mock 模块。
  - `audit/`：每次分析输入、输出、数据快照、版本号。
- [ ] 提供 API：
  - `GET /stocks/search` 已有 mock 版
  - `POST /screeners/run` 已有 mock 版
  - `GET /api/analysis/stocks/{symbol}` 已有 mock 版
  - `POST /api/analysis/anomalies` 已有 mock 版
  - `GET /memory/stocks/{symbol}` 已有 mock 版
  - `GET /api/data-sources` 已有 mock 版
  - `PUT /api/data-sources/{source_id}` 已有 mock 版
  - `POST /api/backtests/run` 已有数据库优先版
  - `PUT /api/accounts/{account_id}/favorites/{symbol}` 已有 mock 版
  - `POST /api/accounts/{account_id}/trades` 已有 mock 版
  - `GET /api/accounts/{account_id}/portfolio` 已有 mock 版
  - `POST /api/data/refresh` 已支持 provider 刷新；BaoStock 会启动后台任务
  - `GET /api/data/jobs/{run_id}` 已有 ingestion 任务状态查询

## 2. 数据库与记忆管理 TODO

推荐：本地版使用 SQLite 起步；分析历史和大批量行情可加 DuckDB/Parquet；如果做云同步，可用 PostgreSQL 或 Cloudflare D1。

### 核心原则

- 股票分析、异动分析、数据快照、claim、因子计算是共享资产。
- 不同账户的持仓列表、交易流水、关注列表、偏好设置是账户私有资产。
- 记忆不是一段泛泛总结，必须是结构化字段 + 版本 + 来源 + 失效条件。

### 建议表结构

- [x] `users`
  - `id`, `email`, `display_name`, `created_at`
- [x] `accounts`
  - `id`, `user_id`, `name`, `base_currency`, `created_at`
- [x] `symbols`
  - `symbol`, `market`, `name`, `currency`, `exchange`, `sector`, `industry`
- [x] `symbol_aliases`
  - `alias`, `normalized_alias`, `symbol`, `source`, `updated_at`
- [x] `daily_bars`
  - `symbol`, `trade_date`, `provider`, `adjust`, `open`, `high`, `low`, `close`, `pre_close`, `change_pct`, `volume`, `amount`, `turnover_rate`, `pe_ttm`, `pb`, `ps_ttm`, `pcf_ncf_ttm`, `is_st`, `trade_status`, `raw_json`, `fetched_at`
- [x] `financial_metrics_history`
  - `symbol`, `report_period`, `provider`, `announce_date`, `revenue_growth`, `roe`, `fcf_margin`, `debt_ratio`, `gross_margin`, `net_margin`, `raw_json`, `fetched_at`
- [x] `filings_history`
  - `symbol`, `source`, `published_at`, `title`, `url`, `category`, `source_tier`, `raw_json`, `fetched_at`
- [x] `ingestion_runs`
  - `provider`, `scope`, `status`, `started_at`, `finished_at`, `requested_symbols`, `updated_symbols`, `counts_json`, `errors_json`
- [x] `market_snapshots`
  - `id`, `symbol`, `provider`, `as_of`, `fetched_at`, `price`, `volume`, `amount`, `turnover_rate`, `spread_bps`, `raw_json`, `freshness_status`
- [x] `financial_snapshots`
  - `id`, `symbol`, `period`, `provider`, `revenue_growth`, `roe`, `fcf_margin`, `debt_ratio`, `pe`, `pb`, `raw_json`
- [ ] `news_items`
  - `id`, `symbol`, `source`, `source_tier`, `title`, `url`, `published_at`, `summary`, `sentiment_score`, `raw_text_hash`
- [ ] `claims`
  - `id`, `symbol`, `claim_text`, `claim_type`, `source_tier`, `source_url`, `confidence`, `truth_status`, `created_at`
- [ ] `factor_runs`
  - `id`, `symbol`, `as_of`, `factor_name`, `score`, `inputs_json`, `method_version`, `provider_set_hash`
- [x] `stock_analysis_runs`
  - `id`, `symbol`, `as_of`, `analysis_version`, `input_snapshot_hash`, `conclusion`, `action`, `confidence`, `reflection_json`, `created_at`
- [x] `anomaly_runs`
  - `id`, `scope_type`, `scope_key`, `question`, `as_of`, `report_json`, `evidence_json`, `created_at`
- [x] `stock_memories`
  - `id`, `symbol`, `memory_version`, `reusable_json`, `must_refresh_json`, `invalidated_by`, `source_run_id`, `created_at`
- [x] `account_favorites`
  - `account_id`, `symbol`, `created_at`, `note`
- [x] `account_trades`
  - `id`, `account_id`, `symbol`, `side`, `trade_date`, `quantity`, `price`, `fee`, `currency`, `broker`, `note`
- [x] `account_positions_cache`
  - `account_id`, `symbol`, `quantity`, `avg_cost`, `realized_pnl`, `unrealized_pnl`, `return_rate`, `computed_at`
- [x] `community_posts`
  - `source`, `symbol`, `source_post_id`, `title`, `content`, `author`, `url`, `published_at`, `metrics_json`, `raw_json`, `fetched_at`；唯一键 `(source, symbol, source_post_id)`
- [x] `sentiment_evidence`
  - `sentiment_type`, `source_table`, `source_id`, `method_version`, `symbol`, `event_date`, `sentiment_score`, `sentiment_label`, `confidence`, `keywords_json`, `evidence_json`, `analyzed_at`
- [x] `sentiment_snapshots`
  - 窗口内 composite 分、分项分、各源计数、标签、confidence
- [x] `community_sentiment_daily`
  - 按日汇总社区情绪（计数、分数、关键词、LLM 总评；不含评论原文）

### 记忆复用规则

- [ ] 可共享复用：公司画像、历史财务基线、已验证 claim、因子计算方法、历史分析版本、异动解释模板。
- [ ] 必须重新拉原数据：行情、K 线、盘口、成交额、买卖价差、新闻情绪、新公告、PE/PB 这种依赖最新价格的估值。
- [ ] 记忆失效条件：新财报、新公告、价格超过阈值、重大新闻、数据源冲突、模型版本更新。
- [ ] 每次二次分析流程：读取共享记忆 -> 拉增量数据 -> 判断失效模块 -> 只重算新增/失效部分 -> 更新记忆版本。

## 3. 多账户设计 TODO

用户需求：用户 A 分析过的股票，用户 B 可以直接拿到之前分析过的数据；但不同账户的持仓列表、关注列表不同。

### 数据边界

- 共享层：
  - `symbols`
  - `market_snapshots`
  - `financial_snapshots`
  - `news_items`
  - `claims`
  - `factor_runs`
  - `stock_analysis_runs`
  - `anomaly_runs`
  - `stock_memories`
- 账户私有层：
  - `account_favorites`
  - `account_trades`
  - `account_positions_cache`
  - 用户偏好、风险等级、默认市场、通知设置。

### 权限逻辑

- [ ] 用户登录后选择一个 account。
- [x] 查询股票分析时，先查共享分析缓存；如果新鲜且未失效，直接复用。当前为 mock API。
- [x] 查询持仓/关注时，只查当前 account。当前为 mock API。
- [x] 用户 A 的交易流水不能被用户 B 看到。当前为 mock API。
- [x] 用户 B 可以看到 A 触发过的共享股票分析结论，但不能看到 A 的私有持仓上下文。当前为 mock API。
- [x] 账户级持仓收益由后端计算并缓存。当前为 mock API。
- [ ] 分析结论里如果引用了持仓相关内容，必须拆成“共享结论”和“账户个性化建议”两段保存。

## 4. API Key 申请 TODO

### 行情和财务

- [x] BaoStock：A 股/ETF/指数代码宇宙、历史日线、PE/PB 回刷。无需 key，非实时。
- [x] Tushare Pro：A 股行情、基础资料、财务、交易日历方向已接入行情/财务缓存。需要 Tushare token。
- [x] AKShare：原型/补充数据和数据探索已接入；仍需持续做源质量标记。
- [x] Alpha Vantage：美股时间序列、基本面、新闻情绪探索已接入。需要 API key。
- [x] Finnhub：美股行情、公司新闻、基本面基础接入。需要 API key，当前按账户私有保存。
- [ ] Polygon/Massive：美股更高质量行情、聚合 K 线、WebSocket。生产环境建议申请 paid key。

### 官方披露

- [ ] SEC EDGAR：美股财报和披露。按 SEC 规则设置 User-Agent；如使用 EDGAR filer APIs 需 token。
- [ ] HKEXnews：港股公告。优先使用官方页面或授权数据商。
- [ ] CNINFO / 上交所 / 深交所：A 股公告和披露。优先官方源。

### AI 和检索

- [x] GLM / DeepSeek API key：社区评论、公告/新闻/财报情绪分类（`backend/sentiment.py`）；读 `.env` 中 `GLM_API_KEY` / `DEEPSEEK_API_KEY`。
- [ ] OpenAI API key：自然语言分析、claim 抽取、反思、异动解释（与情绪面并行，尚未统一进 `llm/` 模块）。
- [ ] Embedding / rerank 服务：可先用 OpenAI embedding，后续再评估本地 embedding。
- [ ] 可选：新闻供应商 API key，例如财联社、同花顺、Wind、Bloomberg、Refinitiv，视预算决定。

### 密钥管理

- [ ] 本地 Mac 版使用 macOS Keychain 保存 key。
- [ ] 后端服务使用 `.env` + 本机加密配置，禁止提交到 git。
- [ ] Cloudflare 部署时使用 Workers Secrets。

## 5. Cloudflare 自动化 TODO

同事提到的 Cloudflare 可以这样用：

### 适合 Cloudflare 的部分

- [ ] Cloudflare Workers Cron Triggers：定时触发每日扫描、盘前/盘后刷新、数据健康检查。
- [ ] Cloudflare Queues：把“拉行情、拉公告、跑分析、生成异动报告”拆成异步队列，避免一个请求做太久。
- [ ] Cloudflare D1：轻量云端 SQL，适合存用户、账户、关注、任务状态、共享分析索引。
- [ ] Cloudflare R2：保存大体积原始数据、公告文本、新闻快照、分析审计 JSON。
- [ ] Cloudflare Pages：如果后续做 Web 版，可以托管前端。

### 推荐任务流

1. Cron 每天/每小时触发 `scan-watchlist` Worker。
2. Worker 读取共享股票池和活跃账户关注/持仓。
3. Worker 把每个 symbol 的刷新任务发送到 Queue。
4. Queue consumer 拉数据、做新鲜度检测、写入共享快照。
5. 如果触发异动阈值，再发送 `analysis-anomaly` 任务。
6. 分析结果写入共享 `stock_analysis_runs` / `anomaly_runs`。
7. 用户打开 Mac app 时，本地同步最新共享分析和当前账户私有数据。

### 注意

- Cloudflare 适合做自动化和云同步，不建议把完整交易隐私只放云端。
- 如果软件定位是本地优先，持仓流水可默认本地保存，用户开启同步后再上传。
- 队列任务要有幂等 key，例如 `symbol + provider + as_of + task_type`。

## 6. Mac 软件打包 TODO

推荐路线：Tauri + 本地 FastAPI sidecar。

- [ ] 前端迁移到 Vite/React。
- [x] 后端 FastAPI 打包成本地 sidecar，监听 `127.0.0.1` 随 app 启动。当前为 Objective-C/WKWebView mock 壳。
- [x] 生成离线 mock 演示包，不依赖目标机器安装 Python 或 uvicorn。
- [ ] Tauri 负责窗口、菜单、托盘、权限、自动更新。
- [x] SQLite 数据库放在 app data 目录。当前使用 `~/Library/Application Support/Keiko Stock AI/data`。
- [ ] API key 放 macOS Keychain。
- [x] 生成 mock `.app`：`dist/macos/Keiko Stock AI.app`。
- [x] 生成 mock zip：`dist/macos/KeikoStockAI-mac-mock.zip`。
- [x] 生成离线 Universal mock zip：`dist/macos-offline/KeikoStockAI-mac-mock-offline-universal.zip`。
- [x] 设置 mock 包最低系统版本为 macOS 12.0。
- [x] 同时输出 Apple Silicon `arm64` 和 Intel `x86_64` 架构。
- [x] 修复 Mac 壳重新打开行为：关闭窗口后再次点击 App 会重新显示窗口。
- [x] 修复 Mac 壳端口占用问题：默认从 `8123` 开始自动选择可用端口。
- [ ] 使用 Tauri 打包正式 `.app` 和 `.dmg`。
- [ ] 用 Developer ID Application 证书签名官网分发版。
- [ ] 启用 Hardened Runtime，并配置必要 entitlement。
- [ ] 使用 Apple notary service 做 notarization。
- [ ] stapling 公证票据到 `.app` / `.dmg`。
- [ ] 生成正式 `.dmg` 或 `.pkg`，并验证 Gatekeeper 首次打开体验。
- [ ] 增加自动更新。官网分发可评估 Sparkle 或 Tauri updater。
- [ ] 如果走 Mac App Store，启用 App Sandbox，拆清本地服务、文件访问、网络访问和通知权限。
- [ ] 如果走 Mac App Store，准备 App Store Connect 信息、截图、隐私标签、审核说明和测试账号。

### 不能继续使用当前 zip 的场景

- [ ] 公开分发给真实用户：不能只用 ad-hoc 签名 zip，需要 Developer ID 签名和 notarization。
- [ ] Mac App Store 上架：不能直接上传当前 `.app` zip，需要 sandboxed、signed、archived 的 Xcode/Tauri 正式产物。
- [ ] iPhone 上架：不能把本地 Python/FastAPI 服务作为用户安装依赖，需要原生包或 WebView 调云端 API。

备选路线：

- Electron：开发快但体积更大。
- 纯 Web + Cloudflare：部署快，但本地持仓隐私和桌面体验弱。

## 6A. iPhone 版本 TODO

推荐路线：先 PWA/移动 Web，再决定是否做 App Store 原生包。

- [x] 加入 `manifest.webmanifest`。
- [x] 加入 `service-worker.js`，缓存 app shell，不缓存 `/api/` 实时请求。
- [x] 加入 iOS mobile web app meta 和底部导航。
- [x] 做 iPhone 安全区适配：顶部/底部 `env(safe-area-inset-*)`。
- [x] 增加局域网预览说明：iPhone 使用 Mac IP 访问，不使用 `localhost`。
- [x] 生成 iPhone SwiftUI/WKWebView mock 源码包：`dist/iphone/KeikoStockAI-iPhone-Mock-Source.zip`。
- [ ] 在完整 Xcode + Apple Developer Team 环境中生成可安装 `.ipa`。
- [ ] 创建正式 Bundle ID、App Group/Keychain Sharing 等需要的 capability。
- [ ] 配置 Apple Developer 证书和 provisioning profile。
- [ ] 用 Xcode Archive 上传到 App Store Connect。
- [ ] 先走 TestFlight 内测，再决定是否提交 App Review。
- [ ] 生成正式 Apple touch icon PNG 和完整 icon set。
- [ ] 设计移动端信息架构：把复杂表格拆成卡片式持仓、交易流水、claim 详情。
- [ ] 做 iPhone 登录/账户切换体验。
- [ ] 做云同步策略：iPhone 不直接访问 Mac 本机数据库，建议通过 Cloudflare/API 同步共享分析与账户私有数据。
- [ ] 正式 iPhone 版不依赖 Mac 局域网地址；所有共享分析、异动分析和账户数据通过云端 API 或用户选择的同步后端访问。
- [ ] 评估正式 iOS 包路线：
  - PWA：最快，适合自用和内测；推送、后台能力、App Store 分发有限。
  - Tauri iOS：可复用 Web 前端，适合和 Mac app 共用技术栈。
  - SwiftUI：体验最好，但开发成本更高。
  - React Native：移动端生态成熟，但和当前 Web demo 复用需要重新组织组件。
- [ ] 如果上架 App Store，补充隐私政策、投资风险披露、数据授权说明和账户数据删除机制。
- [ ] 如果涉及真实资金、券商连接、投资建议或金融交易，准备对应地区的资质/许可说明和审核材料。

## 7. 开发阶段 TODO

### Phase 1：真实数据最小闭环

- [x] A 股先完成历史行情最小闭环：BaoStock/Tushare/AKShare -> SQLite -> 搜索/筛选/分析/回测。
- [x] 美股完成 Finnhub/Alpha Vantage 探索和缓存起点。
- [x] 实现基础数据新鲜度检测。
- [x] 实现共享 `stock_analysis_runs` 和 `stock_memories` 的 mock 起点。
- [ ] 单股分析完全脱离前端 fallback，只基于后端结构化数据和证据生成。
- [x] BaoStock 后台回刷已有可恢复脚本入口和失败重试；前端触发仍用 FastAPI 进程内 background task。
- [ ] 后续把 BaoStock 回刷升级为正式独立 worker/持久队列，支持暂停、恢复、并发控制和任务 UI。
- [ ] 明确筛选/回测默认复权口径，避免未复权和 `qfq` 同时进入同一结果。
- [ ] 给 `daily_bars` 增加必要索引，评估 DuckDB/Parquet 存放大批量历史数据。
- [ ] 为 `debug_warehouse.py` 覆盖率和任务状态添加轻量测试。
- [ ] 把 BaoStock 季频 `financial_metrics_history` 接入单股分析的财务快照优先级，替代只读 `financial_snapshots` 的旧路径。
- [ ] 为 `company_reports_history` 增加前端检索/展示入口，和公告原文链接分开展示。

### Phase 1H：社区情绪（进行中）

- [x] 旧社区源已剔除；`community_posts` 现仅保留雪球入库。
- [x] 雪球讨论区爬虫（DrissionPage 浏览器内 fetch 过 WAF）。
- [x] 雪球 quote 补 GLM prompt 实时价/涨跌幅（`KEIKO_XUEQIU_COOKIE`）。
- [x] 社区 GLM 五档分类 + 关键词；A 股黑话 prompt 规则（guba-v6）。
- [x] 三类 evidence 聚合为 `sentiment_snapshots`；回测页 `sentiment_panels`。
- [x] 半小时 agent + plist；空参数刷新 `acct-admin` 自选股。
- [x] 文档：`docs/sentiment.README.md`。
- [ ] 本机默认 load `com.keiko.community-sentiment-agent.plist`（当前需手动配置路径）。
- [ ] 雪球评论：浏览器会话复用/池化，降低多股连续刷新时的 Chrome 启动开销。
- [ ] 社区爬虫单元测试（mock HTML / mock browser JSON），避免回归 WAF 解析逻辑。
- [ ] `sentiment_status` / 设置页展示 xueqiu 配置状态、最近抓取成功率。
- [ ] 评估 Playwright 替代 DrissionPage（CI 友好性、依赖体积）。

### Phase 2：账户系统和持仓

- [ ] 多账户模型。
- [ ] 账户级关注列表。
- [ ] 账户级交易流水。
- [ ] 持仓收益计算服务。
- [ ] K 线 B/S 标记真实化。

### Phase 3：A/HK/US 数据源

- [x] A 股：BaoStock + Tushare + CNINFO/交易所公告起点。
- [ ] A 股：补交易日历、停复牌、分红拆股、复权因子、行业分类和财务报告历史。
- [ ] 港股：行情供应商 + HKEXnews。
- [ ] 美股：Polygon/Finnhub/Alpha Vantage + SEC EDGAR。
- [ ] 做统一 symbol 标准化、币种、交易日历、时区。

### Phase 4：异动分析自动化

- [ ] 建立异动阈值：涨跌幅、量能、价差、新闻热度、未证实比例。
- [ ] Cloudflare Cron 定时扫描。
- [ ] Cloudflare Queue 异步跑任务。
- [ ] 异动报告进入共享缓存。
- [ ] 用户可订阅账户级提醒。

### Phase 5：桌面软件

- [ ] Tauri 打包 Mac app。
- [ ] Keychain 密钥管理。
- [ ] 本地数据库迁移。
- [ ] 自动更新。
- [ ] 错误日志和审计导出。

## 8. 参考资料

- 情绪面说明：`docs/sentiment.README.md`
- 雪球 WAF 参考：[ForgeRSS xueqiu](https://github.com/tmwgsicp/ForgeRSS)、[xueqiu_crawler](https://github.com/stock2money/xueqiu_crawler)
- Tushare Pro 文档：https://tushare.pro/document/2
- BaoStock 文档：https://www.baostock.com/mainContent?file=home.md
- Alpha Vantage API 文档：https://www.alphavantage.co/documentation/
- Finnhub API 文档：https://www.finnhub.io/docs/api
- SEC EDGAR APIs：https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/understand-edgar-application-programming-interfaces-apis
- Cloudflare Workers Cron Triggers：https://developers.cloudflare.com/workers/configuration/cron-triggers/
- Cloudflare Queues：https://developers.cloudflare.com/queues/
- Cloudflare D1：https://developers.cloudflare.com/d1/get-started/
- Tauri：https://tauri.app/start/
