from __future__ import annotations

from html import unescape
import re
from typing import Iterable

import requests

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT = "ClipFactory/0.1 (https://github.com/itxsam57/Clipfactory-)"


def _plain(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", unescape(str(value)))
    return re.sub(r"\s+", " ", text).strip()


def _meta(extmetadata: dict, key: str) -> str:
    entry = extmetadata.get(key) or {}
    return _plain(entry.get("value"))


def _normalized_license(name: str | None) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def is_automation_safe_license(name: str | None) -> bool:
    """Return True only for licenses ClipFactory can automate safely.

    Public Domain and CC0 impose no attribution/share-alike constraint. CC BY is
    accepted because attribution metadata is retained and emitted by the
    publishing path. ShareAlike, NonCommercial, and NoDerivatives variants are
    deliberately rejected.
    """

    normalized = _normalized_license(name)
    if not normalized:
        return False

    if normalized in {"public domain", "public-domain", "pd", "cc0", "cc0 1.0"}:
        return True

    if normalized.startswith("cc by"):
        blocked_markers = ("-sa", " sa", "-nc", " nc", "-nd", " nd")
        return not any(marker in normalized for marker in blocked_markers)

    return False


def _is_direct_commons_url(url: str) -> bool:
    return url.startswith("https://upload.wikimedia.org/")


def page_to_candidate(page: dict, topic: str, rank: int) -> dict | None:
    infos = page.get("imageinfo") or []
    if not infos:
        return None

    info = infos[0]
    mime = str(info.get("mime") or "")
    mediatype = str(info.get("mediatype") or "")
    direct_url = str(info.get("url") or "")
    source_page_url = str(info.get("descriptionurl") or "")
    extmetadata = info.get("extmetadata") or {}
    license_name = _meta(extmetadata, "LicenseShortName")

    if mediatype.upper() != "VIDEO" or not mime.startswith("video/"):
        return None
    if not _is_direct_commons_url(direct_url):
        return None
    if not source_page_url.startswith("https://commons.wikimedia.org/"):
        return None
    if not is_automation_safe_license(license_name):
        return None

    page_id = page.get("pageid")
    if page_id is None:
        return None

    raw_title = str(page.get("title") or "Untitled Wikimedia video")
    title = re.sub(r"^File:", "", raw_title, flags=re.IGNORECASE)
    title = re.sub(r"\.(?:webm|ogv|ogg|mp4|mov|mkv)$", "", title, flags=re.IGNORECASE)

    artist = _meta(extmetadata, "Artist") or "Wikimedia Commons contributor"
    description = _meta(extmetadata, "ImageDescription") or title
    credit = _meta(extmetadata, "Credit")
    license_url = _meta(extmetadata, "LicenseUrl")
    attribution_required = _meta(extmetadata, "AttributionRequired").casefold() in {
        "true",
        "1",
        "yes",
    }

    # Search rank is a relevance signal, not a claim about real-world virality.
    relevance_score = round(max(0.05, 3.0 / (1.0 + max(rank, 0) * 0.30)), 4)

    return {
        "source_type": "wikimedia_commons",
        "video_id": f"commons-{page_id}",
        "title": title,
        "channel_id": "wikimedia-commons",
        "channel_title": artist,
        "license": license_name,
        "license_url": license_url,
        "attribution_required": attribution_required,
        "credit": credit,
        "description": description,
        "url": direct_url,
        "source_page_url": source_page_url,
        "mime": mime,
        "discovery_class": "open-media-source",
        "matched_topics": [topic],
        "viral_score": relevance_score,
        "has_captions": False,
    }


def search_open_media(topic: str, max_results: int = 10) -> list[dict]:
    """Search Wikimedia Commons for directly downloadable, safe-license videos."""

    requested = max(1, min(int(max_results), 25))
    # Ask for extra rows because the strict license filter intentionally removes
    # a significant portion of Commons search results.
    api_limit = min(50, max(requested * 3, 12))
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "search",
        "gsrsearch": f"{topic} filetype:video",
        "gsrnamespace": "6",
        "gsrlimit": str(api_limit),
        "gsrwhat": "text",
        "prop": "imageinfo",
        "iiprop": "url|mime|mediatype|extmetadata",
    }
    response = requests.get(
        COMMONS_API,
        params=params,
        headers={"User-Agent": _USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()

    pages: Iterable[dict] = response.json().get("query", {}).get("pages", [])
    ordered = sorted(pages, key=lambda page: int(page.get("index", 10_000)))

    out: list[dict] = []
    for rank, page in enumerate(ordered):
        candidate = page_to_candidate(page, topic, rank)
        if candidate is None:
            continue
        out.append(candidate)
        if len(out) >= requested:
            break
    return out


def discover_open_media(cfg: dict) -> list[dict]:
    dc = cfg.get("discovery", {})
    per_topic = int(dc.get("open_media_results_per_topic", 8))
    max_candidates = int(dc.get("max_open_media_candidates", 30))

    merged: dict[str, dict] = {}
    for topic in cfg.get("topics", []):
        try:
            results = search_open_media(topic, per_topic)
        except requests.RequestException as exc:
            print(f"WIKIMEDIA SEARCH FAILED for {topic!r}: {exc}")
            continue

        for candidate in results:
            existing = merged.get(candidate["video_id"])
            if existing is None:
                merged[candidate["video_id"]] = candidate
                continue

            topics = set(existing.get("matched_topics", []))
            topics.update(candidate.get("matched_topics", []))
            existing["matched_topics"] = sorted(topics)
            existing["viral_score"] = max(
                float(existing.get("viral_score", 0)),
                float(candidate.get("viral_score", 0)),
            )

    return sorted(
        merged.values(),
        key=lambda candidate: float(candidate.get("viral_score", 0)),
        reverse=True,
    )[:max_candidates]
