import random

from config import Internship
from .base import BaseScraper


try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class GlassdoorScraper(BaseScraper):
    SOURCE = "glassdoor"
    MAX_JOBS = 20

    async def scrape(self) -> list[Internship]:
        if not PLAYWRIGHT_AVAILABLE:
            return []
        return await self._scrape_playwright()

    async def _scrape_playwright(self) -> list[Internship]:
        url = "https://www.glassdoor.com/Job/egypt-internship-jobs-SRCH_IL.0,5_IN223_KO6,16.htm"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(3000, 5000))
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

                job_data = await page.evaluate(f"""() => {{
                    const cards = document.querySelectorAll('li[data-test="jobListing"], div.jobListing, div[class*="job-card"], article[class*="job"]');
                    const results = [];
                    const seen = new Set();
                    for (const card of cards) {{
                        try {{
                            const titleEl = card.querySelector('a.job-title, a[class*="title"], h2 a, a[class*="jobTitle"]');
                            if (!titleEl) continue;
                            const title = titleEl.innerText.trim();
                            const href = titleEl.getAttribute('href') || '';
                            if (!title || !href || seen.has(href)) continue;
                            seen.add(href);
                            const companyEl = card.querySelector('div.employer-name, span[class*="employer"], a[class*="company"], div[class*="company"]');
                            const company = companyEl ? companyEl.innerText.trim() : '';
                            const locEl = card.querySelector('span[class*="location"], div[class*="location"]');
                            const location = locEl ? locEl.innerText.trim() : 'Egypt';
                            results.push({{ title, href, company, location }});
                        }} catch(e) {{}}
                        if (results.length >= {self.MAX_JOBS}) break;
                    }}
                    return results;
                }}""")

                await browser.close()

                return [
                    Internship(
                        title=d["title"], company=d["company"],
                        location=d["location"] or "Egypt",
                        url=d["href"] if d["href"].startswith("http") else f"https://www.glassdoor.com{d['href']}",
                        source=self.SOURCE,
                    )
                    for d in job_data
                ]
        except Exception:
            return []
