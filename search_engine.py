import asyncio
import re
import random
from urllib.parse import urlparse, quote_plus

from config import SCRAPER_CONFIG, Internship, TARGET_CITIES
from scrapers.base import BaseScraper

BOARD_DOMAINS = {"linkedin.com", "wuzzuf.net", "indeed.com",
    "eg.indeed.com", "glassdoor.com", "tanqeeb.com", "bayt.com",
    "naukrigulf.com", "gulftalent.com", "monster.com",
    "careerjet.com", "jobstreet.com", "jooble.org"}

COMPANY_PATTERNS = [
    (r'\s+[-–|]\s+(.+)$', 1),
    (r'\s+@\s+(.+)$', 1),
    (r'\s+at\s+(.+)$', 1),
    (r'^(.+?)\s+[-–|]\s+', 1),
]


def extract_company_from_title(title: str) -> str | None:
    t = title.strip()
    for pat, group in COMPANY_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            c = m.group(group).strip()
            c = re.sub(r'\s*\([^)]*\)\s*$', '', c)
            if any(kw in c.lower() for kw in ("intern", "trainee", "graduate", "summer",
                                                "training", "entry", "fresh")):
                continue
            if 3 < len(c) < 60:
                return c
    return None


class SearchEngineScraper(BaseScraper):
    SOURCE = "search"

    async def scrape(self) -> list[Internship]:
        cfg = SCRAPER_CONFIG["search_engine"]
        jobs = []
        for kw in cfg["keywords"]:
            url = f"https://www.bing.com/search?q={quote_plus(kw)}&mkt=en-US&cc=EG"
            html = await self.bing_fetch(url)
            if not html:
                continue
            chunk = self._parse(html)
            jobs.extend(chunk)
        return jobs

    def _parse(self, html: str) -> list[Internship]:
        jobs = []
        seen = set()

        pattern = re.compile(
            r'<cite[^>]*>(.*?)</cite>.*?'
            r'<h2[^>]*>(.*?)</h2>',
            re.DOTALL
        )

        for m in pattern.finditer(html):
            cite_raw = m.group(1)
            cite_text = re.sub(r'<[^>]+>', '', cite_raw).strip()
            cite_text = cite_text.replace(" › ", "/").replace(" ", "")
            url = ("https://" + cite_text) if not cite_text.startswith("http") else cite_text

            domain = urlparse(url).netloc.lower().removeprefix("www.")
            if any(b in domain for b in BOARD_DOMAINS):
                continue
            if url in seen:
                continue
            seen.add(url)

            title_raw = m.group(2)
            title = re.sub(r'<[^>]+>', '', title_raw).strip()
            title = re.sub(r'\s+', ' ', title)
            title = title.rstrip("...").strip()
            if not title:
                continue

            block_end = min(m.end() + 300, len(html))
            desc_m = re.search(
                r'<p[^>]*class="[^"]*b_lineclamp2[^"]*"[^>]*>(.*?)</p>',
                html[m.start():block_end], re.DOTALL
            )
            desc = ""
            if desc_m:
                desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip()
                desc = re.sub(r'\s+', ' ', desc)

            location = ""
            text_lower = (title + " " + desc).lower()
            if "egypt" in text_lower or "مصر" in text_lower:
                location = "Egypt"
            for city in TARGET_CITIES:
                if city in text_lower:
                    location = city.title() + ", Egypt"
                    break

            company = extract_company_from_title(title) or ""

            if company:
                title = re.sub(r'\s+[-–|]\s+.*$', '', title).strip()

            jobs.append(Internship(
                title=title, company=company, location=location,
                url=url, source=self.SOURCE, description=desc,
            ))

        return jobs
