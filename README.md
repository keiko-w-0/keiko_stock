# Keiko Stock AI

本地安装型选股研究台原型。当前版本使用 mock 数据，重点验证产品结构：每日观察名单、关注池买卖复核、手动输入股票分析、数据实时性检测、证据链、最多 3 轮反思，以及“共享分析 + 多账户私有持仓/关注”的软件边界。

> 这是研究辅助软件原型，不构成投资建议。真实交易前必须接入授权数据源，并由用户独立复核。

## 立即预览

推荐使用本地 Mock 后端启动，这样可以验证多账户、SQLite 种子库和共享分析缓存：

```bash
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8100
```

然后访问 `http://localhost:8100`。

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
- `requirements.txt`：后端运行依赖。
- `docs/research-report.md`：数据源、资讯源、真实性判断、情绪面、AI 反思和落地路线报告。
- `docs/engineering-todo.md`：后端、数据库、API key、自动化、多账户和打包 TODO。
- `docs/handoff.md`：换电脑或开启新 Codex 会话时的交接说明。

## 已实现的交互原型

- 股票池过滤：支持按市场、流动性、估值质量、技术催化、证据风险组合筛选。
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
- 待做：真实数据 provider、真实数据库迁移、LLM 分析服务、Developer ID 签名/公证、Mac App Store/iOS App Store 上架流程暂未接入。

## 后续真实版本方向

1. 用 FastAPI + SQLite/DuckDB 做本地后端和缓存。
2. 用 Tushare/AkShare 做原型数据，生产环境补齐授权行情供应商。
3. 官方公告优先接入 CNINFO、上交所/深交所、HKEXnews、SEC EDGAR。
4. 每条 AI 结论必须绑定数据快照、来源等级和反思记录。
5. Mac 安装版建议用 Tauri 或原生壳包装前端和后端 sidecar；正式分发时必须做签名、公证和自动更新。
6. iPhone 版短期建议先走 PWA/移动 Web；正式上架时改成 SwiftUI、React Native 或 Tauri iOS，并调用云端 API。

## 工程 TODO

下一阶段的后端、数据库、API key、自动化、多账户和打包计划见：

- [docs/engineering-todo.md](/Users/admin/Documents/keiko_stock/docs/engineering-todo.md)
- [docs/handoff.md](/Users/admin/Documents/keiko_stock/docs/handoff.md)
