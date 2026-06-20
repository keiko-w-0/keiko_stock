# 问财基本面画像

更新日期：2026-06-20

本模块把问财个股详情页里的三块画像写入本地 SQLite，并在单股详情页右侧展示：

- 简介和看点
- 近期概念事件
- 所属概念列表

数据只作为研究辅助缓存。问财接口存在风控和限流，批量抓取必须慢速运行，并启用连续 403 断路保护。

## 本地数据库

默认数据库：

```bash
data/iwencai_profile.db
```

主要表：

- `iwencai_profiles`：每个标的一条画像主记录，包含抓取时间、问句、解析状态、简介文本。
- `iwencai_profile_highlights`：简介和看点下方标签。
- `iwencai_important_events`：近期概念事件。
- `iwencai_concepts`：所属概念列表。
- `iwencai_crawl_state`：每个标的最近一次抓取状态、错误和更新时间。
- `iwencai_crawl_runs`：每次批量任务的启动、结束、统计和错误摘要。

## 单股详情展示

后端 `backend/stock_detail.py` 会读取 `data/iwencai_profile.db`，在单股详情接口中返回：

```json
{
  "fundamental": {
    "iwencai": {
      "status": "ok",
      "summary": "...",
      "highlights": [],
      "important_events": [],
      "concepts": []
    }
  }
}
```

前端单股详情抽屉右侧有两个 tab：

- `基本面分析`：默认展示问财画像，顺序为简介和看点、近期概念事件、所属概念列表。
- `情绪面`：展示原来的公告/社区/交易行为情绪面。

所属概念列表默认收起，点击每个概念可展开详情。

## 手动抓取

抓取单个股票：

```bash
python3 scripts/crawl_iwencai_profile.py 000725.SZ --force
```

全量慢速续跑，跳过最近 168 小时内已经 `ok/no_sections` 的记录，只请求失败和未跑标的：

```bash
python3 -u scripts/crawl_iwencai_profile.py \
  --tier all \
  --stale-hours 168 \
  --sleep 8 \
  --jitter 7 \
  --timeout 30 \
  --max-retries 1 \
  --circuit-403-threshold 5 \
  --circuit-cooldown-seconds 7200 \
  --status-every 25
```

也可以直接运行封装脚本：

```bash
scripts/run_iwencai_profile_slow_resume.sh
```

## 403 断路保护

批量运行时如果连续触发问财 `403 Forbidden`，脚本会暂停，等待冷却后新建 session/token 继续。

当前慢跑配置：

- 连续 `5` 次 403 触发断路
- 暂停 `7200` 秒，也就是 2 小时
- 冷却后继续跑剩余标的
- `--circuit-max-cooldowns 0` 表示不限冷却次数

日志中会出现类似：

```text
[circuit-breaker] consecutive_403=5 cooldown_count=1 last=002128.SZ 电投能源 pause_seconds=7200 resume_at=2026-06-20 23:20:00
```

## 2026-06-20 21:00 定时任务

本机已设置 macOS LaunchAgent：

```text
/Users/wangwenhui/Library/LaunchAgents/com.keiko.iwencai.profile.slowresume.once.plist
```

它会在 `2026-06-20 21:00` 启动问财画像慢速续跑。当前 plist 直接调用 conda Python：

```text
/Users/wangwenhui/miniconda3/bin/python3 -u scripts/crawl_iwencai_profile.py --tier all --stale-hours 168 --sleep 8 --jitter 7 --timeout 30 --max-retries 1 --circuit-403-threshold 5 --circuit-cooldown-seconds 7200 --status-every 25
```

不要再通过 `/bin/bash -lc "cd ...; ./scripts/run_iwencai_profile_slow_resume.sh"` 包装启动；这种方式在 2026-06-20 21:00 触发过 macOS `Operation not permitted`，任务会卡在入口，跑不到问财请求。

检查是否已加载或正在运行：

```bash
launchctl list | rg 'com\.keiko\.iwencai\.profile\.slowresume\.once'
launchctl print gui/$(id -u)/com.keiko.iwencai.profile.slowresume.once
```

停止这个任务：

```bash
launchctl unload -w ~/Library/LaunchAgents/com.keiko.iwencai.profile.slowresume.once.plist
```

## 监控进度

查看 LaunchAgent 日志：

```bash
tail -f logs/iwencai_profile_launchd_once.out.log
tail -f logs/iwencai_profile_launchd_once.err.log
```

手动运行 `scripts/run_iwencai_profile_slow_resume.sh` 时，查看脚本自带慢跑日志：

```bash
ls -t logs/iwencai_profile_slow_resume_*.log | head -1
tail -f "$(ls -t logs/iwencai_profile_slow_resume_*.log | head -1)"
```

查看是否有进程在跑：

```bash
ps -ef | rg '[c]rawl_iwencai_profile|[r]un_iwencai_profile_slow_resume'
```

查看最新 run 和状态统计：

```bash
python3 - <<'PY'
import json, sqlite3
conn = sqlite3.connect('data/iwencai_profile.db')
conn.row_factory = sqlite3.Row
run = conn.execute('select * from iwencai_crawl_runs order by id desc limit 1').fetchone()
print(dict(run))
if run and run['counts_json']:
    print(json.dumps(json.loads(run['counts_json']), ensure_ascii=False, indent=2))
print('state counts:')
for row in conn.execute('select status, count(*) c from iwencai_crawl_state group by status order by c desc'):
    print(dict(row))
PY
```

查看近期失败原因：

```bash
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('data/iwencai_profile.db')
conn.row_factory = sqlite3.Row
for row in conn.execute("""
    select symbol, name, target_type, status, updated_at, substr(last_error, 1, 220) last_error
    from iwencai_crawl_state
    where status='failed'
    order by updated_at desc
    limit 20
"""):
    print(dict(row))
PY
```

## 2026-06-20 抓取状态

当日全量任务 `run_id=4` 因连续 403 被手动停止，并标记为 `stopped`：

- 目标总数：`7281`
- 实际处理到：约 `750`
- 有有效画像：`469`
- 成功返回但无三块内容：`83`
- 已有新鲜数据跳过：`4`
- 失败：`194`
- 失败原因：全部为 `403 Forbidden`
- 本地 `iwencai_profiles` 总覆盖：`556`

后续续跑会跳过 `ok/no_sections` 的新鲜记录，优先补失败和未跑标的。

## 画像召回库

问财画像可同步成一个“关键词 + BGE embedding”的混合召回库，用来搜索类似：

```text
AI应用 或者 玻璃基板，先进封装
```

召回库分两层：

- `data/iwencai_recall.db`：SQLite 关键词倒排库、文档库、构建状态和构建 run。
- Qdrant：BGE 向量库，默认使用本地 `data/qdrant_iwencai_recall`；如果设置 `QDRANT_URL`，则连接外部 Qdrant 服务。

关键词库不维护人工主题词表。构建时会从问财全库自动抽取：

- 股票代码、股票名。
- 问财概念名、事件名、看点标题。
- 概念名和正文里的 2-8 字/字符短语 n-gram，例如黄金、铜矿、锂矿、电解铝、CPO、Chiplet。
- 英文/数字技术词。

embedding 负责补同义表达和语义相近表达，关键词层负责精确、可解释召回。

默认 embedding 模型：

```text
BAAI/bge-small-zh-v1.5
```

首次使用前，先把模型下载到本地目录（默认 `data/models/bge-small-zh-v1.5`），后续建库和检索都走本地 CPU 推理，不再每次访问 Hugging Face：

```bash
python3 scripts/download_iwencai_bge_model.py --json
```

推理得到的文档向量会写入 `data/iwencai_recall.db` 的 `iwencai_recall_embeddings` 表；重建 Qdrant 时优先复用缓存，只对新增或正文变更的文档重新 embedding。

可用环境变量覆盖：

```bash
export IWENCAI_BGE_MODEL=BAAI/bge-small-zh-v1.5
export IWENCAI_BGE_DEVICE=cpu
export IWENCAI_BGE_MODEL_PATH=/path/to/local/bge-small-zh-v1.5
export IWENCAI_BGE_BATCH_SIZE=64
export QDRANT_URL=http://127.0.0.1:6333
export QDRANT_API_KEY=...
```

如果后端 API 常驻并且日更脚本也会同时运行，建议启动独立 Qdrant 服务并设置 `QDRANT_URL`；未设置时会使用 qdrant-client 的本地持久化目录，适合单进程或轻量本机使用。

本地 Qdrant 目录同一时刻只能被一个进程独占。若重建脚本报 `already accessed by another instance`，通常是 uvicorn 正在占用；重启 API 后再跑重建，或改用 `QDRANT_URL`。

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

日级更新脚本：

```bash
python3 scripts/run_iwencai_recall_daily.py --json
```

更新逻辑：

- 脚本先读取 `iwencai_profile.db`，把可索引画像拆成 summary、highlight、event、concept 文档。
- 计算“当前可索引股票集合”的 hash。
- 如果 hash 和上次构建一致，说明没有新增画像股票，直接跳过，不重建关键词库和 Qdrant。
- 如果 hash 变化，说明问财库有新股票画像进入，整库重建：先写新的 Qdrant collection，成功后再替换 SQLite 关键词库和 active collection 状态。
- 检索结果会按 `rerank_score` 重排，并默认过滤低于 `0.42` 的弱相关结果（可用 `min_score` 参数或 `IWENCAI_RECALL_MIN_SCORE` 环境变量调整）。
- 英文缩写词（如 `CPO`）不再拆成 `cp` / `po` 这类短 n-gram，避免误召回“百度概念 / 阿里巴巴概念”等无关股票。

手动检查是否需要重建：

```bash
python3 scripts/run_iwencai_recall_daily.py --dry-run --json
```

手动强制重建并做一次 smoke search：

```bash
python3 scripts/run_iwencai_recall_daily.py \
  --force \
  --query "AI应用或者玻璃基板，先进封装" \
  --json
```

API：

```bash
curl -sS "http://127.0.0.1:8100/api/iwencai-recall/status" | python3 -m json.tool
curl -sS "http://127.0.0.1:8100/api/iwencai-recall/search?q=AI应用或者玻璃基板，先进封装&limit=20" | python3 -m json.tool
curl -sS -X POST "http://127.0.0.1:8100/api/iwencai-recall/update?dry_run=true" | python3 -m json.tool
```

macOS 定时源配置：

```text
scripts/com.keiko.iwencai-recall-daily.plist
```

默认每天 `23:40` 运行：

```bash
cp scripts/com.keiko.iwencai-recall-daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.keiko.iwencai-recall-daily.plist
```

日志：

```bash
tail -f logs/iwencai-recall-daily.log
tail -f logs/iwencai-recall-daily.err.log
```
