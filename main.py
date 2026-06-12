import asyncio
import sys
import time

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import SCRAPER_CONFIG, OUTPUT_DIR
import filters as f
from filters import filter_jobs
from output import save_json, save_html


def _progress(queue, kind, **kw):
    if kind is None:
        return
    if queue is not None:
        queue.put_nowait({"type": kind, **kw})


async def run_pipeline(user_config: dict = None, progress_queue: asyncio.Queue = None):
    if user_config:
        for key, value in user_config.items():
            if key in SCRAPER_CONFIG and isinstance(value, dict):
                SCRAPER_CONFIG[key].update(value)
            else:
                SCRAPER_CONFIG[key] = value
        if "exclude_titles" in user_config:
            f.EXCLUDE_TITLES = user_config["exclude_titles"]
        if "include_titles" in user_config:
            f.INCLUDE_TITLES = user_config["include_titles"]
        if "target_cities" in user_config:
            f.TARGET_CITIES = user_config["target_cities"]

    start = time.time()
    OUTPUT_DIR.mkdir(exist_ok=True)

    async def _run(name, scraper, timeout=90):
        try:
            jobs = await asyncio.wait_for(scraper.scrape(), timeout=timeout)
            msg = f"  {name}: {len(jobs)} results"
            print(msg, flush=True)
            _progress(progress_queue, "phase_done", source=name, count=len(jobs))
            return jobs
        except asyncio.TimeoutError:
            msg = f"  {name}: TIMEOUT after {timeout}s"
            print(msg, flush=True)
            _progress(progress_queue, "phase_error", source=name, error="timeout")
            return []
        except Exception as e:
            msg = f"  {name}: ERROR — {e}"
            print(msg, flush=True)
            _progress(progress_queue, "phase_error", source=name, error=str(e))
            return []
        finally:
            await scraper.close()

    async def _phase(cfg_key, name, scraper_cls, timeout=90):
        if not SCRAPER_CONFIG.get(cfg_key, {}).get("enabled", True):
            msg = f"  {name}: skipped (disabled)"
            print(msg, flush=True)
            _progress(progress_queue, "phase_skip", source=name)
            return []
        scraper = scraper_cls()
        return await _run(name, scraper, timeout=timeout)

    all_jobs = []

    msg = "Phase 1 — Playwright scrapers (serialized, retry-enabled)"
    print(msg, flush=True)
    _progress(progress_queue, "message", text=msg)
    from scrapers.indeed import IndeedScraper
    from scrapers.wuzzuf import WuzzufScraper

    jobs = await _phase("indeed", "Indeed", IndeedScraper)
    all_jobs.extend(jobs)

    jobs = await _phase("wuzzuf", "Wuzzuf", WuzzufScraper)
    all_jobs.extend(jobs)

    msg = "Phase 2 — Bing-backed scrapers (rate-limited)"
    print("", flush=True)
    print(msg, flush=True)
    _progress(progress_queue, "message", text=msg)
    from scrapers.company_pages import CompanyPagesScraper
    from search_engine import SearchEngineScraper

    jobs = await _phase("company_pages", "Company Pages", CompanyPagesScraper, timeout=90)
    all_jobs.extend(jobs)

    jobs = await _phase("search_engine", "Search Engine", SearchEngineScraper, timeout=90)
    all_jobs.extend(jobs)

    msg = "Phase 3 — HTTP scrapers"
    print("", flush=True)
    print(msg, flush=True)
    _progress(progress_queue, "message", text=msg)
    from scrapers.linkedin import LinkedInScraper

    jobs = await _phase("linkedin", "LinkedIn", LinkedInScraper, timeout=120)
    all_jobs.extend(jobs)

    print("", flush=True)
    msg = f"Total raw results: {len(all_jobs)}"
    print(msg, flush=True)
    _progress(progress_queue, "message", text=msg)

    before_dedup = len(all_jobs)
    filtered = filter_jobs(all_jobs)
    after_dedup = len(filtered)
    dedup_removed = before_dedup - after_dedup

    print(f"After dedup/filter: {len(filtered)}", flush=True)
    print(f"  Dedup/filter removed {dedup_removed} entries", flush=True)

    elapsed = time.time() - start

    if filtered:
        json_path = save_json(filtered, "internships")
        html_path = save_html(filtered, "internships")
        print(f"Exported to {OUTPUT_DIR / 'internships.json'}", flush=True)
        print(f"Exported to {OUTPUT_DIR / 'internships.html'}", flush=True)
        _progress(progress_queue, "done",
                  total=len(filtered), removed=dedup_removed,
                  json_path=json_path, html_path=html_path,
                  elapsed=round(elapsed, 1))
    else:
        print("No results found.", flush=True)
        _progress(progress_queue, "done",
                  total=0, removed=dedup_removed,
                  json_path=None, html_path=None,
                  elapsed=round(elapsed, 1))

    print("", flush=True)
    print(f"Total time: {elapsed:.1f}s", flush=True)
    _progress(progress_queue, None)
    return filtered


async def main():
    print("Egypt Internships Scraper")
    print("=" * 40)
    await run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
