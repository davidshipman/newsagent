import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit


def _title_key(title: str) -> str:
    return re.sub(r"[^\w]+", "", title.casefold())


def select_items(items, topics, seen, window_hours: float, max_items_per_topic: int, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    eligible, urls, titles = [], set(), set()
    for item in sorted(items, key=lambda i: i.published_utc, reverse=True):
        if item.id in seen or item.published_utc < cutoff or item.published_utc > now + timedelta(minutes=5):
            continue
        normalized_url = urlunsplit((*urlsplit(item.url)[:3], "", "")) if item.url else ""
        title = _title_key(item.title)
        if (normalized_url and normalized_url in urls) or (title and title in titles):
            continue
        if normalized_url:
            urls.add(normalized_url)
        if title:
            titles.add(title)
        eligible.append(item)
    result = {}
    for topic in topics:
        matches = []
        for item in eligible:
            if topic.feeds is not None and item.feed_id not in topic.feeds:
                continue
            text = f"{item.title} {item.summary_text}".casefold()
            if any(word.casefold() in text for word in topic.exclude):
                continue
            if any(word.casefold() in text for word in topic.keywords):
                matches.append(item)
        result[topic.name] = matches[:max_items_per_topic]
    return result, eligible
