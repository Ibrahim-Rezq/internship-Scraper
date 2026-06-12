# Internship Scraper

Scrapes internship listings in Egypt from LinkedIn, job boards, and company career pages. Comes with a web UI to configure searches and view results.

## How it works

The scraper runs in 3 phases:

1. **Playwright sources** — Indeed and Wuzzuf (headless browser, serialized to avoid Chrome conflicts)
2. **Bing-backed sources** — Company career pages and general search engine results (rate-limited to avoid 429s)
3. **LinkedIn** — Direct HTTP with 4 fallback parsers to handle HTML variation

After scraping, results go through a filter pipeline: URL dedup → same-source fuzzy dedup (0.85 threshold) → title relevance → Egypt location check. Output is written to `output/internships.json` and `output/internships.html`.

The HTML report is a self-contained dark-mode page with search, source filtering, and sortable columns.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python3 app.py
```

Opens `http://localhost:8000` in your browser.

## Usage

### Web UI (recommended)

```bash
python3 app.py
```

Configure keywords, toggle sources, set filters, click Run. Progress streams live via SSE. Results link to the generated JSON and HTML report.

### CLI

```bash
python3 main.py
```

Runs with the default config from `config.py`. Output goes to `output/`.

## Config

All per-source settings live in `SCRAPER_CONFIG` in `config.py`. Toggle sources on/off, set keywords per source, adjust timeouts. The "Load Defaults" button in the web UI reads these same values.

## Project structure

```
app.py                 FastAPI server (web UI)
main.py                Entry point, pipeline orchestrator
config.py              Scraper config, constants, Internship dataclass
filters.py             Dedup, relevance, location filtering
output.py              JSON and HTML report generation
search_engine.py       Bing search scraper
scrapers/
  base.py              Shared HTTP client, rate limiter, Playwright lock
  linkedin.py          LinkedIn scraper (4 fallback parsers)
  indeed.py            Indeed scraper (Playwright)
  wuzzuf.py            Wuzzuf scraper (Playwright)
  company_pages.py     Company career page scraper (Bing)
  glassdoor.py         Glassdoor scraper (incomplete)
templates/
  index.html           Web UI
output/                Generated reports
```

## Deployment

Not suited for serverless (needs Chrome + long runtimes). Works on any VPS or Docker host — a `Dockerfile` is included.
