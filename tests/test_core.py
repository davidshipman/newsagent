import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from briefing.config import TopicConfig, load_config
from briefing.feeds import Item, parse_feed
from briefing.render import render_notes, render_topic
from briefing.select import select_items
from briefing.state import load_seen, save_seen
from briefing.summarise import summarise

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


def test_parse_rss_atom_and_bad_xml():
    rss = parse_feed((FIXTURES / "rss.xml").read_bytes(), "rss", NOW)
    assert rss[0].id == "guid-a" and rss[0].summary_text == "Details here"
    assert rss[1].published_utc == NOW
    atom = parse_feed((FIXTURES / "atom.xml").read_bytes(), "atom", NOW)
    assert atom[0].url == "https://example.test/c"
    with pytest.raises(ValueError):
        parse_feed(b"not xml", "bad", NOW)


def test_config_validation(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("settings: {ntfy: {priority: 6}}\nfeeds: []\ntopics: []\n")
    with pytest.raises(ValueError, match="priority"):
        load_config(path)


def test_selection_seen_dedupe_exclude_and_feed_restriction():
    a = Item("1", "f1", "AI safety: New launch!", "https://x/a", NOW, "Details")
    dup = Item("2", "f2", "ai safety new launch", "https://x/b", NOW, "Details")
    old = Item("3", "f1", "AI safety old", "https://x/c", NOW - timedelta(days=2), "")
    topics = [TopicConfig("AI", ("ai safety",), exclude=("celebrity",), feeds=("f1",))]
    grouped, eligible = select_items([a, dup, old], topics, {}, 24, 25, NOW)
    assert grouped["AI"] == [a] and len(eligible) == 1
    assert select_items([a], topics, {"1": "seen"}, 24, 25, NOW)[0]["AI"] == []


def test_summarise_retries_and_discards_bad_reference():
    item = Item("1", "feed", "Headline", "https://x/a", NOW, "Summary")
    answers = iter(["not json", json.dumps({"bullets": [{"text": "Valid", "item_numbers": [1]}, {"text": "Bad", "item_numbers": [9]}]})])
    calls = []
    result = summarise("Topic", [item], 5, "model", lambda *args: (calls.append(args) or next(answers)))
    assert len(calls) == 2 and result == [{"text": "Valid", "item_numbers": [1]}]


def test_render_utf8_budget_order_actions_and_notes():
    items = [Item(str(i), f"f{i}", "Headline", f"https://x/{i}", NOW, "") for i in range(1, 5)]
    bullets = [{"text": "🙂漢" * 450, "item_numbers": [i]} for i in range(1, 5)]
    notification = render_topic(TopicConfig("Topic", ("x",), tag="robot"), bullets, items, "17 Nov", 3)
    assert len(notification.message.encode()) <= 4000
    assert notification.click == items[0].url
    assert len(notification.actions) <= 3
    assert notification.tags == ["robot"]
    assert render_notes([], 2, 1, 0) is None
    assert render_notes([{"feed_id": "broken", "error": "timeout"}], 2, 1, 0).priority == 2


def test_seen_state_prunes_old_entries(tmp_path):
    path = tmp_path / "state" / "seen.json"
    save_seen(path, {"old": (NOW - timedelta(days=20)).isoformat()}, ["new"], 14, NOW)
    assert load_seen(path).keys() == {"new"}
