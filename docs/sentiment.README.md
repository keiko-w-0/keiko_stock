三类情绪来源
1. 公告 / 新闻 / 基本面（filing_news）
从以下表拉候选数据（默认近 30 天，排除 mock 源）：

filings_history — 公告（只读 SQL 缓存，不在情绪分析阶段重复请求公告源）
company_reports_history — 公司报告
news_items — 新闻
financial_metrics_history — 财务指标（转成「基本面快照」）
文本先生成本地兜底分，再按批次调用 GLM/DeepSeek 增强，最后写入 sentiment_evidence。

2. 社区讨论（community）
从 community_posts 读帖子（标题 + 正文），默认分析上限 120 条。可选先爬取东方财富股吧（crawl_community_for_symbols → providers/community.py），默认每只股票抓 120 条。

社区文本在通用关键词规则之外，还有专用词表：

正面：看多、利好、涨停、低估…
负面：看空、利空、跌停、暴雷…
3. 交易型情绪（market）
用 preferred_daily_bars 取日 K，算一条「交易型情绪」证据，不依赖文本。主要因子包括：

1/5/20 日涨跌幅加权
成交额/量比相对 20 日均值
窗口内涨跌停天数
最大回撤、高换手 + 下跌
打分机制
本地规则（兜底）
KEYWORD_RULES 约 40+ 条中文关键词，每条带：

分数（如「回购」+42、「立案」-58）
类别（capital_action、regulatory、earnings 等）
影响周期（1d/1w/1m/1q）
匹配到的关键词累加，再 clamp 到 [-100, 100]，并映射标签：

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
基本面单独用 score_financial_metrics：营收增速、ROE、净利率、负债率、是否亏损等算规则分。

LLM 增强（默认）
use_llm 默认 True。配置了 API Key 时，在本地规则结果上批量调用 Chat Completions，要求返回 JSON：

sentiment_score、confidence、category、impact_horizon、keywords、reason

LLM 优先级：GLM > DeepSeek（读 .env 或环境变量）。批量大小默认 24，可用 `KEIKO_SENTIMENT_LLM_BATCH_SIZE` 调整。

聚合：综合情绪快照
upsert_sentiment_snapshot 把窗口内所有 evidence 按类型分组，各自做带时间衰减的加权平均（weighted_score + recency_weight），再合成 composite：

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
history.py 集成：详情页刷新会调用 refresh_symbol_sentiment；若 6 小时内已有快照，则跳过 GLM 重算，避免重复刷新同一批结果
工具函数：symbol 规范化、日期窗口、JSON 解析、分数 clamp 等
设计特点小结
可解释：每条 evidence 存 keywords_json、evidence_json（规则命中、行情明细、LLM reason）
可增量：upsert + (sentiment_type, source_table, source_id, method_version) 唯一键，重复刷新会更新而非重复插入
默认 GLM 优先：不依赖 LLM 也能跑，但配置 GLM 后刷新会优先使用 GLM 结果
A 股语境：关键词、涨跌停阈值（9.4%）、股吧爬虫都针对 A 股场景
如果你希望，我可以继续帮你对照前端或 stock_detail 看 composite 分具体在哪里展示，或者 walk through 某只股票的 refresh 实际 SQL 读写路径。
