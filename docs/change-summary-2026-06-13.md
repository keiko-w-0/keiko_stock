# 2026-06-12 晚至 2026-06-13 变更总结

更新时间：2026-06-13
时区：Asia/Shanghai

本文档汇总 2026-06-12 晚上至 2026-06-13 今天在本仓库中的改动，并记录代码冲突检查结果。

## 范围说明

- 已提交变更：`c27d456 情绪面分析`，提交时间 `2026-06-13 00:47:33 +0800`，当前 `main` 与 `origin/main` 对齐。
- 未提交变更：工作区仍有一批源码、文档、脚本和日志改动，尚未 commit。
- 本文档本身是本次整理新增的文档文件。

## 昨晚已提交：情绪面分析主线

提交 `c27d456` 是昨晚到今天凌晨落地的主干功能，核心是把“情绪面分析”从概念推进到后端、数据库、脚本、前端展示和交接文档都能串起来的版本。

主要改动：

- 新增情绪分析核心：`backend/sentiment.py`，覆盖公告/新闻/财报、社区讨论、交易型情绪三类来源，并写入 `sentiment_evidence` 与 `sentiment_snapshots`。
- 新增社区数据源：`backend/providers/community.py`，接入东方财富股吧抓取与解析。
- 新增 API 和 schema：`backend/app.py`、`backend/schemas.py` 增加情绪状态、股票情绪、情绪刷新、社区抓取等接口输入。
- 扩展数据库：`backend/db.py` 增加社区帖子、情绪证据、情绪快照等数据结构和索引。
- 前端增加情绪面展示：`app.js`、`styles.css`、`index.html` 展示综合情绪、分项情绪、证据卡片、刷新状态和对应样式。
- 单股详情接入刷新链路：`backend/history.py`、`backend/stock_detail.py` 在详情刷新时联动行情、财务、公告和情绪刷新。
- 回测与历史仓库增强：`backend/backtesting.py`、`backend/history.py`、`scripts/test_warehouse_guards.py` 等继续强化数据库优先回测、仓库保护测试和后台刷新可靠性。
- 新增运维脚本：包括 A 股公告补刷、ingestion watchdog、情绪刷新脚本，以及 macOS LaunchAgent plist。
- 更新文档：`README.md`、`docs/handoff.md`、`docs/sentiment.README.md`、仓库相关 README 说明新增的数据源、定时任务和情绪面机制。
- 新增本地工具：`tools/ngrok` 和 `tools/ngrok.zip` 用于临时公网预览。

提交涉及 44 个文件，约 `9258` 行新增、`470` 行删除。

## 今天未提交：社区情绪 agent、日汇总和回测面板

今天工作区未提交改动集中在情绪面继续深化，尤其是“股吧半小时 agent + 日级汇总 + 回测展示”。

### 后端接口和输入模型

- `backend/app.py`
  - 新增 `GET /api/sentiment/community/daily/{symbol}`，读取某只股票的社区情绪日汇总。
  - 新增 `POST /api/sentiment/community/cycle`，用于触发一轮社区情绪 agent：抓股吧、刷新短窗口 K 线、按需补公告、跑情绪分析、生成日汇总和清理过期明细。
- `backend/schemas.py`
  - 新增 `CommunitySentimentCycleInput`，支持配置 `symbols`、`use_llm`、`community_limit`、`evidence_limit`、`analysis_days`、`retention_days`、`refresh_market`、`refresh_filings`、`market_days`。

### 数据库和仓库口径

- `backend/db.py`
  - 新增 `community_sentiment_daily` 表，用于永久保存社区日级聚合结果。
  - 新增 `idx_community_sentiment_daily_symbol_date` 索引，支持按股票和日期快速读取。
- `backend/history.py`
  - `warehouse_summary` 增加 `community_sentiment_daily` 计数。
  - 单股情绪快照新鲜度从 6 小时收紧到 30 分钟，并按当前 `method_version` 判断，避免 prompt 升级后误用旧快照。
  - A 股公告补刷后新增按标题去重：同一股票、标题规范化一致的公告只保留优先级更高的一条，同时删除被去重公告对应的情绪 evidence。
  - ingestion counts 里增加公告去重统计，方便从任务结果看删除了多少重复公告和旧 evidence。

### 情绪算法和 LLM 调用

- `backend/sentiment.py`
  - 升级 prompt/method version 到 `prompt-20260613-guba-v4` / `sentiment-v4-*`。
  - 社区评论改为五档分类：正面、偏正面、中性、偏负面、负面，再映射为 `+2/+1/0/-1/-2`。
  - 新增社区日汇总：统计当日分析条数、正/中/负数量、关键词、均分、标签、置信度和总评。
  - 新增 `run_community_sentiment_cycle`，串起社区抓取、短窗口行情刷新、公告缺口刷新、情绪分析、日汇总生成和 3 天明细清理。
  - 增强 LLM 批处理：社区 batch 默认 10 条，失败后可按 5 条拆分重试，默认并发 2，公告/新闻和社区分别有超时配置。
  - 增加 LLM 缓存和性能统计：记录请求数、发送条数、缓存命中、fallback、耗时、慢步骤等。
  - 社区原文和单条 evidence 默认只保留 3 天；`community_sentiment_daily` 永久保留，不存单条原文。
- `backend/providers/community.py`
  - 新增股吧详情正文 HTML 解析器，尽量把标题之外的正文也纳入社区情绪分析。

### 回测和前端展示

- `backend/backtesting.py`
  - `/api/backtests/run` 返回新增 `sentiment_panels`。
  - 数据库回测会附带两个面板：`daily_kline.rows` 展示社区日情绪与对齐 K 线，`realtime.rows` 展示最新 K 线、最新情绪快照和当天社区抓取/分析状态。
  - fallback/mock 回测返回空情绪面板，避免前端判断缺字段。
- `app.js`
  - 回测页新增“股吧日情绪 × K线”和“实时变化”两个情绪面板。
  - 情绪详情增加五档社区分类、社区均分、LLM 失败标记、快照年龄、刷新耗时、分项权重和更多证据解释。
  - 单股详情和情绪刷新增加进行中 banner、elapsed timer，并在账户/Tab 切换后自动触发回测刷新。
  - 筛选规则增加问号 tooltip，解释每条规则逻辑。
- `styles.css`
  - 新增刷新 banner、耗时状态、社区情绪条、LLM 失败卡片、回测情绪面板、规则 tooltip 等样式。
- `index.html`、`service-worker.js`
  - 缓存版本更新到 `20260613-community-card-v1` / `jubao-pen-community-card-v1`，确保浏览器拿到最新前端资源。

### 脚本和定时任务

- 新增 `scripts/run_community_sentiment_agent.py`
  - 半小时 agent 入口，支持 `--once`、循环模式、社区抓取数量、evidence 数量、保留天数、K 线刷新天数、是否使用 LLM、JSON 输出等参数。
- 新增 `scripts/com.keiko.community-sentiment-agent.plist`
  - macOS LaunchAgent 配置，`StartInterval=1800`，每 30 分钟运行一次 `--once`。
  - 日志目标是 `logs/community-sentiment-agent.log` 和 `logs/community-sentiment-agent.err.log`。
- 新增 `scripts/debug_sentiment_score.py`
  - 只读情绪 evidence 调试脚本，可按 source row 或 symbol 复算快照拆分，查看 LLM 结果、权重、时间衰减和 composite 贡献。
- 修改 `scripts/run_a_share_filings_backfill.py`、`scripts/crawl_community_sentiment.py`、`scripts/run_sentiment_refresh.py`、`scripts/test_warehouse_guards.py`
  - 补齐公告去重、社区刷新、情绪刷新参数和仓库保护测试。

### 文档和日志

- `docs/sentiment.README.md`
  - 补充社区五档分类、GLM prompt 口径、缓存、批处理、半小时 agent、保留策略、macOS 定时、日级汇总和回测面板说明。
- `logs/*.log`
  - 多个夜间任务和本地测试日志被刷新，包括 BaoStock 日线、BaoStock 财务、A 股公告、ingestion watchdog、uvicorn/codex 测试日志。
  - 这些属于运行记录，不是业务源码；提交前建议确认是否需要纳入版本库。

## 当前工作区文件清单

已修改但未提交的源码/文档/配置：

- `app.js`
- `backend/app.py`
- `backend/backtesting.py`
- `backend/db.py`
- `backend/history.py`
- `backend/providers/community.py`
- `backend/schemas.py`
- `backend/sentiment.py`
- `backend/stock_detail.py`
- `docs/sentiment.README.md`
- `index.html`
- `scripts/crawl_community_sentiment.py`
- `scripts/run_a_share_filings_backfill.py`
- `scripts/run_sentiment_refresh.py`
- `scripts/test_warehouse_guards.py`
- `service-worker.js`
- `styles.css`

已修改但更像运行产物的日志：

- `logs/a-share-filings-nightly.log`
- `logs/baostock-financial-nightly.log`
- `logs/baostock-nightly.err.log`
- `logs/baostock-nightly.log`
- `logs/ingestion-watchdog.err.log`
- `logs/ingestion-watchdog.log`

新增但未跟踪：

- `scripts/com.keiko.community-sentiment-agent.plist`
- `scripts/debug_sentiment_score.py`
- `scripts/run_community_sentiment_agent.py`
- `logs/codex-nohup-test.log`
- `logs/codex-uvicorn-8100-test.log`
- `logs/codex-uvicorn-8100.err.log`
- `logs/codex-uvicorn-8100.log`
- `docs/change-summary-2026-06-13.md`

## 冲突和检查结果

已完成检查：

- `git status --short --branch`：当前分支 `main...origin/main`，没有显示未合并状态。
- `git fetch origin` 后执行 `git rev-list --left-right --count main...origin/main`：结果为 `0 0`，本地 `main` 与远端跟踪分支没有 ahead/behind 分叉。
- `git diff --name-only --diff-filter=U`：无输出，没有 Git unmerged 文件。
- `git ls-files -u`：无输出，没有 index 冲突条目。
- `rg -n "^(<<<<<<<|=======|>>>>>>>)" .`：无输出，没有残留合并冲突标记。
- `git diff --check`：通过，没有 whitespace error 或 conflict marker 报错。
- `python3 -m py_compile ...`：已对本次涉及的后端 Python 文件和脚本做语法检查，通过。
- 使用 Codex bundled Node 执行：
  - `/Users/wangwenhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check app.js`
  - `/Users/wangwenhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check service-worker.js`
  两项均通过。
- `python3 scripts/test_warehouse_guards.py`：通过，输出 `warehouse guard tests ok`。

结论：截至本次检查，代码没有 Git 合并冲突、没有残留冲突标记，Python/JS 语法检查通过，仓库保护测试通过。

## 提交前建议

- 日志文件变更量很大，提交前建议决定哪些日志需要保留，哪些只是本地运行记录。
- `tools/ngrok` 和 `tools/ngrok.zip` 已在昨晚提交中进入仓库；如后续不希望提交二进制工具，建议单独讨论是否迁出版本库。
- 社区情绪 agent plist 里包含本机绝对路径 `/Users/wangwenhui/Documents/keiko_stock` 和 Python 路径；如果要给别人使用，需要改成安装脚本或模板。
- 情绪分析 prompt/method version 已升级，旧缓存不会命中新版本；这是预期行为。
