from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
import re

import feedparser
import httpx

USER_AGENT = "DailyNewsBriefing/0.1 (+https://github.com/)"


@dataclass(frozen=True)
class Item:
    id: str
    feed_id: str
    title: str
    url: str
    published_utc: datetime
    summary_text: str


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", text or ""))).strip()


def parse_feed(content: bytes, feed_id: str, fetched_at: datetime | None = None) -> list[Item]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Malformed feed: {parsed.bozo_exception}")
    result = []
    for entry in parsed.entries:
        url = entry.get("link", "")
        identity = entry.get("id") or entry.get("guid") or url
        published = fetched_at
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            if entry.get(key):
                try:
                    import calendar
                    published = datetime.fromtimestamp(calendar.timegm(entry[key]), timezone.utc)
                    break
                except (ValueError, OverflowError, TypeError):
                    continue
        content_value = entry.get("summary", "")
        if not content_value and entry.get("content"):
            content_value = entry.content[0].get("value", "")
        result.append(Item(str(identity), feed_id, _clean(entry.get("title", "(untitled)")), url, published, _clean(content_value)))
    return result


def fetch_feeds(feeds) -> tuple[list[Item], list[dict[str, str]]]:
    def fetch(feed):
        response = httpx.get(feed.url, timeout=15, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return parse_feed(response.content, feed.id)
    items, errors = [], []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(feeds)))) as pool:
        futures = {pool.submit(fetch, feed): feed for feed in feeds}
        for future in as_completed(futures):
            feed = futures[future]
            try:
                items.extend(future.result())
            except Exception as exc:
                errors.append({"feed_id": feed.id, "error": str(exc)[:240]})
    return items, errors
