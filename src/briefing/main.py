import argparse
from datetime import datetime
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from .config import load_config
from .deliver import NtfyDeliverer, send_all
from .feeds import fetch_feeds
from .render import render_notes, render_topic
from .select import select_items
from .state import load_seen, save_seen
from .summarise import summarise

LOG = logging.getLogger("briefing")
load_dotenv()


def run(args):
    config = load_config(args.config)
    state_path = Path("state/seen.json")
    seen = load_seen(state_path)
    fetched, errors = fetch_feeds(config.feeds)
    now = datetime.now(ZoneInfo(config.settings.get("timezone", "UTC")))
    grouped, eligible = select_items(fetched, config.topics, seen, args.hours or config.settings["window_hours"], config.settings["max_items_per_topic"], now)
    notifications, shown_ids, dropped = [], set(), 0
    ntfy_cfg = config.settings["ntfy"]
    models = config.settings.get("models", {})
    provider = os.getenv("LLM_PROVIDER", "")
    for topic in config.topics:
        items = grouped[topic.name]
        if not items:
            continue
        if args.no_llm:
            bullets = [{"text": item.title, "item_numbers": [i]} for i, item in enumerate(items, 1)][:config.settings["max_bullets_per_topic"]]
        else:
            model = models.get(provider, "")
            if not model:
                raise ValueError(f"Set settings.models.{provider} in config")
            bullets = summarise(topic.name, items, config.settings["max_bullets_per_topic"], model)
        notification = render_topic(topic, bullets, items, now.strftime("%-d %b"), ntfy_cfg["priority"])
        if notification:
            notifications.append(notification)
            for bullet in bullets:
                for number in bullet["item_numbers"]:
                    if 1 <= number <= len(items):
                        shown_ids.add(items[number - 1].id)
    notes = render_notes(errors, len(fetched), len(eligible), dropped)
    if notes:
        notifications.append(notes)
    if args.dry_run:
        for n in notifications:
            print(f"TITLE: {n.title}\nMESSAGE:\n{n.message}\nCLICK: {n.click}\nACTIONS: {n.actions}\n")
        return
    deliverer = NtfyDeliverer(markdown=ntfy_cfg["markdown"])
    send_all(deliverer, notifications, ntfy_cfg["inter_message_delay_seconds"], LOG)
    save_seen(state_path, seen, shown_ids, config.settings["seen_retention_days"], now)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/topics.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--hours", type=float)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        run(args)
    except Exception as exc:
        LOG.error("Briefing failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
