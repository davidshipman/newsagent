import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_seen(path: str | Path) -> dict[str, str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}


def save_seen(path: str | Path, seen: dict[str, str], item_ids, retention_days: int, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)
    kept = {}
    for key, timestamp in seen.items():
        try:
            if datetime.fromisoformat(timestamp) >= cutoff:
                kept[key] = timestamp
        except (TypeError, ValueError):
            continue
    for item_id in item_ids:
        kept[item_id] = now.isoformat()
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(kept, indent=2, sort_keys=True) + "\n", encoding="utf-8")
