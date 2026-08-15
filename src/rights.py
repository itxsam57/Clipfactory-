from __future__ import annotations
from datetime import datetime, timezone

def is_download_allowed(video: dict, cfg: dict) -> tuple[bool, str]:
    rights = cfg["rights"]
    channel_id = video["channel_id"]
    license_name = video.get("license")

    if channel_id in set(rights.get("allowed_channel_ids", [])):
        return True, "explicit-channel-allowlist"

    if rights.get("allow_creative_commons", True) and license_name == "creativeCommon":
        return True, "youtube-creative-commons"

    return False, "trend-signal-only"

def source_recently_used(video_id: str, state: dict, min_days: int) -> bool:
    raw = state.get("used_sources", {}).get(video_id)
    if not raw:
        return False
    try:
        used = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return True
    age_days = (datetime.now(timezone.utc) - used).total_seconds() / 86400
    return age_days < min_days
