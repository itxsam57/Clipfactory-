from __future__ import annotations

from datetime import datetime, timezone
import re


def _normalized_license(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def _wikimedia_rights_reason(video: dict) -> tuple[bool, str]:
    normalized = _normalized_license(video.get("license"))

    if normalized in {"public domain", "public-domain", "pd"}:
        return True, "wikimedia-public-domain"
    if normalized in {"cc0", "cc0 1.0"}:
        return True, "wikimedia-cc0"
    if normalized.startswith("cc by"):
        blocked_markers = ("-sa", " sa", "-nc", " nc", "-nd", " nd")
        if not any(marker in normalized for marker in blocked_markers):
            creator = str(video.get("channel_title") or "").strip()
            license_url = str(video.get("license_url") or "").strip()
            source_page = str(video.get("source_page_url") or "").strip()
            if (
                not creator
                or creator == "Wikimedia Commons contributor"
                or not license_url
                or not source_page.startswith("https://commons.wikimedia.org/")
            ):
                return False, "incomplete-cc-by-attribution"
            return True, "wikimedia-cc-by"

    return False, "unsupported-open-media-license"


def is_download_allowed(video: dict, cfg: dict) -> tuple[bool, str]:
    rights = cfg["rights"]
    source_type = video.get("source_type", "youtube")
    channel_id = video["channel_id"]
    license_name = video.get("license")

    if source_type == "wikimedia_commons":
        return _wikimedia_rights_reason(video)

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
