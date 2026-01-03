import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"


def ensure_log_dir():
    LOG_DIR.mkdir(exist_ok=True)


def append_event(filename, payload):
    ensure_log_dir()
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {"timestamp": timestamp, **payload}
    path = LOG_DIR / filename
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    return record


def read_latest_event(filename):
    path = LOG_DIR / filename
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None


def read_recent_events(filename, limit=5):
    path = LOG_DIR / filename
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()
        if not lines:
            return []
        recent = lines[-limit:]
        return [json.loads(line) for line in reversed(recent)]
    except Exception:
        return []
