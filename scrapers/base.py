import asyncio
import random
from abc import ABC, abstractmethod
from typing import Optional

import aiohttp

from config import USER_AGENTS, REQUEST_TIMEOUT, Internship


try:
    from fake_useragent import UserAgent
    _ua = UserAgent()
    def _random_ua() -> str:
        try:
            return _ua.random
        except Exception:
            return random.choice(USER_AGENTS)
except ImportError:
    def _random_ua() -> str:
        return random.choice(USER_AGENTS)


_pw_lock = asyncio.Lock()
_bing_limiter = asyncio.Semaphore(5)


class BaseScraper(ABC):
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self, headers: Optional[dict] = None) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=headers or self._headers())
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _headers(self) -> dict:
        return {
            "User-Agent": _random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
        }

    async def fetch(self, url: str, timeout: int = REQUEST_TIMEOUT,
                    headers: Optional[dict] = None) -> Optional[str]:
        session = await self._get_session(headers)
        for attempt in range(3):
            try:
                async with session.get(url, timeout=timeout, allow_redirects=True) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if len(text) > 1000:
                            return text
            except (asyncio.TimeoutError, aiohttp.ClientError, Exception):
                pass
            wait = (attempt + 1) * random.uniform(2, 4)
            await asyncio.sleep(wait)
        return None

    async def bing_fetch(self, url: str, timeout: int = 25) -> Optional[str]:
        async with _bing_limiter:
            html = await self.fetch(url, timeout=timeout)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return html

    async def safe_fetch(self, url: str, headers: Optional[dict] = None,
                         timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
        for attempt in range(2):
            html = await self.fetch(url, timeout=timeout, headers=headers)
            if html:
                return html
            await asyncio.sleep(random.uniform(2, 3))
        return None

    @abstractmethod
    async def scrape(self) -> list[Internship]:
        ...
