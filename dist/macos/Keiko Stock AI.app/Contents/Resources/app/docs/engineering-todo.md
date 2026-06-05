# Keiko Stock AI 工程 TODO

更新时间：2026-06-05

目标：把当前静态 mock demo 逐步变成可安装在 MacBook 上、支持多账户、真实数据、共享分析记忆、独立持仓/关注的股票研究软件。

## 0. 当前 Demo 已验证

- 股票池过滤：显式规则 + 自然语言规则。
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
- Phase 1D 打包：已生成 Mac mock `.app`、Mac zip、iPhone SwiftUI/WKWebView mock 源码包和 iPhone zip。

## 1. 技术架构 TODO

### 前端

- [ ] 把当前 `index.html` / `styles.css` / `app.js` 迁移到 React + TypeScript + Vite。
- [x] 当前静态前端加入 PWA/iPhone app shell。
- [ ] 拆组件：`StockCard`、`SingleStockDrawer`、`PortfolioTable`、`AnomalyReport`、`DataHealthPanel`、`MemoryPanel`。
- [ ] 建立前端状态层：用户会话、当前账户、股票池过滤、关注列表、持仓、分析报告、异动报告。
- [ ] 所有按钮和表单增加 loading、error、empty、stale 状态。
- [ ] 为关键交互写 Playwright 测试：查看分析、关注/取消关注、录入 Buy/Sell、刷新股价、生成异动报告。
- [ ] 生成正式 iOS app icon PNG/icon set，替换当前 SVG 原型图标。

### 后端

- [x] 使用 FastAPI 做本地 API 服务。
- [ ] 建立模块：
  - `providers/`：行情、财务、公告、新闻、情绪供应商适配器。
  - `ingestion/`：拉取、去重、标准化、缓存。
  - `data_quality/`：新鲜度、字段完整性、异常值、跨源一致性。当前已有 mock 模块。
  - `claims/`：claim 抽取、证据绑定、真实性评分。
  - `strategy/`：过滤、因子评分、候选生成、持仓复核。
  - `memory/`：结构化分析记忆读写和版本管理。
  - `llm/`：RAG、反思 rubrics、最多 3 轮反思。
  - `accounts/`：多账户、权限、账户级持仓/关注。当前已有 mock 模块。
  - `portfolio/`：账户级持仓、收益率、盈利金额、币种汇总。当前已有 mock 模块。
  - `audit/`：每次分析输入、输出、数据快照、版本号。
- [ ] 提供 API：
  - `GET /stocks/search`
  - `POST /screeners/run`
  - `GET /api/analysis/stocks/{symbol}` 已有 mock 版
  - `POST /api/analysis/anomalies` 已有 mock 版
  - `GET /memory/stocks/{symbol}`
  - `PUT /api/accounts/{account_id}/favorites/{symbol}` 已有 mock 版
  - `POST /api/accounts/{account_id}/trades` 已有 mock 版
  - `GET /api/accounts/{account_id}/portfolio` 已有 mock 版
  - `POST /api/data/refresh` 已有 mock 版

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
- [ ] `market_snapshots`
  - `id`, `symbol`, `provider`, `as_of`, `fetched_at`, `price`, `volume`, `amount`, `turnover_rate`, `spread_bps`, `raw_json`, `freshness_status`
- [ ] `financial_snapshots`
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

- [ ] Tushare Pro：A 股行情、基础资料、财务、交易日历。需要 Tushare token。
- [ ] AKShare：原型/补充数据，可先不需要 key，但必须做源质量标记。
- [ ] Alpha Vantage：美股时间序列、基本面、新闻情绪。需要 API key。
- [ ] Finnhub：美股/全球股票行情、公司新闻、基本面。需要 API key。
- [ ] Polygon/Massive：美股更高质量行情、聚合 K 线、WebSocket。生产环境建议申请 paid key。

### 官方披露

- [ ] SEC EDGAR：美股财报和披露。按 SEC 规则设置 User-Agent；如使用 EDGAR filer APIs 需 token。
- [ ] HKEXnews：港股公告。优先使用官方页面或授权数据商。
- [ ] CNINFO / 上交所 / 深交所：A 股公告和披露。优先官方源。

### AI 和检索

- [ ] OpenAI API key：自然语言分析、claim 抽取、反思、异动解释。
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
- [ ] Tauri 负责窗口、菜单、托盘、权限、自动更新。
- [x] SQLite 数据库放在 app data 目录。当前使用 `~/Library/Application Support/Keiko Stock AI/data`。
- [ ] API key 放 macOS Keychain。
- [x] 生成 mock `.app`：`dist/macos/Keiko Stock AI.app`。
- [x] 生成 mock zip：`dist/macos/KeikoStockAI-mac-mock.zip`。
- [ ] 使用 Tauri 打包正式 `.app` 和 `.dmg`。
- [ ] 后续增加签名、公证、自动更新。

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
- [ ] 生成正式 Apple touch icon PNG 和完整 icon set。
- [ ] 设计移动端信息架构：把复杂表格拆成卡片式持仓、交易流水、claim 详情。
- [ ] 做 iPhone 登录/账户切换体验。
- [ ] 做云同步策略：iPhone 不直接访问 Mac 本机数据库，建议通过 Cloudflare/API 同步共享分析与账户私有数据。
- [ ] 评估正式 iOS 包路线：
  - PWA：最快，适合自用和内测；推送、后台能力、App Store 分发有限。
  - Tauri iOS：可复用 Web 前端，适合和 Mac app 共用技术栈。
  - SwiftUI：体验最好，但开发成本更高。
  - React Native：移动端生态成熟，但和当前 Web demo 复用需要重新组织组件。
- [ ] 如果上架 App Store，补充隐私政策、投资风险披露、数据授权说明和账户数据删除机制。

## 7. 开发阶段 TODO

### Phase 1：真实数据最小闭环

- [ ] 选择一个市场先做，建议美股。
- [ ] 接入行情 K 线 + SEC EDGAR + 新闻情绪。
- [ ] 实现数据新鲜度检测。
- [ ] 实现共享 `stock_analysis_runs` 和 `stock_memories`。
- [ ] 单股分析只基于结构化数据和证据生成。

### Phase 2：账户系统和持仓

- [ ] 多账户模型。
- [ ] 账户级关注列表。
- [ ] 账户级交易流水。
- [ ] 持仓收益计算服务。
- [ ] K 线 B/S 标记真实化。

### Phase 3：A/HK/US 数据源

- [ ] A 股：Tushare + CNINFO/交易所公告。
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

- Tushare Pro 文档：https://tushare.pro/document/2
- Alpha Vantage API 文档：https://www.alphavantage.co/documentation/
- Finnhub API 文档：https://www.finnhub.io/docs/api
- SEC EDGAR APIs：https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/understand-edgar-application-programming-interfaces-apis
- Cloudflare Workers Cron Triggers：https://developers.cloudflare.com/workers/configuration/cron-triggers/
- Cloudflare Queues：https://developers.cloudflare.com/queues/
- Cloudflare D1：https://developers.cloudflare.com/d1/get-started/
- Tauri：https://tauri.app/start/
