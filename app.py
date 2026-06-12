import asyncio
import json
import os
import sys
import webbrowser
from pathlib import Path
from threading import Timer
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from main import run_pipeline
import config
import filters

BASE = Path(__file__).parent
PERSISTED_CONFIG = BASE / "persisted_config.json"
TEMPLATES = BASE / "templates"

app = FastAPI(title="Egypt Internships Scraper")
runs = {}


class RunRequest(BaseModel):
    keywords: list[str]
    exclude_titles: list[str]
    include_titles: list[str]
    target_cities: list[str]
    sources: dict[str, bool]
    location: str = "Egypt"
    days_posted: int = 7


def _defaults() -> dict:
    return {
        "keywords": config.KEYWORDS,
        "exclude_titles": config.EXCLUDE_TITLES,
        "include_titles": config.INCLUDE_TITLES,
        "target_cities": config.TARGET_CITIES,
        "sources": {k: v.get("enabled", True) for k, v in config.SCRAPER_CONFIG.items()},
        "location": "Egypt",
        "days_posted": 7,
    }


def _load_config() -> dict:
    if PERSISTED_CONFIG.exists():
        try:
            stored = json.loads(PERSISTED_CONFIG.read_text())
            d = _defaults()
            d.update(stored)
            return d
        except Exception:
            pass
    return _defaults()


def _save_config(data: dict):
    safe = {k: data[k] for k in ("keywords", "exclude_titles", "include_titles",
                                  "target_cities", "sources", "location", "days_posted")
            if k in data}
    PERSISTED_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    PERSISTED_CONFIG.write_text(json.dumps(safe, indent=2, ensure_ascii=False))


def _to_scraper_config(req: RunRequest) -> dict:
    cfg = {}
    for source, enabled in req.sources.items():
        if source in config.SCRAPER_CONFIG:
            cfg[source] = {**config.SCRAPER_CONFIG[source], "enabled": enabled}
    cfg["keywords"] = req.keywords
    cfg["location"] = req.location
    cfg["days_posted"] = req.days_posted
    cfg["exclude_titles"] = req.exclude_titles
    cfg["include_titles"] = req.include_titles
    cfg["target_cities"] = req.target_cities
    return cfg


async def _execute_run(req: RunRequest, queue: asyncio.Queue, run_id: str):
    try:
        user_cfg = _to_scraper_config(req)
        await run_pipeline(user_config=user_cfg, progress_queue=queue)
    except Exception as e:
        queue.put_nowait({"type": "error", "text": str(e)})
    finally:
        queue.put_nowait(None)


@app.get("/", response_class=HTMLResponse)
async def index():
    html = TEMPLATES / "index.html"
    if not html.exists():
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
    return HTMLResponse(html.read_text(encoding="utf-8"))


@app.get("/api/defaults")
async def get_defaults():
    return JSONResponse(_defaults())


@app.get("/api/config")
async def get_config():
    return JSONResponse(_load_config())


@app.post("/api/config")
async def post_config(data: dict):
    _save_config(data)
    return JSONResponse({"ok": True})


@app.post("/api/run")
async def start_run(req: RunRequest):
    _save_config(req.model_dump())
    run_id = str(uuid4())[:8]
    queue = asyncio.Queue()
    runs[run_id] = queue
    asyncio.create_task(_execute_run(req, queue, run_id))
    return JSONResponse({"run_id": run_id})


@app.get("/api/stream/{run_id}")
async def stream(run_id: str):
    queue = runs.get(run_id)
    if queue is None:
        return JSONResponse({"error": "not found"}, status_code=404)

    async def event_gen():
        try:
            while True:
                msg = await queue.get()
                if msg is None:
                    yield "data: [DONE]\n\n"
                    break
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
        finally:
            runs.pop(run_id, None)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/output/{filename:path}")
async def output_file(filename: str):
    path = config.OUTPUT_DIR / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    url = f"http://localhost:{port}"

    print("┌──────────────────────────────────────────────────┐")
    print(f"│  Egypt Internships Scraper UI                    │")
    print(f"│  {url}                    │")
    print("└──────────────────────────────────────────────────┘")

    Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="0.0.0.0", port=port)
