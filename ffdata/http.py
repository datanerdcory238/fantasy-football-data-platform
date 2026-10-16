"""A polite, cached HTTP fetcher.

Responsibilities (each one is a real data-engineering concern):

1. **Respect robots.txt** – we check it before fetching any URL.
2. **Rate limiting** – wait between live requests so we never hammer the site.
   Sports-Reference temporarily bans clients that exceed ~20 requests/minute.
3. **Retries with backoff** – transient errors (429 / 5xx / network) are retried.
4. **Raw-data caching** – every page is saved to ``data/raw/`` exactly as
   downloaded. This is the *raw / bronze* layer: if a parser has a bug we can
   re-parse from disk without re-scraping. In Step 2 this folder becomes S3.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from .config import settings

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RobotsDisallowed(Exception):
    """Raised when robots.txt forbids fetching a URL."""


@dataclass
class FetchResult:
    url: str
    html: str
    cache_path: Path
    from_cache: bool


class PoliteFetcher:
    def __init__(
        self,
        delay_seconds: float | None = None,
        user_agent: str | None = None,
        raw_dir: Path | None = None,
        max_retries: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        self.delay = settings.delay_seconds if delay_seconds is None else delay_seconds
        self.user_agent = user_agent or settings.user_agent
        self.raw_dir = raw_dir or settings.raw_data_dir
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = self.user_agent
        self._last_request_at = 0.0
        self._robots: dict[str, RobotFileParser] = {}

    # ---------- public API ----------
    def get(self, url: str, refresh: bool = False) -> FetchResult:
        """Return page HTML, from the raw cache unless ``refresh`` is True."""
        path = self.cache_path_for(url)
        if path.exists() and not refresh:
            log.debug("cache hit %s", url)
            return FetchResult(url, path.read_text(encoding="utf-8"), path, True)

        self._check_robots(url)
        html = self._download(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return FetchResult(url, html, path, False)

    def get_json(self, url: str) -> Any:
        """Call a JSON API (e.g. GitHub's). Never cached: we ask the API to learn what changed."""
        self._check_robots(url)
        return self._request(url).json()

    def download(self, url: str, dest: Path, headers: dict[str, str] | None = None) -> Path:
        """Download a file and save it, byte for byte, to ``dest`` (the raw layer)."""
        self._check_robots(url)
        resp = self._request(url, headers)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return dest

    def cache_path_for(self, url: str) -> Path:
        """Map a URL to a file path, e.g.
        https://www.pro-football-reference.com/years/2025/games.htm
        -> data/raw/www.pro-football-reference.com/years/2025/games.htm
        """
        parsed = urlparse(url)
        rel = parsed.path.lstrip("/") or "index.html"
        return self.raw_dir / parsed.netloc / rel

    # ---------- internals ----------
    def _check_robots(self, url: str) -> None:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = RobotFileParser()
            try:
                resp = self.session.get(f"{base}/robots.txt", timeout=30)
                rp.parse(resp.text.splitlines() if resp.ok else [])
            except requests.RequestException:
                log.warning("could not read robots.txt for %s; proceeding cautiously", base)
                rp.parse([])
            self._robots[base] = rp
        if not rp.can_fetch(self.user_agent, url):
            raise RobotsDisallowed(url)

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _download(self, url: str) -> str:
        return self._request(url).text

    def _request(self, url: str, headers: dict[str, str] | None = None) -> requests.Response:
        """GET with rate limiting and retries; returns the successful response."""
        for attempt in range(1, self.max_retries + 1):
            self._wait_for_rate_limit()
            self._last_request_at = time.monotonic()
            try:
                resp = self.session.get(url, headers=headers, timeout=60)
            except requests.RequestException as exc:
                err: str = repr(exc)
            else:
                if resp.status_code == 200:
                    log.info("fetched %s", url)
                    return resp
                if resp.status_code not in RETRYABLE_STATUS:
                    resp.raise_for_status()
                err = f"HTTP {resp.status_code}"
            backoff = self.delay * (2 ** attempt)
            log.warning("attempt %d/%d for %s failed (%s); sleeping %.0fs",
                        attempt, self.max_retries, url, err, backoff)
            time.sleep(backoff)
        raise RuntimeError(f"giving up on {url} after {self.max_retries} attempts")
