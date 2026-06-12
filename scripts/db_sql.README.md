具体的字段说明在 docs/warehouse-schema.md中， backend/db.py中有建表逻辑

# symbols
python3 scripts/debug_warehouse.py sql "select * from symbols limit 10"
symbol     market  name    currency  exchange  sector  industry
---------  ------  ------  --------  --------  ------  --------
002594.SZ  A       比亚迪     CNY       SZSE      新能源     汽车
0700.HK    HK      腾讯控股    HKD       HKEX      互联网     平台与游戏
NVDA       US      NVIDIA  USD       NASDAQ    半导体     AI 算力
600519.SH  A       贵州茅台    CNY       SSE       消费      白酒
1810.HK    HK      小米集团    HKD       HKEX      智能硬件    手机与汽车
AAPL       US      Apple   USD       NASDAQ    消费电子    硬件与服务
688114.SH  A       华大智造    CNY       SSE       医疗器械    基因测序设备
000001.SZ  A       平安银行    CNY       SZSE      深圳      银行
000002.SZ  A       万科A     CNY       SZSE      深圳      全国地产
000004.SZ  A       *ST国华   CNY       SZSE      深圳      软件服务

python3 scripts/debug_warehouse.py sql "select market, count(*) from symbols group by market"
market  count(*)
------  --------
A       7578
HK      2
US      2

挑选市场：
python3 scripts/debug_warehouse.py sql "select industry, count(*) from symbols where market='A' group by industry"
python3 scripts/debug_warehouse.py sql "select * from symbols where market='A' and industry='火力发电'"
600578.SH 京能电力


```bash
python3 scripts/debug_warehouse.py --raw sql "select raw_json from daily_bars where symbol = '600489.SH' order by trade_date desc limit 1" | python3 -m json.tool
```

验证 JSON 是否有效：

```bash
python3 scripts/debug_warehouse.py sql "select symbol, trade_date, provider, adjust, json_valid(raw_json) raw_valid from daily_bars where symbol = '600489.SH' order by trade_date desc limit 3"
```


# symbol_aliases
python3 scripts/debug_warehouse.py sql "select * from symbol_aliases limit 10"


# daily_bars 日k线
python3 scripts/debug_warehouse.py sql "select * from daily_bars limit 10"
python3 scripts/debug_warehouse.py sql "select provider, count(*) from daily_bars group by provider"
provider         count(*)
---------------  --------
akshare-market   169
baostock-market  1100472
finnhub-market   2
mock-market      6
tushare-market   171

get最近的一条数据
python3 scripts/debug_warehouse.py sql "select * from daily_bars where symbol='600578.SH' order by trade_date DESC limit 1"
python3 scripts/debug_warehouse.py sql "select * from daily_bars where symbol='000001.SH' order by trade_date DESC limit 1"


# financial_metrics_history 季度财务数据
python3 scripts/debug_warehouse.py sql "select * from financial_metrics_history limit 10"

python3 scripts/debug_warehouse.py sql "select provider, count(*) from financial_metrics_history group by provider"

python3 scripts/debug_warehouse.py sql "select * from financial_metrics_history where provider='baostock-financial' limit 10"

# company_reports_history 季度公司报告
python3 scripts/debug_warehouse.py sql "select * from company_reports_history limit 10"
<!-- python3 scripts/debug_warehouse.py sql "select provider, count(*) from company_reports_history group by provider" -->

python3 scripts/debug_warehouse.py sql "select * from ingestion_runs limit 10"




清理任务

python3 -c "
import sys; from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from backend.db import get_db, init_db
from backend.history import finish_ingestion, parse_json_value
init_db()
with get_db() as conn:
    row = conn.execute('select * from ingestion_runs where id=?', (32,)).fetchone()
    item = dict(row)
    finish_ingestion(conn, 32, 'interrupted',
        parse_json_value(item['updated_symbols'], []),
        parse_json_value(item['counts_json'], {}),
        parse_json_value(item['errors_json'], []) + [{'scope':'manual','error':'interrupted'}])
    conn.commit()
"


python scripts/run_baostock_financial_backfill.py \
  --quarters 4 --batch-size 10 --no-universe-refresh --json

KEIKO_BAOSTOCK_FINANCIAL_BATCH_TIMEOUT_SECONDS=8 \
KEIKO_BAOSTOCK_REPORT_BATCH_TIMEOUT_SECONDS=5 \
python scripts/run_baostock_financial_backfill.py 600578.SH \
  --quarters 1 --batch-size 1 --max-batches 1 --no-universe-refresh --json


