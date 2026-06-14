# 情绪面（Sentiment）说明

当前 prompt 版本：`prompt-20260613-guba-v6`（method_version 内含该版本号，prompt 变更后旧 LLM 缓存不再命中）。

---

## 三类情绪来源

### 1. 公告 / 新闻 / 基本面（`filing_news`）

从以下表拉候选数据（默认近 30 天，排除 mock 源）：

| 表 | 内容 |
|---|---|
| `filings_history` | 公告（只读 SQL 缓存，情绪阶段不重复请求公告源） |
| `company_reports_history` | 公司报告 |
| `news_items` | 新闻 |
| `financial_metrics_history` | 财务指标（转成「基本面快照」） |

文本默认按批次调用 GLM 做情绪分类、置信度、影响周期和情绪面关键词提取，最后写入 `sentiment_evidence`；只有未配置 LLM 或请求失败时才写入中性兜底结果。

公告/新闻/财报文本会按 `source_id + method_version + provider/model` 复用 **30 分钟内** 的 LLM 缓存。社区评论缓存按同样键复用，直到明细被清理。

---

### 2. 社区讨论（`community`）

从 `community_posts` 读帖子（标题 + 正文），默认分析上限 **120 条**。刷新前可先爬取社区数据（`crawl_community_for_symbols` → `backend/providers/community.py`）。

#### 数据源（默认 `source=all`）

| source | 说明 | 模块 |
|---|---|---|
| `eastmoney_guba` | 东方财富股吧 | HTTP 抓取列表页 + 详情页 |
| `xueqiu` | 雪球个股讨论区 | HTTP 优先；WAF 拦截时 DrissionPage 浏览器内 `fetch` |
| `all` | 上述两者合并 | 默认；单源失败记入 `errors`，不拖垮整轮 |

`community_posts` 唯一键：`(source, symbol, source_post_id)`。同一评论重复抓取只更新同一行。

#### GLM 社区 prompt 要点

- 判断「对**目标股票 / 股价后续表现**」的情绪，不把发帖人的遗憾、谨慎或黑话直接当成股票利空。
- 每条评论附带 **股票上下文**（见下文「评论上下文」），必须结合 `stock_name`、`current_price`、`change_pct` 理解，勿把评论里提到的其他股票误当成目标股。
- 默认每个 GLM prompt **10 条**评论，带稳定 `id`；解析时按 `id` 合并，避免顺序错位。
- 社区评论由 GLM 同时返回 **`sentiment_score`（-100～100）** 与 **`sentiment_class`（正面/偏正面/中性/偏负面/负面）**；今日社区分为所有评论分数的**算术平均**，五档计数来自 LLM 的 `sentiment_class`。

常见 A 股语境（prompt 内已说明）：

- 卖飞 / 卖早 / 踏空 / 后悔卖了 → 通常是强势导致的遗憾，偏正面
- 可以了 / 飞 / 起飞 → 满意或上涨强势，偏正面
- 甩下车 / 洗盘 / 震仓 → 强势或洗盘叙事，不自动归为利空

---

### 3. 交易型情绪（`market`）

用 `preferred_daily_bars` 取日 K，算一条「交易型情绪」证据，不依赖文本。主要因子：1/5/20 日涨跌幅加权、成交额/量比、涨跌停天数、最大回撤、高换手 + 下跌等。

---

## 评论上下文（`community_stock_context`）

每条社区评论送入 GLM 前，会附带目标股上下文（`extra.stock_context`）：

| 字段 | 来源优先级 |
|---|---|
| `stock_name` | `symbols` 表 → 雪球 quote |
| `current_price` | `market_snapshots` → `daily_bars` → **雪球 quote 覆盖** |
| `change_pct` | `daily_bars` → **雪球 quote 覆盖** |
| `price_as_of` | 本地快照日期 / K 线日期 / 雪球 quote 时间戳 |
| `price_source` | 如 `akshare`、`baostock`、`xueqiu` |
| `market_status` | 雪球 quote（如「交易中」「休市」） |

**雪球实时价**：`backend/providers/xueqiu.py` 调用 `stock.xueqiu.com/v5/stock/quote.json`（需 `KEIKO_XUEQIU_COOKIE`）。成功时覆盖本地滞后价格，保证 prompt 里现价、涨跌幅与雪球一致。

---

## 雪球配置（`.env`）

```bash
# 行情接口必需；建议从浏览器 Network 复制整段 Cookie（不仅是 Application 面板）
KEIKO_XUEQIU_COOKIE=xq_a_token=...; xq_r_token=...; device_id=...

# 可选：仅 token 时也可尝试，但行情/HTTP 评论成功率较低
# KEIKO_XUEQIU_TOKEN=your_xq_a_token

# 评论抓取模式（默认 auto）
# auto   = HTTP（curl_cffi）失败后自动 DrissionPage 浏览器
# always = 始终用浏览器（慢但稳定）
# never  = 仅 HTTP（评论几乎必被 WAF 拦，不推荐）
KEIKO_XUEQIU_BROWSER=auto
```

| 能力 | 是否需要 Cookie | 是否需要 DrissionPage |
|---|---|---|
| 雪球实时 quote | **是** | 否 |
| 雪球评论 HTTP | 建议有 | 否（通常仍被 WAF 拦） |
| 雪球评论浏览器 fallback | 否（页面会话即可） | **是** |

依赖（见 `requirements.txt`）：`curl_cffi`、`DrissionPage`。修改 `.env` 后需**重启 backend**。

### 雪球评论技术说明

- 直接 Python/curl 调 `xueqiu.com/query/v1/symbol/search/status.json` 会被阿里云 WAF 拦截。
- 参考开源做法：[ForgeRSS](https://github.com/tmwgsicp/ForgeRSS)（DrissionPage 过 WAF）、[stock2money/xueqiu_crawler](https://github.com/stock2money/xueqiu_crawler)（首页 warm-up + cookie）。
- 本项目实现：DrissionPage headless 打开 `https://xueqiu.com/S/{SH600547}`，在页面内执行 `fetch(status.json)` 拿 JSON，单浏览器会话内分页；解析逻辑与 HTTP 路径共用。

### 快速验证

```bash
cd /Users/wangwenhui/Documents/keiko_stock

# 行情
python3 -c "
from dotenv import load_dotenv; load_dotenv('.env')
from backend.providers.xueqiu import fetch_xueqiu_quote
print(fetch_xueqiu_quote('600547.SH'))
"

# 雪球评论（约 12–15 秒，含浏览器启动）
python3 -c "
from backend.providers.community import fetch_xueqiu_posts
print(len(fetch_xueqiu_posts('600547.SH', limit=5)))
"

# 股吧 + 雪球
python3 -c "
from backend.providers.community import crawl_community_posts
r = crawl_community_posts('600547.SH', source='all', limit=5)
print(r['count'], r.get('errors'))
"
```

---

## 打分与标签

### GLM 文本分类

`use_llm` 默认 `True`。配置了 GLM API Key 时：

- 公告/新闻/财报：返回 `sentiment_score`、`confidence`、`category`、`impact_horizon`、`keywords`、`reason`
- 社区评论：返回 `sentiment_score`（-100～100）、`sentiment_class`（正面/偏正面/中性/偏负面/负面）、`confidence`、`keywords`

`keywords` 由 GLM 提取，不再用本地规则生成 `rule_matches`。

### 社区分数与分类

- 单条评论：LLM 同时输出 **sentiment_score** 与 **sentiment_class**，二者方向应一致。
- 今日社区均分：当天所有评论 `sentiment_score` 的算术平均。
- 五档统计：按 LLM 返回的 `sentiment_class` 计数（正/偏正/中/偏负/负）。

### 综合标签（公告/新闻等 -100~100）

| 分数区间 | 标签 |
|---|---|
| ≥ 35 | positive |
| ≤ -35 | negative |
| ≥ 12 | mild_positive |
| ≤ -12 | mild_negative |
| 其他 | neutral |

---

## LLM 与环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `KEIKO_SENTIMENT_LLM_BATCH_SIZE` | 24 | 公告/新闻 batch |
| `KEIKO_SENTIMENT_COMMUNITY_LLM_BATCH_SIZE` | 10 | 社区评论 batch |
| `KEIKO_SENTIMENT_COMMUNITY_LLM_RETRY_BATCH_SIZE` | 5 | 社区 prompt 超时拆分重试 |
| `KEIKO_SENTIMENT_LLM_CONCURRENCY` | 2 | batch 并发上限 |
| `KEIKO_SENTIMENT_LLM_TIMEOUT` | 25s | 公告/新闻 |
| `KEIKO_SENTIMENT_COMMUNITY_LLM_TIMEOUT` | 40s | 社区 |
| `KEIKO_SENTIMENT_ACCOUNT_ID` | `acct-admin` | 未传 symbols 时用该账户自选股 |
| `KEIKO_XUEQIU_COOKIE` | — | 雪球 Cookie |
| `KEIKO_XUEQIU_BROWSER` | `auto` | 雪球评论抓取模式 |

LLM 优先级：**GLM > DeepSeek**（读 `.env` 或环境变量）。

刷新结果的 `performance` 返回爬虫、分析、快照各步耗时，以及 LLM 请求数、缓存命中，便于判断慢在「抓 120 条社区」还是「GLM API」。

---

## 聚合：综合情绪快照

`upsert_sentiment_snapshot` 把窗口内 evidence 按类型分组；公告/新闻和交易用带时间衰减的加权平均，社区用评论分类分算术平均，再合成 composite：

| 类型 | 权重 |
|---|---|
| `filing_news` | 40% |
| `community` | 25% |
| `market` | 35% |

某类无数据时权重按比例重分配。快照含分项分、`composite_score`、`sentiment_label`、`confidence`、各源数量等。

---

## 刷新目标

`resolve_sentiment_target_symbols` 解析顺序：

1. 请求里显式传入的 `symbols`
2. **`acct-admin`（或 `KEIKO_SENTIMENT_ACCOUNT_ID`）关注列表**（`account_favorites`）
3. 仅当 `favorites_only=false`（或 agent 加 `--all-active`）时，才回退到近 30 日活跃股票（`recent_activity`）

**关注列表 agent 在每天 08:00–24:00（北京时间）期间每 30 分钟刷新一次**；窗口外与关注列表为空时跳过本轮。详情页手动点「刷新」仍只刷新当前股票，不受影响。

---

## 半小时社区 Agent

入口：`scripts/run_community_sentiment_agent.py`

```bash
# 单只股票试跑
python3 scripts/run_community_sentiment_agent.py --once 600519.SH

# 空参数 = 仅刷新 acct-admin 关注列表
python3 scripts/run_community_sentiment_agent.py --once

# 指定账户关注列表
python3 scripts/run_community_sentiment_agent.py --once --account-id acct-admin

# 旧行为：空参数时回退到近期活跃股票
python3 scripts/run_community_sentiment_agent.py --once --all-active
```

每轮默认：

- 每只股票爬 **120 条**社区帖（`source=all`：股吧 + 雪球）
- 短窗口 K 线刷新
- 公告仅在 `filing_refresh_state` 有缺口时拉取
- 使用 GLM/DeepSeek（`--no-llm` 仅本地排查）
- **单轮超时**默认 **1200 秒（20 分钟）**（`KEIKO_SENTIMENT_CYCLE_TIMEOUT_SECONDS`）；超时后停止剩余股票，已完成的快照保留，状态记 `timed_out=true`。手动长跑可用 `--cycle-timeout-seconds 0` 关闭限制。

macOS 定时：`scripts/com.keiko.community-sentiment-agent.plist`（`StartInterval=1800`，每 30 分钟触发；脚本在 08:00 前自动跳过）

每轮运行会写入 `ingestion_runs`（`provider=community-sentiment-agent`），`counts_json` 含严格用量统计：

- `inventory.community` / `inventory.filing_news`：`total`、`cache_hits`、`uncached`（满足 `total = cache_hits + uncached`）
- `llm_requests` / `llm_request_items`：实际打 GLM 的 HTTP 次数与条数（**不含**缓存命中）
- `cache_hits`：与 inventory 汇总一致
- `daily_conclusion_requests`：日汇总结论的 GLM 请求数
- `accounting.*`：三项对账布尔值，应为 `true`

查询最近 agent 运行：

```bash
python3 scripts/debug_warehouse.py sql "
select id, status, started_at, finished_at, json_extract(counts_json, '$.cache_hits') cache_hits,
       json_extract(counts_json, '$.llm_requests') llm_requests,
       json_extract(counts_json, '$.llm_request_items') llm_items
from ingestion_runs
where provider='community-sentiment-agent'
order by id desc limit 10"
```

或通过 API：`GET /api/sentiment/status` → `recent_agent_runs`。

```bash
# 加载（路径按本机项目目录改 WorkingDirectory / ProgramArguments）
launchctl load ~/Library/LaunchAgents/com.keiko.community-sentiment-agent.plist
```

日志：

- `logs/community-sentiment-agent.log`
- `logs/community-sentiment-agent.err.log`

---

## 去重、缓存与保留

**去重**

- `community_posts`：`(source, symbol, source_post_id)` 唯一
- `sentiment_evidence`：`(sentiment_type, source_table, source_id, method_version)` 唯一

**缓存**

- 社区评论 LLM：按 `source_id + method_version + provider/model` 复用至明细清理
- 公告/新闻 LLM：30 分钟 TTL

**保留**

- 单条股吧/雪球原文 + 单条分析结论：**3 天**（`cleanup_expired_community_sentiment`）
- `community_sentiment_daily`：永久日汇总（计数、分数、关键词、LLM 总评，**不含**评论原文）

---

## 日级汇总与回测

`refresh_community_daily_summaries` 按 `analyzed_at` 日期写入 `community_sentiment_daily`：`analyzed_count`、正/负/中性计数、`sentiment_score`、`keyword_counts_json`、`conclusion` 等。

`/api/backtests/run` 的 `sentiment_panels`：

- `daily_kline.rows`：社区日汇总 + 对齐 K 线
- `realtime.rows`：最新 K 线、最新 snapshot、当天社区抓取/分析状态

---

## 前端展示

- 详情页情绪区按钮：**「刷新」**（原「GLM情绪」）
- 涨跌配色遵循 A 股惯例：**涨/正面 = 红（`cn-up`），跌/负面 = 绿（`cn-down`）**（分数、标签、进度条、关键词高亮）

---

## 相关代码文件

| 文件 | 职责 |
|---|---|
| `backend/sentiment.py` | 刷新编排、LLM prompt、快照聚合、`community_stock_context` |
| `backend/providers/community.py` | 股吧 + 雪球爬取、入库 |
| `backend/providers/xueqiu.py` | 雪球 quote、HTTP/浏览器评论 API |
| `backend/accounts.py` | 自选股 `favorite_symbols_for_accounts` |
| `scripts/run_community_sentiment_agent.py` | 30 分钟 agent CLI |
| `app.js` / `styles.css` | 情绪 UI 与 A 股配色 |

---

## 单条评论调试

用生产 batch 路径（不是 `llm_analyze_text`）：

```python
from backend.db import get_db, init_db
from backend.sentiment import community_stock_context, analyze_text_item

init_db()
with get_db() as conn:
    ctx = community_stock_context(conn, "600489.SH")
    result = analyze_text_item(
        {
            "id": "debug-1",
            "symbol": "600489.SH",
            "title": "",
            "content": "这里贴一条股吧或雪球评论原文",
            "extra": {"stock_context": ctx},
        },
        use_llm=True,
        community=True,
    )
    print(result)
```

---

## 设计特点小结

- **可解释**：每条 evidence 存 `keywords_json`、`evidence_json`
- **可增量**：upsert + 唯一键，重复刷新更新而非重复插入
- **默认 GLM 优先**：无 LLM 可跑兜底，配置后使用 GLM 结果
- **A 股语境**：涨跌停阈值 9.4%、股吧/雪球双源、prompt 黑话规则
- **实时价补充**：雪球 quote 覆盖滞后本地价，提升评论情绪判断准确度
