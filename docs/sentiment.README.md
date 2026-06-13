三类情绪来源
1. 公告 / 新闻 / 基本面（filing_news）
从以下表拉候选数据（默认近 30 天，排除 mock 源）：

filings_history — 公告（只读 SQL 缓存，不在情绪分析阶段重复请求公告源）
company_reports_history — 公司报告
news_items — 新闻
financial_metrics_history — 财务指标（转成「基本面快照」）
文本默认按批次调用 GLM 做情绪分类、置信度、影响周期和情绪面关键词提取，最后写入 sentiment_evidence；只有未配置 LLM 或请求失败时才写入中性兜底结果。公告/新闻/财报文本会按 source_id + method_version + provider/model 复用 30 分钟内的 LLM 缓存，避免同一批公告反复分析。method_version 内包含 prompt version，prompt 一改就升版本，旧评论/公告缓存不再命中，必须重新 infer。

2. 社区讨论（community）
从 community_posts 读帖子（标题 + 正文），默认分析上限 120 条。可选先爬取东方财富股吧（crawl_community_for_symbols → providers/community.py），默认每只股票抓 120 条。
评论会按 `community_posts` 的 source_id + method_version + provider/model 复用缓存；命中的评论不再重复发送给 GLM。股吧讨论使用社区专用 prompt：判断“对股票/股价后续表现”的情绪，不把发帖人的遗憾、谨慎或黑话直接当成股票利空。默认每个 GLM prompt 放 10 条评论，每条带稳定 `id`，要求 GLM 按原顺序返回同样的 `id`；解析时优先按 `id` 合并结果，避免顺序错位。社区 prompt 不让 GLM 返回数值分，只返回 `sentiment_class` 五档：正面、偏正面、中性、偏负面、负面；后端映射为 +2、+1、0、-1、-2，社区类分数就是所有评论分类分的算术平均。
3. 交易型情绪（market）
用 preferred_daily_bars 取日 K，算一条「交易型情绪」证据，不依赖文本。主要因子包括：

1/5/20 日涨跌幅加权
成交额/量比相对 20 日均值
窗口内涨跌停天数
最大回撤、高换手 + 下跌
打分机制
GLM 文本分类
use_llm 默认 True。配置了 GLM API Key 时，公告/新闻/财报文本和社区文本会批量发送给 GLM，要求返回：

公告/新闻/财报要求返回 sentiment_score、confidence、category、impact_horizon、keywords、reason。
社区评论要求返回 sentiment_class、confidence、keywords，不返回 sentiment_score。

keywords 是 GLM 提取的情绪面关键词或短语，不再使用本地关键词规则生成 `rule_matches`。社区 prompt 明确：
卖飞/卖早/踏空/后悔卖了通常是股票强势导致的遗憾，按偏正面理解；
可以了/飞/起飞/指标线还没跟上通常是满意或上涨强势，按偏正面理解；
甩下车/洗盘/震仓/散户下车通常是强势上涨或洗盘叙事，不自动归为风险提示。
公告/新闻/财报 sentiment_score clamp 到 [-100, 100]，并映射标签。社区评论按五档分类映射到 [-2, 2]：

分类	评论分
正面
+2
偏正面
+1
中性
0
偏负面
-1
负面
-2

分数区间	标签
≥ 35
positive
≤ -35
negative
≥ 12
mild_positive
≤ -12
mild_negative
其他
neutral
基本面在 GLM 不可用时会用结构化财务指标生成兜底分；GLM 可用时以 GLM 分类结果为准。

LLM 优先级：GLM > DeepSeek（读 .env 或环境变量）。公告/新闻 batch 大小默认 24，可用 `KEIKO_SENTIMENT_LLM_BATCH_SIZE` 调整；社区评论 batch 默认 10，可用 `KEIKO_SENTIMENT_COMMUNITY_LLM_BATCH_SIZE` 调整；社区 prompt 超时时会按默认 5 条拆分重试，可用 `KEIKO_SENTIMENT_COMMUNITY_LLM_RETRY_BATCH_SIZE` 调整；默认最多 2 个 batch 并发，可用 `KEIKO_SENTIMENT_LLM_CONCURRENCY` 调整，避免一次开太多请求触发限流；公告/新闻 batch 默认 25 秒超时，可用 `KEIKO_SENTIMENT_LLM_TIMEOUT` 调整；社区 prompt 默认 40 秒超时，可用 `KEIKO_SENTIMENT_COMMUNITY_LLM_TIMEOUT` 调整。
刷新结果的 `performance` 会返回爬虫、公告/社区/交易分析、快照聚合分步耗时，以及 LLM 请求数、实际发送条数、缓存命中和 LLM 总耗时，用来判断慢在抓 120 条社区数据还是 GLM API。

聚合：综合情绪快照
upsert_sentiment_snapshot 把窗口内所有 evidence 按类型分组；公告/新闻和交易按带时间衰减的加权平均（weighted_score + recency_weight），社区按所有评论分类分的算术平均，再合成 composite：

类型	权重
filing_news
40%
community
25%
market
35%
若某类没有数据，权重会按比例重新分配。快照字段包括分项分、composite_score、sentiment_label、confidence、各源数量等。

辅助能力
sentiment_payload：读最新 snapshot + 分组 evidence，给前端/API 详情页
sentiment_status：表行数、最近 20 只股票的快照时间、LLM 配置（密钥打码）
history.py 集成：详情页刷新会调用 refresh_symbol_sentiment；若 30 分钟内已有快照，则跳过 GLM 重算，避免重复刷新同一批结果
工具函数：symbol 规范化、日期窗口、JSON 解析、分数 clamp 等

股吧半小时 agent
`scripts/run_community_sentiment_agent.py` 是社区情绪面的半小时 agent 入口：

```bash
python3 scripts/run_community_sentiment_agent.py --once 600519.SH
python3 scripts/run_community_sentiment_agent.py 600519.SH 000001.SZ
```

默认每轮对每只股票抓 120 条东方财富股吧评论，刷新短窗口 K 线，公告只在 `filing_refresh_state` 判断有缺口时拉取，财务不在这个轮次重复刷新。默认使用 GLM/DeepSeek；`--no-llm` 只用于本地排查。

去重口径：

- `community_posts` 对 `(source, symbol, source_post_id)` 做唯一约束，同一评论重复抓取只更新同一行。
- `sentiment_evidence` 对 `(sentiment_type, source_table, source_id, method_version)` 做唯一约束，同一评论不会重复插入分析结果。
- 社区评论的 LLM 缓存按 `source_id + method_version + provider/model` 复用到明细被清理为止；公告/新闻仍保留 30 分钟缓存。

保留口径：

- 单条股吧原文和单条分析结论保留 3 天，`cleanup_expired_community_sentiment` 会删除过期 `community_posts` 与对应 `sentiment_evidence`。
- `community_sentiment_daily` 是永久日汇总，只保存计数、分数、关键词统计和 LLM 总评，不保存评论原文。

macOS 定时：

`scripts/com.keiko.community-sentiment-agent.plist` 使用 `StartInterval=1800`，每 30 分钟运行一次 `--once`。日志写入：

- `logs/community-sentiment-agent.log`
- `logs/community-sentiment-agent.err.log`

日级汇总
`refresh_community_daily_summaries` 按 `analyzed_at` 的日期汇总当天去重后的社区 evidence，写入 `community_sentiment_daily`：

- `analyzed_count`
- `positive_count / negative_count / neutral_count`
- `sentiment_score / sentiment_label / confidence`
- `keyword_counts_json`
- `conclusion`

日汇总的 LLM 总评只基于聚合统计，不引用或保存单条评论原文。

回测页面板
`/api/backtests/run` 返回 `sentiment_panels`：

- `daily_kline.rows`：社区日汇总 + 对齐的最近 K 线涨跌。
- `realtime.rows`：最新 K 线、最新 sentiment_snapshot、当天社区抓取/分析状态。

前端回测平台会展示“股吧日情绪 × K线”和“实时变化”两个面板。
设计特点小结
可解释：每条 evidence 存 keywords_json、evidence_json（行情明细、GLM reason）
可增量：upsert + (sentiment_type, source_table, source_id, method_version) 唯一键，重复刷新会更新而非重复插入
默认 GLM 优先：不依赖 LLM 也能跑，但配置 GLM 后刷新会使用 GLM 结果
A 股语境：关键词、涨跌停阈值（9.4%）、股吧爬虫都针对 A 股场景
如果你希望，我可以继续帮你对照前端或 stock_detail 看 composite 分具体在哪里展示，或者 walk through 某只股票的 refresh 实际 SQL 读写路径。
