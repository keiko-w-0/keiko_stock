先读 README.md、scripts/debug_warehouse.README.md、docs/warehouse-schema.md、docs/handoff.md、docs/engineering-todo.md。

当前主线是数据库驱动的本地研究台，不再是纯 mock：先检查 BaoStock 后台回刷和 SQLite 历史数据仓库状态，再继续开发。

启动/确认后端：

```bash
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8104
```

接手时优先执行：

```bash
python3 scripts/debug_warehouse.py runs --limit 5
python3 scripts/debug_warehouse.py coverage
python3 scripts/debug_warehouse.py providers
python3 scripts/debug_warehouse.py financials
python3 scripts/debug_warehouse.py financial-symbol 600519.SH --quarters 12
```

如果有 BaoStock `running` 任务，用：

```bash
curl -sS http://127.0.0.1:8104/api/data/jobs/<run_id>
```

如果需要手动继续回刷，不依赖前端：

```bash
python3 scripts/run_baostock_backfill.py --days 260 --batch-size 30
```

如果需要手动继续 BaoStock 季频财务/公司报告回刷：

```bash
python3 scripts/run_baostock_financial_backfill.py --quarters 12 --batch-size 10
```

改 BaoStock 仓库/回刷逻辑后先跑：

```bash
python3 scripts/test_warehouse_guards.py
python3 -m compileall backend scripts
```

本机已有 LaunchAgent 自动回刷：

```bash
launchctl print gui/501/com.keiko.baostock-nightly
launchctl print gui/501/com.keiko.baostock-financial-nightly
```

- `com.keiko.baostock-nightly`：每天 00:00 回刷 BaoStock 日线。
- `com.keiko.baostock-financial-nightly`：每天 02:30 回刷 BaoStock 季频财务/公司报告。

继续开发重点：BaoStock 正式 worker/队列、复权口径统一、daily_bars 索引或 DuckDB/Parquet、数据库筛选/回测测试、把 BaoStock 季频 `financial_metrics_history` 接入单股分析财务快照、单股分析进一步脱离前端 fallback。
