from __future__ import annotations
import json
from datetime import datetime, timezone
from .config import ROOT

STATE_PATH = ROOT / "data" / "state.json"

def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"used_sources": {}, "posts": [], "last_run": None}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))

def save_state(state: dict) -> None:
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

def mark_source_used(state: dict, video_id: str, post_record: dict) -> None:
    state.setdefault("used_sources", {})[video_id] = datetime.now(timezone.utc).isoformat()
    state.setdefault("posts", []).append(post_record)
