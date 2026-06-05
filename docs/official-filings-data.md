# Official filings data

This project now has a live filings adapter for four public disclosure entry points:

- CNINFO: A-share/B-share filings mirror for SH/SZ/BJ companies.
- Shanghai Stock Exchange: official SH listed-company announcement search.
- Shenzhen Stock Exchange: official SZ listed-company announcement search.
- HKEXnews: official HK listed-company announcement search.

These endpoints are public website endpoints, not licensed bulk data feeds. Use them for light research, caching, and manual verification. For production distribution, review each site's terms and add rate limiting, caching, retry backoff, and data licensing checks.

## FastAPI usage

Start the backend:

```bash
python3 -B -m uvicorn backend.app:app --host 127.0.0.1 --port 8100
```

List supported filing sources:

```bash
curl -sS "http://127.0.0.1:8100/api/filings/sources" | python3 -m json.tool
```

Query a Shanghai stock through its primary exchange source:

```bash
curl -sS "http://127.0.0.1:8100/api/filings/search?symbol=600519.SH&source=auto&start_date=2026-01-01&end_date=2026-06-05&page_size=10" | python3 -m json.tool
```

Query a Shenzhen stock from both CNINFO and SZSE:

```bash
curl -sS "http://127.0.0.1:8100/api/filings/search?symbol=002594.SZ&source=all&keyword=%E4%B8%9A%E7%BB%A9&page_size=10" | python3 -m json.tool
```

Query a Hong Kong stock through HKEXnews:

```bash
curl -sS "http://127.0.0.1:8100/api/filings/search?symbol=0700.HK&source=hkexnews&start_date=2026-01-01&page_size=10" | python3 -m json.tool
```

## CLI usage

```bash
python3 scripts/fetch_filings.py 600519.SH --source auto --start-date 2026-01-01 --page-size 10
python3 scripts/fetch_filings.py 002594.SZ --source all --keyword 业绩 --json
python3 scripts/fetch_filings.py 0700.HK --source hkexnews --start-date 2026-01-01
```

## Source selection

- `source=auto`: `.SH -> sse`, `.SZ -> szse`, `.HK -> hkexnews`.
- `source=all`: `.SH -> cninfo + sse`, `.SZ -> cninfo + szse`, `.HK -> hkexnews`.
- Explicit values: `cninfo`, `sse`, `szse`, `hkexnews`.

## Unified document fields

Every returned filing document is normalized to:

- `source`: `cninfo`, `sse`, `szse`, or `hkexnews`.
- `symbol`: normalized project symbol such as `600519.SH`.
- `stock_code`: raw exchange code.
- `company`: company short name when supplied by the source.
- `title`: announcement title.
- `published_at`: source publish time when available.
- `url`: direct PDF/document URL when available.
- `file_type`: usually `PDF`.
- `category`: source category text when available.
- `source_tier`: `S`, because these are official or exchange-operated disclosure sources.
- `raw`: original source row for auditing and parser fixes.

## Implementation files

- `backend/providers/filings.py`: source-specific HTTP requests, JSON/JSONP/HTML parsing, URL normalization.
- `backend/filings.py`: source selection, input validation, aggregate response.
- `backend/app.py`: `/api/filings/sources` and `/api/filings/search`.
- `scripts/fetch_filings.py`: command-line fetch helper.
