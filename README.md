# 聚宝盆

本地安装型选股研究台原型。当前版本使用 mock 数据，重点验证产品结构：每日观察名单、关注池买卖复核、手动输入股票分析、数据实时性检测、证据链、最多 3 轮反思，以及“共享分析 + 多账户私有持仓/关注”的软件边界。

> 这是研究辅助软件原型，不构成投资建议。真实交易前必须接入授权数据源，并由用户独立复核。

## 立即预览

推荐使用本地 Mock 后端启动，这样可以验证多账户、SQLite 种子库和共享分析缓存：

```bash
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8100
```

然后访问 `http://localhost:8100`。

如果要试 AKShare 真实数据模块，先安装后端依赖：

```bash
python3 -m pip install -r requirements.txt
```

当前 AKShare 模块不会替代主界面的 mock 分析链路，而是在设置页提供“AKShare 数据探索”面板，并暴露独立 API 方便查看能拉到哪些字段：

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

这个包会启动本地 FastAPI mock 后端，再在 app 窗口中打开页面。SQLite 会写入 `~/Library/Application Support/Keiko Stock AI/data`，不会写进 `.app` 资源目录。它更适合本机开发调试；如果发给别人，对方机器仍可能缺少 Python 或 Python 依赖。

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
- `app.js`：mock 股票数据、评分、搜索分析、数据健康和反思渲染逻辑。
- `manifest.webmanifest`：iPhone/PWA 安装入口元数据。
- `service-worker.js`：PWA app shell 缓存，API 请求仍走实时后端。
- `assets/app-icon.svg`：当前原型图标，后续打包阶段替换为正式 PNG/icon set。
- `packaging/mac/`：Mac WKWebView app 壳和 Info.plist。
- `ios/KeikoStockAI/`：iPhone SwiftUI/WKWebView mock app 源码壳。
- `scripts/package_mac_app.sh`：生成 Mac `.app` 和 zip。
- `scripts/package_mac_offline_app.sh`：生成不依赖 Python 后端的 Mac 离线 mock `.app` 和 zip。
- `scripts/package_ios_mock_source.sh`：生成 iPhone mock 源码包。
- `backend/app.py`：FastAPI mock 后端，提供账户、关注、交易、共享分析和异动分析 API。
- `backend/accounts.py`：账户私有关注和交易流水服务。
- `backend/analysis.py`：共享单股分析、共享异动分析和共享缓存统计。
- `backend/portfolio.py`：账户级持仓、收益率、盈利金额和持仓缓存计算。
- `backend/data_quality.py`：Mock 数据健康检查和刷新任务响应。
- `backend/db.py`：SQLite 连接、schema 初始化和种子库写入。
- `backend/seed_data.py`：SQLite 种子数据，模拟多账户与共享分析缓存。
- `backend/providers/`：Phase 1E mock provider，生成行情、财务、新闻、claim 和因子快照。
- `backend/providers/tushare.py`：Tushare Pro HTTP 客户端，按官方 Pro 协议调用 `stock_basic`、`daily`、`daily_basic`、`income`、`fina_indicator`。
- `backend/tushare_service.py`：Tushare A 股刷新服务，把真实行情和财务快照写入 SQLite 缓存。
- `backend/providers/filings.py`：CNINFO、上交所、深交所、HKEXnews 公告/披露查询适配器。
- `backend/filings.py`：公告来源选择、日期校验和统一返回结构。
- `backend/data_sources.py`：网页版数据源配置服务，控制哪些 mock 来源进入分析。
- `backend/stocks.py`：股票搜索、筛选和记忆 API 的 mock 服务。
- `backend/backtesting.py`：回测平台 mock 研究引擎，输出收益曲线、回撤、调仓记录和研究限制。
- `scripts/fetch_filings.py`：命令行查询官方公告/披露数据。
- `requirements.txt`：后端运行依赖。
- `docs/official-filings-data.md`：真实公告数据源接入说明和 API/CLI 示例。
- `docs/research-report.md`：数据源、资讯源、真实性判断、情绪面、AI 反思和落地路线报告。
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
- Mock 后端：页面启动时优先读取 `/api/bootstrap`；后端不可用时保持本地 fallback。
- 多账户原型：账户 A/B 可切换；股票分析、异动分析、记忆共享；关注列表和持仓流水按账户隔离。
- 后端持仓计算：`/api/accounts/{account_id}/portfolio` 返回账户级持仓、盈亏、收益率和币种汇总。
- 后端刷新盈利：点击“刷新股价”会调用 `/api/data/refresh`，用 mock 最新价重算 portfolio。
- iPhone/PWA 原型：支持 mobile web app meta、manifest、service worker 和手机底部导航。
- 网页版 tab：左侧导览切换后只显示当前 tab 内容，不再把后续页面连续接在下面。
- 设置页：按 A/HK/US 市场配置行情、财务、公告、新闻情绪 mock 数据源；未启用或未配置的数据源不会进入后续 mock 分析。
- 回测平台：支持选择策略模板、市场、区间、持仓数、调仓频率、手续费和滑点，生成 mock 研究回测报告。
- Tushare Pro：支持账户级 token 配置，刷新 A 股行情/每日指标/利润表/财务指标，搜索和持仓价格优先使用 Tushare 缓存。

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
- 当前优先：先开发网页版；macOS 和 iPhoneOS 打包暂缓。
- 待做：真实数据 provider、真实数据库迁移、LLM 分析服务、Developer ID 签名/公证、Mac App Store/iOS App Store 上架流程暂未接入。

## 后续真实版本方向

1. 用 FastAPI + SQLite/DuckDB 做本地后端和缓存。
2. 用 Tushare/AkShare 做原型数据，生产环境补齐授权行情供应商。
3. 官方公告优先接入 CNINFO、上交所/深交所、HKEXnews、SEC EDGAR。当前已新增 `/api/filings/search` 和 `scripts/fetch_filings.py`，可查询 CNINFO、上交所、深交所、HKEXnews 的公开公告入口。
4. 每条 AI 结论必须绑定数据快照、来源等级和反思记录。
5. Mac 安装版建议用 Tauri 或原生壳包装前端和后端 sidecar；正式分发时必须做签名、公证和自动更新。
6. iPhone 版短期建议先走 PWA/移动 Web；正式上架时改成 SwiftUI、React Native 或 Tauri iOS，并调用云端 API。

## 工程 TODO

下一阶段的后端、数据库、API key、自动化、多账户和打包计划见：

- [docs/engineering-todo.md](/Users/admin/Documents/keiko_stock/docs/engineering-todo.md)
- [docs/handoff.md](/Users/admin/Documents/keiko_stock/docs/handoff.md)
