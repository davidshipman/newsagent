from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


@dataclass(frozen=True)
class FeedConfig:
    id: str
    url: str


@dataclass(frozen=True)
class TopicConfig:
    name: str
    keywords: tuple[str, ...]
    tag: str | None = None
    exclude: tuple[str, ...] = ()
    feeds: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Config:
    settings: dict
    feeds: tuple[FeedConfig, ...]
    topics: tuple[TopicConfig, ...]


def load_config(path: str | Path) -> Config:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Unable to read config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Config must be a YAML mapping")
    settings = raw.get("settings")
    feeds_raw, topics_raw = raw.get("feeds"), raw.get("topics")
    if not isinstance(settings, dict) or not isinstance(feeds_raw, list) or not isinstance(topics_raw, list):
        raise ValueError("Config must contain settings, feeds, and topics")
    feed_map = {}
    feeds = []
    for feed in feeds_raw:
        if not isinstance(feed, dict) or not feed.get("id") or not isinstance(feed.get("url"), str):
            raise ValueError("Each feed needs an id and URL")
        parsed = urlparse(feed["url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Feed {feed['id']!r} has a bad URL: {feed['url']!r}")
        if feed["id"] in feed_map:
            raise ValueError(f"Duplicate feed id: {feed['id']}")
        feed_map[feed["id"]] = feed["url"]
        feeds.append(FeedConfig(feed["id"], feed["url"]))
    topics, names = [], set()
    for topic in topics_raw:
        if not isinstance(topic, dict) or not isinstance(topic.get("name"), str) or not topic["name"].strip():
            raise ValueError("Each topic needs a name")
        name = topic["name"].strip()
        if name.casefold() in names:
            raise ValueError(f"Duplicate topic name: {name}")
        names.add(name.casefold())
        keywords = topic.get("keywords")
        if not isinstance(keywords, list) or not keywords or any(not isinstance(k, str) or not k.strip() for k in keywords):
            raise ValueError(f"Topic {name!r} must have non-empty keywords")
        allowed = topic.get("feeds")
        if allowed is not None:
            if not isinstance(allowed, list):
                raise ValueError(f"Topic {name!r} feeds must be a list")
            unknown = set(allowed) - feed_map.keys()
            if unknown:
                raise ValueError(f"Topic {name!r} references unknown feeds: {', '.join(sorted(unknown))}")
        topics.append(TopicConfig(name, tuple(keywords), topic.get("tag"), tuple(topic.get("exclude", [])), tuple(allowed) if allowed is not None else None))
    ntfy = settings.get("ntfy", {})
    priority = ntfy.get("priority", 3)
    if not isinstance(priority, int) or not 1 <= priority <= 5:
        raise ValueError("settings.ntfy.priority must be between 1 and 5")
    for key, default in (("window_hours", 24), ("max_items_per_topic", 25), ("max_bullets_per_topic", 5), ("seen_retention_days", 14)):
        val = settings.get(key, default)
        if not isinstance(val, (int, float)) or val <= 0:
            raise ValueError(f"settings.{key} must be positive")
    settings = {**settings, "ntfy": {"priority": priority, "markdown": bool(ntfy.get("markdown", False)), "inter_message_delay_seconds": max(0, float(ntfy.get("inter_message_delay_seconds", 1)))}}
    return Config(settings, tuple(feeds), tuple(topics))
