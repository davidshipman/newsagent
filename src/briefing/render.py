from dataclasses import dataclass
from datetime import datetime

MAX_BODY_BYTES = 4000


@dataclass(frozen=True)
class Notification:
    title: str
    message: str
    tags: list[str]
    priority: int
    click: str | None
    actions: list[dict]


def render_topic(topic, bullets, items, date_label: str, priority: int) -> Notification | None:
    indexed = {i: item for i, item in enumerate(items, 1)}
    usable = []
    for bullet in bullets:
        refs = [indexed[n] for n in bullet["item_numbers"] if n in indexed]
        if refs:
            usable.append((bullet["text"], refs))
    while usable:
        message = "\n\n".join(f"{text}\n{refs[0].url}" for text, refs in usable)
        if len(message.encode("utf-8")) <= MAX_BODY_BYTES:
            break
        usable.pop()
    if not usable:
        return None
    top_items = [refs[0] for _, refs in usable]
    actions, sources = [], set()
    for item in top_items:
        if item.feed_id in sources:
            continue
        sources.add(item.feed_id)
        actions.append({"action": "view", "label": item.feed_id, "url": item.url})
        if len(actions) == 3:
            break
    tag = [topic.tag] if topic.tag else []
    return Notification(f"{topic.name}, {date_label}", message, tag, priority, top_items[0].url, actions)


def render_notes(errors, fetched_count: int, filtered_count: int, dropped_count: int) -> Notification | None:
    if not errors and not dropped_count:
        return None
    rows = []
    for err in errors:
        rows.append(f"{err['feed_id']}: {err['error']}")
    rows.append(f"Items fetched: {fetched_count}; items after filtering: {filtered_count}.")
    if dropped_count:
        rows.append(f"Bullets dropped to fit notification limits: {dropped_count}.")
    message = "\n".join(rows)
    while len(message.encode("utf-8")) > MAX_BODY_BYTES:
        rows.pop(0)
        message = "\n".join(rows)
    return Notification("Briefing notes", message, [], 2, None, [])
