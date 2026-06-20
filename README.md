# 聚宝盆

本地安装型选股研究台原型。当前版本已从纯 mock 演示推进到“本地 SQLite 历史数据仓库 + 真实/缓存数据源”方向：支持 BaoStock 历史日线回刷、Tushare/AKShare/Finnhub/Alpha Vantage 等数据源配置、股票搜索、数据库筛选、回测和共享分析记忆；LLM 投研结论仍处于研究辅助原型阶段。

> 这是研究辅助软件原型，不构成投资建议。真实交易前必须接入授权数据源，并由用户独立复核。

## 立即预览

推荐使用本地 FastAPI 后端启动，这样可以验证多账户、SQLite 历史仓库、共享分析缓存和真实/缓存数据源：

```bash
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8100
```

然后访问 `http://localhost:8100`。

如果要试 AKShare 真实数据模块，先安装后端依赖：

```bash
python3 -m pip install -r requirements.txt
```

AKShare 当前主要用于数据探索和部分 A 股历史行情 fallback，并暴露独立 API 方便查看能拉到哪些字段：

- `GET /api/akshare/status`：检查当前 Python 环境是否已安装 AKShare。
- `GET /api/akshare/capabilities`：查看已登记能力、分类、AKShare 函数名、示例参数和当前版本是否支持。
- `GET /api/akshare/query/{capability_id}`：按白名单能力调用 AKShare，例如 `/api/akshare/query/stock_a_hist?symbol=600519&adjust=qfq&limit=20`。
- `GET /api/akshare/search?q=茅台&market=A`：跨 A/HK/US 市场搜索股票快照。
- `GET /api/akshare/stocks/A/600519/hist?adjust=qfq&limit=60`：股票历史行情快捷入口，支持 `A`、`HK`、`US`。
- `GET /api/akshare/indices/spot?limit=50`：A 股指数快照快捷入口。

已登记的 AKShare 能力覆盖：A 股/港股/美股快照与历史 K 线、A 股分钟线、A 股个股资料、财务摘要、三大财务报表、个股新闻、A 股指数、行业/概念板块、ETF/开放式基金、债券/可转债、CPI/PPI/PMI/GDP、外汇、期货主力连续和全球财经资讯。真实可用范围取决于当前安装的 AKShare 版本、上游源站可用性和网络环境；接口会把源站异常转成可读错误，不会影响原有 mock 页面。

当前已新增本地 `acct-admin` 管理账户。数据源开关和 API key 按 `account_id + source_id` 存在 SQLite 私有表里，不再是全局配置；行情、财务、新闻等刷新后的标准化快照仍属于共享缓存。Finnhub 支持美股报价、基本面和公司新闻：

- `GET /api/data/finnhub/status?account_id=acct-admin`：查看 admin 账户下 Finnhub key 和三个数据源是否生效。
- `POST /api/data/finnhub/refresh`：刷新美股数据，例如 body 为 `{"provider":"finnhub","account_id":"acct-admin","symbols":["AAPL","NVDA"]}`。
- 也可以在设置页的 admin 账户下保存 Finnhub key；环境变量 `KEIKO_FINNHUB_TOKEN` 或 `FINNHUB_API_KEY` 也会被识别。

## 问财基本面画像

2026-06-20 新增问财个股详情画像入库和展示。脚本会抓取问财页面里的三块数据：

- 简介和看点
- 近期概念事件
- 所属概念列表

数据写入独立 SQLite：

```bash
data/iwencai_profile.db
```

单股详情接口会返回 `fundamental.iwencai`，前端在单股详情抽屉右侧新增 `基本面 / 情绪面` tab。有问财画像时默认显示基本面，展示顺序为简介和看点、近期概念事件、所属概念列表；所属概念详情默认收起，点击后展开。原来 K 线下方重复的“社区来源”条已移除，左侧 K 线图也缩小为更紧凑的展示。

手动抓单个股票：

```bash
python3 scripts/crawl_iwencai_profile.py 000725.SZ --force
```

慢速续跑失败和未跑标的，跳过最近 168 小时内已 `ok/no_sections` 的记录：

```bash
scripts/run_iwencai_profile_slow_resume.sh
```

慢跑配置内置连续 403 断路保护：连续 5 次 `403 Forbidden` 后暂停 2 小时，冷却后新建 session/token 继续跑。2026-06-20 21:00 本机已设置 LaunchAgent 自动启动慢跑；当前 LaunchAgent 避开 shell 包装，直接调用 conda `python3 -u scripts/crawl_iwencai_profile.py ...`。详细表结构、监控命令和停止方式见 `docs/iwencai-profile.README.md`。

问财画像还可以同步成关键词 + BGE/Qdrant 混合召回库：`scripts/run_iwencai_recall_daily.py` 会按天检查是否有新增可索引画像股票，有新增才整库重建；检索接口是 `/api/iwencai-recall/search`。使用方法见 `docs/iwencai-profile.README.md` 的“画像召回库”小节。

## BaoStock 历史数据仓库

BaoStock 用作 A 股、ETF、指数的历史回刷源，不作为实时行情源。已接入：

- `query_all_stock`：写入 `symbols` 和 `symbol_aliases`，用于股票名/代码搜索。
- `query_history_k_data_plus`：写入 `daily_bars` 和最新 `market_snapshots`，字段包括 OHLC、成交量、成交额、换手率、`peTTM`、`pbMRQ`、`psTTM`、`pcfNcfTTM`、`isST`。
- 季频财务指标：`query_profit_data`、`query_operation_data`、`query_growth_data`、`query_balance_data`、`query_cash_flow_data`、`query_dupont_data` 写入 `financial_metrics_history`。
- 季频公司报告：`query_performance_express_report`、`query_forecast_report` 写入 `company_reports_history`。
- 后台长任务：点击设置页 BaoStock “刷新数据”或调用 `/api/data/refresh` 后立即返回 `run_id`，后端按批继续回刷；网络接收错误会自动等待、重新登录并重试，长时间没有心跳的旧 `running` 任务会标记为 `interrupted` 后按缺口继续。

启动后台回刷：

```bash
curl -sS http://127.0.0.1:8100/api/data/refresh \
  -H 'Content-Type: application/json' \
  -d '{"provider":"baostock","scope":"baostock","account_id":"acct-admin","refresh_universe":true}'
```

查询任务：

```bash
curl -sS http://127.0.0.1:8100/api/data/jobs/<run_id>
```

后台/定时任务也可以直接跑脚本：

```bash
python3 scripts/run_baostock_backfill.py --days 260 --batch-size 30
```

季度财务/公司报告回刷：

```bash
python3 scripts/run_baostock_financial_backfill.py --quarters 12 --batch-size 10
```

公告/披露缺口回刷：

```bash
python3 scripts/run_a_share_filings_backfill.py --source all --days 180 --batch-size 20
```

或走接口：

```bash
curl -sS http://127.0.0.1:8100/api/data/refresh \
  -H 'Content-Type: application/json' \
  -d '{"provider":"baostock-financial","scope":"quarterly-financials","account_id":"acct-admin","refresh_universe":true}'
```

季度任务按 A 股披露截止日选择成熟季度。例如 2026-06-07 会从 2026Q1 开始，不会提前把未披露的 2026Q2 写成空数据。ETF/指数等无季报证券会写 `raw_json.status = "no_data"` 的空指标占位，避免全市场任务重复刷同一批无数据标的。

BaoStock 季频财务和公司报告批次通过子进程执行；如果 SDK 网络接收卡住，父进程会按批次规模超时终止子进程并把 run 标记为 `partial`/`failed`，不会让后台任务无限挂住。

本机已安装 macOS LaunchAgent：

- `com.keiko.baostock-nightly`：每天 00:00 运行日线回刷，日志位于 `logs/baostock-nightly.log` 和 `logs/baostock-nightly.err.log`。项目内配置文件是 `scripts/com.keiko.baostock-nightly.plist`。
- `com.keiko.baostock-financial-nightly`：每天 02:30 运行季频财务/公司报告回刷，批量为 3，日志位于 `logs/baostock-financial-nightly.log` 和 `logs/baostock-financial-nightly.err.log`。项目内配置文件是 `scripts/com.keiko.baostock-financial-nightly.plist`。
- `com.keiko.a-share-filings-nightly`：每天 20:30 运行 A 股公告缺口回刷，默认拉 CNINFO 加上对应交易所公告，日志位于 `logs/a-share-filings-nightly.log` 和 `logs/a-share-filings-nightly.err.log`。项目内配置文件是 `scripts/com.keiko.a-share-filings-nightly.plist`。
- `com.keiko.ingestion-watchdog`：每 15 分钟运行 `scripts/run_ingestion_watchdog.py --json`，发现 stale running、孤儿旧进程、或最新任务 `partial/failed/interrupted` 且仍有剩余候选时，会先终止旧脚本，再小批量启动一个续跑任务。日志位于 `logs/ingestion-watchdog.log` 和 `logs/ingestion-watchdog.err.log`。
- `com.keiko.iwencai.profile.slowresume.once`：2026-06-20 21:00 运行问财画像慢速续跑，LaunchAgent 直接调用 conda Python，避免 `/bin/bash -lc` 触发 macOS 权限拦截。日志位于 `logs/iwencai_profile_launchd_once.out.log` 和 `logs/iwencai_profile_launchd_once.err.log`。配置文件在 `~/Library/LaunchAgents/com.keiko.iwencai.profile.slowresume.once.plist`。

本地仓库诊断脚本：

```bash
python3 scripts/debug_warehouse.py summary
python3 scripts/debug_warehouse.py coverage
python3 scripts/debug_warehouse.py providers
python3 scripts/debug_warehouse.py daily-symbol 600519.SH
python3 scripts/debug_warehouse.py financials
python3 scripts/debug_warehouse.py financial-symbol 600519.SH --quarters 12
python3 scripts/debug_warehouse.py missing-bars --limit 50
python3 scripts/debug_warehouse.py symbol 中金黄金 --limit 20
```

字段说明见 `docs/warehouse-schema.md`，调试脚本说明见 `scripts/debug_warehouse.README.md`。

改动 BaoStock 仓库逻辑后先跑：

```bash
python3 scripts/test_warehouse_guards.py
python3 -m compileall backend scripts
```

## Alpha Vantage 美股接入

Alpha Vantage key 不写入源码；本机可放在 `.env`，也可以用环境变量：

```bash
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

已接入的快捷 API：

- `GET /api/alpha-vantage/status`
- `GET /api/alpha-vantage/capabilities`
- `GET /api/alpha-vantage/search?q=AAPL`
- `GET /api/alpha-vantage/quote/AAPL`
- `GET /api/alpha-vantage/stocks/AAPL/daily?return_limit=20`
- `GET /api/alpha-vantage/stocks/AAPL/intraday?interval=5min&return_limit=50`
- `GET /api/alpha-vantage/stocks/AAPL/overview`
- `GET /api/alpha-vantage/stocks/AAPL/financials?sections=overview,income`
- `GET /api/alpha-vantage/news-sentiment?tickers=AAPL&limit=20`
- `GET /api/alpha-vantage/etf/SPY/profile`
- `GET /api/alpha-vantage/market-status`
- `GET /api/alpha-vantage/top-movers`
- `GET /api/alpha-vantage/listing-status?state=active&return_limit=100`
- `GET /api/alpha-vantage/currency-exchange-rate?from_currency=USD&to_currency=CNY`

`/api/alpha-vantage/query/{capability_id}` 是通用白名单入口，设置页的 Alpha Vantage 数据探索面板也使用这个接口。已登记能力覆盖代码搜索、上市列表、quote、盘中分钟线、日线、复权日/周/月线、涨跌幅榜、公司概览、三大财务报表、EPS、ETF profile、新闻情绪、市场状态和汇率。实测当前 key 可调用 `GLOBAL_QUOTE` 和免费 `TIME_SERIES_DAILY`；`TIME_SERIES_DAILY_ADJUSTED` 这类复权接口可能按 Alpha Vantage 套餐返回 premium 提示。

如果要在同一 Wi-Fi 的 iPhone 上预览，启动局域网可访问版本：

```bash
python3 -B -m uvicorn backend.app:app --host 0.0.0.0 --port 8101
```

然后在 iPhone Safari 访问 `http://<你的 Mac 局域网 IP>:8101`。iPhone 不能用 `localhost` 访问 Mac，因为手机上的 `localhost` 指向手机自己。

如果要临时让非局域网用户访问，可以用 ngrok 把本机 `8100` 端口映射成公网 HTTPS 地址。当前本机已下载 Apple Silicon 版 ngrok 到项目内 `tools/ngrok`，authtoken 保存在用户目录的 ngrok 配置中，不写入源码。

先确认本地 FastAPI 服务已启动：

```bash
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8100
```

另开一个终端启动公网隧道：

```bash
tools/ngrok http 8100 --log=stdout
```

终端输出里的 `https://...ngrok-free.dev` 就是可发给别人访问的临时公网地址。这个方式依赖当前 Mac、uvicorn 和 ngrok 持续运行；机器睡眠、终端关闭或隧道断开后地址会失效。当前应用没有登录保护，只适合发给信任的人临时预览，不适合作为正式公开网站。

也可以直接在浏览器打开静态文件，前端会自动退回到内置 mock 数据：

```bash
open /Users/admin/Documents/keiko_stock/index.html
```

## Mock App 打包

当前打包产物适合做 mock 演示、团队内测和兼容性验证，不是正式上架包。

推荐发给别人试用的离线演示包：

- App：`dist/macos-offline/Keiko Stock AI.app`
- Zip：`dist/macos-offline/KeikoStockAI-mac-mock-offline-universal.zip`
- 打包脚本：`scripts/package_mac_offline_app.sh`

这个包是 Objective-C + WKWebView 壳，直接打开内置静态页面和 mock 数据，不依赖对方电脑安装 Python、uvicorn 或后端依赖。当前已按 Universal binary 打包，包含 Apple Silicon 和 Intel 两个架构，并把最低系统版本设置为 macOS 12.0。它仍然只是 ad-hoc 签名，未做 Apple notarization，所以适合内测，不适合公开分发或上架。

开发调试用的本地后端包：

- App：`dist/macos/Keiko Stock AI.app`
- Zip：`dist/macos/KeikoStockAI-mac-mock.zip`
- 打包脚本：`scripts/package_mac_app.sh`

这个包会启动本地 FastAPI 后端，再在 app 窗口中打开页面。SQLite 会写入 `~/Library/Application Support/Keiko Stock AI/data`，不会写进 `.app` 资源目录。它更适合本机开发调试；如果发给别人，对方机器仍可能缺少 Python 或 Python 依赖。

Mac app 壳已处理两个启动稳定性问题：如果关闭窗口后再次打开 App，会重新显示窗口；如果默认 `8123` 端口被占用，会自动选择后续可用端口启动后端。

iPhone mock app 已生成源码包：

- 源码目录：`dist/iphone/KeikoStockAI-iPhone-Mock`
- Zip：`dist/iphone/KeikoStockAI-iPhone-Mock-Source.zip`
- 打包脚本：`scripts/package_ios_mock_source.sh`

当前机器只有 Command Line Tools，没有完整 Xcode、iOS SDK、模拟器和 Apple 签名环境，所以这里不能直接产出可安装 `.ipa`。iPhone 版本先提供两种方式：Safari 添加到主屏幕的 PWA；或者把源码包放进完整 Xcode 项目后签名运行。

## 正式上架与公开分发

如果目标是上架或公开发给用户，不能直接用现在这种 ad-hoc zip。

Mac 公开分发有两条路线：

1. Mac App Store：需要完整 Xcode 工程、Apple Developer Program、Bundle ID、正式签名、App Sandbox、权限说明、App Store Connect 提交和 App Review。Apple 明确要求通过 Mac App Store 分发的 macOS app 启用 App Sandbox。
2. 官网下载：不走 App Review，但也要用 Developer ID 签名、Hardened Runtime、notarization、公证票据 stapling，再做 `.dmg` 或 `.pkg`。Apple 的 notarization 不是 App Review，但会检查恶意内容和签名问题，Gatekeeper 会据此判断用户是否能放心打开。

iPhone 上架只能走完整 Xcode + Apple Developer Team + App Store Connect/TestFlight/App Review。不能靠把 zip 或本地 Python 服务塞给用户安装；正式 iPhone 版应改成原生壳或 WebView 调云端 API，账户数据和共享分析通过后端同步。

股票/投资类软件还要额外准备：隐私政策、数据授权证明、投资风险披露、用户数据删除机制、模型免责声明，以及各市场行情/资讯 API 的商业授权。Apple App Review Guidelines 对金融、投资、资金管理类 app 有更严格的资质和许可要求。

参考 Apple 官方文档：[Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)、[Developer ID](https://developer.apple.com/support/developer-id/)、[App Sandbox](https://developer.apple.com/documentation/security/app_sandbox)、[TestFlight](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/)、[App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)。

## 当前内容

- `index.html`：本地单页应用入口。
- `styles.css`：响应式界面样式。
- `app.js`：前端交互、API 调用、fallback 股票数据、筛选、分析、数据健康和反思渲染逻辑。
- `manifest.webmanifest`：iPhone/PWA 安装入口元数据。
- `service-worker.js`：PWA app shell 缓存，API 请求仍走实时后端。
- `assets/app-icon.svg`：当前原型图标，后续打包阶段替换为正式 PNG/icon set。
- `packaging/mac/`：Mac WKWebView app 壳和 Info.plist。
- `ios/KeikoStockAI/`：iPhone SwiftUI/WKWebView mock app 源码壳。
- `scripts/package_mac_app.sh`：生成 Mac `.app` 和 zip。
- `scripts/package_mac_offline_app.sh`：生成不依赖 Python 后端的 Mac 离线 mock `.app` 和 zip。
- `scripts/package_ios_mock_source.sh`：生成 iPhone mock 源码包。
- `backend/app.py`：FastAPI 后端，提供账户、关注、交易、共享分析、异动分析、数据源刷新和历史仓库 API。
- `backend/accounts.py`：账户私有关注和交易流水服务。
- `backend/analysis.py`：共享单股分析、共享异动分析和共享缓存统计。
- `backend/portfolio.py`：账户级持仓、收益率、盈利金额和持仓缓存计算。
- `backend/data_quality.py`：数据健康检查和刷新任务基础响应。
- `backend/db.py`：SQLite 连接、schema 初始化和种子库写入。
- `backend/seed_data.py`：SQLite 种子数据，模拟多账户与共享分析缓存。
- `backend/providers/`：数据源 provider，包含 mock fallback、Tushare、AKShare、Alpha Vantage、Finnhub、BaoStock 和公告适配器。
- `backend/providers/iwencai_profile.py`：问财基本面画像客户端、解析器、SQLite schema/upsert/read helper，写入 `data/iwencai_profile.db`。
- `backend/providers/tushare.py`：Tushare Pro HTTP 客户端，按官方 Pro 协议调用 `stock_basic`、`daily`、`daily_basic`、`income`、`fina_indicator`。
- `backend/tushare_service.py`：Tushare A 股刷新服务，把真实行情和财务快照写入 SQLite 缓存。
- `backend/history.py`：历史数据仓库服务，负责 AKShare/BaoStock/Tushare fallback、BaoStock 后台回刷、数据库筛选和回测日线读取。
- `backend/providers/baostock_provider.py`：BaoStock 适配器，封装 `query_all_stock`、`query_history_k_data_plus` 等接口。
- `backend/providers/filings.py`：CNINFO、上交所、深交所、HKEXnews 公告/披露查询适配器。
- `backend/filings.py`：公告来源选择、日期校验和统一返回结构。
- `backend/data_sources.py`：网页版数据源配置服务，控制哪些来源进入分析。
- `backend/stocks.py`：股票搜索、筛选、分析展示和记忆 API 服务。
- `backend/backtesting.py`：回测平台研究引擎，优先使用 `daily_bars`，数据不足时回退到研究 mock。
- `scripts/fetch_filings.py`：命令行查询官方公告/披露数据。
- `scripts/run_baostock_backfill.py`：后台/定时 BaoStock 回刷入口，复用 `ingestion_runs` 和 SQLite 历史仓库，可断点续跑。
- `scripts/run_baostock_financial_backfill.py`：BaoStock 季频财务指标和公司报告后台回刷入口。
- `scripts/run_a_share_filings_backfill.py`：A 股公告/披露缺口后台回刷入口，覆盖 CNINFO、SSE、SZSE 和自动源。
- `scripts/crawl_iwencai_profile.py`：问财画像抓取入口，支持关注股、A 股个股、指数分层抓取、最近数据跳过、连续 403 断路冷却。
- `scripts/run_iwencai_profile_slow_resume.sh`：问财画像慢速续跑封装脚本，默认跳过新鲜成功记录，补失败和未跑标的。
- `scripts/debug_warehouse.py`：只读调试 SQLite 历史数据仓库，查看 provider 覆盖、BaoStock 缺口、PE/PB 和 ingestion 任务。
- `scripts/debug_warehouse.README.md`：debug 脚本和 BaoStock 后台任务使用说明。
- `requirements.txt`：后端运行依赖。
- `docs/official-filings-data.md`：真实公告数据源接入说明和 API/CLI 示例。
- `docs/warehouse-schema.md`：SQLite 历史数据仓库字段字典和 provider 原始字段映射。
- `docs/research-report.md`：数据源、资讯源、真实性判断、情绪面、AI 反思和落地路线报告。
- `docs/sentiment.README.md`：社区情绪（股吧+雪球）、GLM prompt、雪球 quote/评论配置、半小时 agent、自选股刷新范围。
- `docs/iwencai-profile.README.md`：问财基本面画像数据库、抓取脚本、断路保护、21:00 慢跑任务和监控命令。
- `docs/engineering-todo.md`：后端、数据库、API key、自动化、多账户和打包 TODO。
- `docs/handoff.md`：换电脑或开启新 Codex 会话时的交接说明。

## 已实现的交互原型

- 筛选股票：支持按市场、流动性、估值质量、技术催化、证据风险组合筛选。
- 自然语言过滤：可输入类似“趋势强、放量、催化、任一”的描述来启用过滤规则。
- 结构化记忆：区分可复用中间结果、必须重新拉取的原始数据、本次增量。
- 低置信处理：数据过时可点“刷新数据”，证据不足可补充材料并更新可信度。
- Claim 追溯：每条判断可查看来源等级、置信度、字段快照、分析过程和链接。
- 因子详情：每个因子可查看具体数据值、数据来源和计算/复核逻辑。
- 我的持仓：支持录入 Buy/Sell，按交易记录计算剩余持仓、盈利金额、收益率，并展示天级收益曲线。
- 关注/持仓拆分：关注列表和持仓列表是两个独立页面；关注列表使用股票卡片，持仓列表支持收益、刷新股价、折叠流水和带 B/S 标记的 K 线。
- 异动分析：支持从今日观察、关注列表和持仓列表生成股票池，点击股票查看异动报告，也支持自然语言询问大盘或板块异动。
- 单股分析浮层：点击任意股票的“查看分析”后打开较轻量的浮动分析界面，关闭按钮放在左上角，更贴近 Mac 使用习惯。
- 本地后端：页面启动时优先读取 `/api/bootstrap`；后端不可用时保持本地 fallback。
- 多账户原型：账户 A/B 可切换；股票分析、异动分析、记忆共享；关注列表和持仓流水按账户隔离。
- 后端持仓计算：`/api/accounts/{account_id}/portfolio` 返回账户级持仓、盈亏、收益率和币种汇总。
- 后端刷新盈利：点击“刷新股价”会调用 `/api/data/refresh`，用 mock 最新价重算 portfolio。
- iPhone/PWA 原型：支持 mobile web app meta、manifest、service worker 和手机底部导航。
- 网页版 tab：左侧导览切换后只显示当前 tab 内容，不再把后续页面连续接在下面。
- 设置页：按 A/HK/US 市场配置行情、财务、公告、新闻情绪数据源；未启用或未配置的数据源不会进入后续分析。
- 回测平台：支持选择策略模板、市场、区间、持仓数、调仓频率、手续费和滑点，优先基于数据库历史日线生成研究回测。
- Tushare Pro：支持账户级 token 配置，刷新 A 股行情/每日指标/利润表/财务指标，搜索和持仓价格优先使用 Tushare 缓存。
- BaoStock：支持 A 股/ETF/指数代码宇宙回刷、历史 K 线后台长任务、PE/PB 缓存和 SQLite 仓库覆盖率诊断。
- 问财基本面画像：单股详情右侧新增“基本面分析”tab，展示简介和看点、近期概念事件、所属概念列表；概念详情默认收起可展开。
- 数据库筛选：筛选股票“应用”直接查 `daily_bars`，自然语言如 `PE<10` 会作为独立 SQL 条件，不会自动勾选复选框。

## Tushare Pro A 股接入

当前已接入 Tushare Pro 的 A 股行情和财务缓存。token 不写入源码，可以通过环境变量配置：

```bash
export KEIKO_TUSHARE_TOKEN="你的 Tushare Pro token"
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8100
```

也可以在网页“设置”页里给 `Tushare Pro A股行情` 或 `Tushare Pro 财务/估值` 保存 token。凭据按账户写入本地 SQLite 的 `data_source_credentials` 私有表，页面和 API 只返回掩码。

刷新真实数据：

```bash
curl -X POST http://127.0.0.1:8100/api/data/refresh \
  -H 'Content-Type: application/json' \
  -d '{"provider":"tushare","scope":"real-data","account_id":"acct-demo-a"}'
```

刷新会默认处理本地股票池里的 A 股代码，把 `daily`/`daily_basic` 写入 `market_snapshots`，把 `fina_indicator`/`income` 写入 `financial_snapshots`。股票搜索和持仓价格会优先使用 `tushare-*` 缓存；没有真实缓存时继续回退到 mock 数据。

Tushare Pro 不同账号有接口频率限制。刷新服务会逐只股票返回错误列表，例如 `daily_basic` 超限时不会中断已成功写入的股票，下次等频率窗口恢复后再刷新即可。官方接口说明见 [Tushare Pro 文档](https://tushare.pro/document/2)。

## 当前开发进度

- Phase 0：静态交互 demo 已完成。
- Phase 1A：已加入 FastAPI + SQLite mock 后端。
- Phase 1A：已打通账户切换、账户级关注、账户级交易流水、共享分析缓存统计。
- Phase 1B：已把后端拆成 `db/accounts/analysis/portfolio/data_quality/schemas` 模块。
- Phase 1B：已实现后端持仓收益计算、`account_positions_cache`、portfolio API 和 mock 价格刷新。
- Phase 1C：已加入 iPhone/PWA app shell 和移动端底部导航。
- Phase 1C：已支持局域网预览方式，iPhone 可通过 Mac IP + `8101` 打开。
- Phase 1D：已生成 Mac mock `.app`、Mac 离线 Universal mock `.app` 和 iPhone mock SwiftUI/WKWebView 源码包。
- Phase 1D：已把 Mac mock 包最低系统版本降到 macOS 12.0，并同时支持 Apple Silicon 与 Intel。
- Phase 1E：已加入 mock provider、共享快照表、数据源配置表、股票搜索/筛选/记忆 API、网页版设置页和回测平台。
- Phase 1F：已接入 Tushare Pro A 股行情/财务缓存，支持账户级 token 配置、真实刷新、搜索展示和持仓价格覆盖。
- Phase 1G：已接入历史数据仓库、BaoStock 回刷、数据库筛选、数据库回测和 `debug_warehouse` 诊断脚本；BaoStock 全量回刷改为后台长任务。
- Phase 1H：已接入问财基本面画像本地库、慢速续跑脚本、连续 403 断路保护，并在单股详情右侧以 tab 展示基本面画像。
- 当前优先：先开发网页版；macOS 和 iPhoneOS 打包暂缓。
- 待做：持久化任务队列/断点续跑、DuckDB/Parquet 大批量历史数据层、真实 LLM 分析服务、Developer ID 签名/公证、Mac App Store/iOS App Store 上架流程暂未接入。

## 后续真实版本方向

1. 用 FastAPI + SQLite/DuckDB 做本地后端和缓存。
2. 用 BaoStock/Tushare/AKShare 做原型历史数据，生产环境补齐授权行情供应商和更稳定的批量任务队列。
3. 官方公告优先接入 CNINFO、上交所/深交所、HKEXnews、SEC EDGAR。当前已新增 `/api/filings/search` 和 `scripts/fetch_filings.py`，可查询 CNINFO、上交所、深交所、HKEXnews 的公开公告入口。
4. 每条 AI 结论必须绑定数据快照、来源等级和反思记录。
5. Mac 安装版建议用 Tauri 或原生壳包装前端和后端 sidecar；正式分发时必须做签名、公证和自动更新。
6. iPhone 版短期建议先走 PWA/移动 Web；正式上架时改成 SwiftUI、React Native 或 Tauri iOS，并调用云端 API。

## 工程 TODO

下一阶段的后端、数据库、API key、自动化、多账户和打包计划见：

- [docs/engineering-todo.md](docs/engineering-todo.md)
- [docs/handoff.md](docs/handoff.md)
- [docs/warehouse-schema.md](docs/warehouse-schema.md)
- [docs/iwencai-profile.README.md](docs/iwencai-profile.README.md)
- [scripts/debug_warehouse.README.md](scripts/debug_warehouse.README.md)
