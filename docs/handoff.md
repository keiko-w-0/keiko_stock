# Keiko Stock AI Handoff

更新时间：2026-06-05

这份文档用于换电脑或开启新 Codex 会话时快速接手。新会话优先阅读：

1. `README.md`
2. `docs/engineering-todo.md`
3. `docs/research-report.md`
4. 本文件

## 当前产品状态

当前是 mock 数据阶段，不接真实行情、不调用真实 LLM、不接真实 API key。目标是先把产品交互、数据库边界、多账户、记忆管理和打包路线跑通。

已完成：

- 静态前端：`index.html`、`styles.css`、`app.js`
- FastAPI mock 后端：`backend/app.py`
- SQLite schema 和种子数据：`backend/db.py`、`backend/seed_data.py`
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

这个包会启动本地 FastAPI mock 后端，更适合本机调试；发给别人时可能受 Python 环境影响。

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

用户明确说“先不用真实数据”。所以下一阶段仍以 mock provider 为主，不申请真实 API key，不接真实行情。

建议从 Phase 1E 开始：

1. 建立 provider 抽象，但先实现 `MockMarketProvider`、`MockNewsProvider`、`MockFinancialProvider`。
2. 补齐 mock 版数据库表：`market_snapshots`、`financial_snapshots`、`news_items`、`claims`、`factor_runs`。
3. 把当前 `app.js` 中的大块 mock 数据逐步迁到后端 seed/provider，前端只调用 API。
4. 增加 `GET /stocks/search`、`POST /screeners/run`、`GET /memory/stocks/{symbol}` 的 mock API。
5. 给关键流程加测试：bootstrap、账户隔离、portfolio 计算、刷新价格、共享分析缓存、异动分析。
6. 再考虑把静态前端迁移到 React + TypeScript + Vite。

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
