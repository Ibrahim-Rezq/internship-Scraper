import asyncio
from urllib.parse import quote_plus

from config import SCRAPER_CONFIG, Internship
from .base import BaseScraper


class CompanyPagesScraper(BaseScraper):
    SOURCE = "company"

    async def scrape(self) -> list[Internship]:
        cfg = SCRAPER_CONFIG["company_pages"]
        templates = cfg["query_templates"]
        targets = [("company", c) for c in cfg["companies"]] + [("university", u) for u in cfg["universities"]]

        async def search_target(name):
            queries = [t.format(name=name) for t in templates]
            jobs = []
            for q in queries:
                url = f"https://www.bing.com/search?q={quote_plus(q)}&mkt=en-US&cc=EG"
                html = await self.bing_fetch(url)
                if not html:
                    continue
                jobs.extend(self._parse(html, name))
            return jobs

        tasks = [search_target(name) for kind, name in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        jobs = []
        for r in results:
            if isinstance(r, list):
                jobs.extend(r)
        return jobs

    def _parse(self, html: str, name: str) -> list[Internship]:
        import re
        jobs = []
        cites = set()
        for m in re.finditer(r'<cite[^>]*>(.*?)</cite>', html, re.DOTALL):
            cite_raw = m.group(1)
            cite_text = re.sub(r'<[^>]+>', '', cite_raw).strip()
            cite_text = cite_text.replace(" › ", "/").replace(" ", "")
            url = ("https://" + cite_text) if not cite_text.startswith("http") else cite_text
            if any(x in url for x in ("linkedin.com/jobs", "wuzzuf", "indeed", "glassdoor")):
                continue
            if url in cites:
                continue
            cites.add(url)
            title = name
            tm = re.search(
                r'<a[^>]*href="https?://(?!www\.bing\.com)[^"]*"[^>]*>(.*?)</a>',
                html[html.find(cite_raw) - 200:html.find(cite_raw) + 50], re.DOTALL
            )
            if tm:
                title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
            jobs.append(Internship(
                title=f"{title} — {name}", company=name,
                location="Egypt", url=url, source=self.SOURCE,
            ))
        return jobs
