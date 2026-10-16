"""Tests for the polite fetcher using a fake HTTP session (no network)."""
import pytest

from ffdata.http import PoliteFetcher, RobotsDisallowed


class FakeResponse:
    def __init__(self, status, text):
        self.status_code, self.text = status, text
        self.ok = status < 400
        self.content = text.encode("utf-8")

    def raise_for_status(self):
        raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, robots="User-agent: *\nDisallow: /private/\n"):
        self.headers, self.calls, self.robots = {}, [], robots

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(200, self.robots)
        return FakeResponse(200, f"<html>{url}</html>")


def make(tmp_path):
    session = FakeSession()
    return PoliteFetcher(delay_seconds=0, raw_dir=tmp_path, session=session), session


def test_saves_raw_html_and_serves_from_cache(tmp_path):
    fetcher, session = make(tmp_path)
    url = "https://example.com/years/2025/games.htm"

    first = fetcher.get(url)
    assert first.from_cache is False
    assert first.cache_path == tmp_path / "example.com" / "years" / "2025" / "games.htm"
    assert first.cache_path.read_text() == first.html

    second = fetcher.get(url)
    assert second.from_cache is True
    assert session.calls.count(url) == 1  # no second network request


def test_refresh_bypasses_cache(tmp_path):
    fetcher, session = make(tmp_path)
    url = "https://example.com/a.htm"
    fetcher.get(url)
    fetcher.get(url, refresh=True)
    assert session.calls.count(url) == 2


def test_respects_robots_txt(tmp_path):
    fetcher, _ = make(tmp_path)
    with pytest.raises(RobotsDisallowed):
        fetcher.get("https://example.com/private/secret.htm")


def test_download_saves_file_and_checks_robots(tmp_path):
    fetcher, session = make(tmp_path)
    dest = tmp_path / "nflverse" / "schedules" / "games.csv"
    assert fetcher.download("https://example.com/assets/2", dest) == dest
    assert dest.read_text(encoding="utf-8") == "<html>https://example.com/assets/2</html>"
    with pytest.raises(RobotsDisallowed):
        fetcher.download("https://example.com/private/x.csv", tmp_path / "x.csv")
