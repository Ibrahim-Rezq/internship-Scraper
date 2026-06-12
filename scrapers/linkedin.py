import asyncio
import re
import random

from config import SCRAPER_CONFIG, Internship
from .base import BaseScraper


class LinkedInScraper(BaseScraper):
    SOURCE = "linkedin"
    BASE_URL = "https://www.linkedin.com/jobs/search"

    def _is_valid_title(self, t: str) -> bool:
        if not t or t.lower() in {"linkedin", "clear text", "skip to main content", ""}:
            return False
        if len(t) > 80:
            return False
        low = t.lower()
        noise = ["sign in", "join now", "past week", "past month",
                  "past 24 hours", "any time", "done company",
                  "done experience", "clear text", "expand search"]
        for phrase in noise:
            if phrase in low:
                return False
        if re.search(r'\(\d+\)', t):
            return False
        return True

    async def scrape(self) -> list[Internship]:
        cfg = SCRAPER_CONFIG["linkedin"]
        locations_param = cfg["location"]
        days = cfg["days_posted"]
        exp = ",".join(str(e) for e in cfg["experience_level"])
        sort = cfg["sort_by"]

        jobs = []
        all_kw = set(cfg["keywords"] + cfg["industry_keywords"])
        for kw in all_kw:
            params = {
                "keywords": kw, "location": locations_param,
                "f_TPR": f"r{days * 86400}", "f_E": exp,
                "sortBy": sort,
            }
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{self.BASE_URL}?{qs}"
            chunk = await self._fetch_jobs(url)
            jobs.extend(chunk)
            await asyncio.sleep(random.uniform(2, 4))
        return jobs

    def _clean_title(self, raw: str) -> str:
        t = re.sub(r'<[^>]+>', '', raw).strip()
        t = re.sub(r'\s+', ' ', t)
        t = re.sub(r'\s*\d{7,}\s*$', '', t)
        return t

    def _try_parse_v1(self, html: str) -> list[dict] | None:
        hrefs = re.findall(r'base-card__full-link[^>]*href="([^"]+)"', html)
        if not hrefs:
            return None
        raw_titles = re.findall(
            r'sr-only[^>]*>\s*(.*?)\s*</span>', html, re.DOTALL
        )
        companies = re.findall(
            r'base-search-card__subtitle[^>]*>\s*<a[^>]*>(.*?)</a>', html, re.DOTALL
        )
        locations = re.findall(
            r'job-search-card__location[^>]*>(.*?)</span>', html, re.DOTALL
        )
        titles = [self._clean_title(t) for t in raw_titles]
        return [dict(hrefs=hrefs, titles=titles, companies=companies, locations=locations)]

    def _try_parse_v2(self, html: str) -> list[dict] | None:
        blocks = re.findall(
            r'<a[^>]*class="[^"]*job-card[^"]*"[^>]*href="([^"]+)"[^>]*>.*?'
            r'<span[^>]*class="[^"]*job-title[^"]*"[^>]*>(.*?)</span>.*?'
            r'<span[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</span>',
            html, re.DOTALL
        )
        if blocks:
            result = []
            for href, title, company in blocks:
                result.append(dict(href=href, title=self._clean_title(title), company=company.strip()))
            return result if result else None
        return None

    def _try_parse_v3(self, html: str) -> list[dict] | None:
        cards = re.findall(
            r'<div[^>]*class="[^"]*job-card-container[^"]*"[^>]*>.*?'
            r'href="([^"]+)"[^>]*>.*?<span[^>]*>(.*?)</span>',
            html, re.DOTALL
        )
        if cards:
            result = []
            for href, title in cards:
                t = self._clean_title(title)
                if self._is_valid_title(t):
                    result.append(dict(href=href, title=t))
            return result if result else None
        return None

    async def _fetch_jobs(self, url: str) -> list[Internship]:
        html = await self.safe_fetch(url, timeout=45)
        if not html:
            return []

        parsed = self._try_parse_v1(html)
        if parsed is None:
            parsed = self._try_parse_v2(html)
        if parsed is None:
            parsed = self._try_parse_v3(html)

        if parsed is None:
            hrefs = re.findall(r'href="(https?://[^"]*linkedin[^"]*/jobs/view/[^"]+)"', html)
            titles = re.findall(r'<h3[^>]*class="[^"]*"[^>]*>(.*?)</h3>', html, re.DOTALL)
            if hrefs:
                parsed = [dict(hrefs=hrefs, titles=[self._clean_title(t) for t in titles],
                               companies=[], locations=[])]

        if parsed is None:
            return []

        seen_ids = set()
        results = []

        data = parsed[0] if isinstance(parsed[0], dict) and "hrefs" in parsed[0] else None

        if data:
            hrefs = data.get("hrefs", [])
            titles = data.get("titles", [])
            companies = data.get("companies", [])
            locations = data.get("locations", [])
            for i, href in enumerate(hrefs):
                jid_match = re.search(r'(\d+)(?:\?|$)', href.split("-")[-1] if "-" in href else href)
                if not jid_match:
                    continue
                jid = jid_match.group(1)
                if jid in seen_ids:
                    continue
                seen_ids.add(jid)

                title = ""
                if i < len(titles) and self._is_valid_title(titles[i]):
                    title = titles[i]

                if not title:
                    url_title = href.split("/")[-1].split("?")[0]
                    url_title = re.sub(r'-\d+$', '', url_title)
                    url_title = url_title.replace("-", " ").title()
                    if url_title:
                        title = url_title

                company = ""
                if i < len(companies):
                    company = re.sub(r'<[^>]+>', '', companies[i]).strip()
                    company = re.sub(r'\s+', ' ', company)

                location = SCRAPER_CONFIG["linkedin"]["location"]
                if i < len(locations):
                    location = re.sub(r'<[^>]+>', '', locations[i]).strip()
                    location = re.sub(r'\s+', ' ', location)

                clean_href = href.split("?")[0]
                results.append(Internship(
                    title=title, company=company, location=location,
                    url=clean_href, source=self.SOURCE,
                ))
        else:
            for entry in parsed:
                href = entry.get("href", "")
                jid_match = re.search(r'(\d+)(?:\?|$)', href.split("-")[-1] if "-" in href else href)
                if not jid_match:
                    continue
                jid = jid_match.group(1)
                if jid in seen_ids:
                    continue
                seen_ids.add(jid)

                title = entry.get("title", "")
                if not title:
                    url_title = href.split("/")[-1].split("?")[0]
                    url_title = re.sub(r'-\d+$', '', url_title)
                    url_title = url_title.replace("-", " ").title()
                    if url_title:
                        title = url_title

                company = entry.get("company", "")
                clean_href = href.split("?")[0]
                results.append(Internship(
                    title=title, company=company,
                    location=SCRAPER_CONFIG["linkedin"]["location"],
                    url=clean_href, source=self.SOURCE,
                ))

        return results
