from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import requests

from .config import env

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _search(
    topic: str,
    published_after: str,
    max_results: int,
    region_code: str,
    key: str,
) -> list[str]:
    response = requests.get(
        f"{YOUTUBE_API}/search",
        params={
            "part": "snippet",
            "type": "video",
            "q": topic,
            "publishedAfter": published_after,
            "order": "viewCount",
            "maxResults": min(50, max_results),
            "regionCode": region_code,
            "key": key,
        },
        timeout=30,
    )
    response.raise_for_status()
    return [
        item["id"]["videoId"]
        for item in response.json().get("items", [])
        if item.get("id", {}).get("videoId")
    ]


def discover(cfg: dict) -> list[dict]:
    """Discover fresh YouTube videos strictly as trend signals.

    Production footage is discovered separately by ``open_media.py``. Keeping
    this function trend-only halves the previous search workload and prevents a
    YouTube media URL from accidentally entering the scheduled source pool.
    """

    key = env("YOUTUBE_API_KEY", required=True)
    dc = cfg["discovery"]
    now = datetime.now(timezone.utc)
    region = dc.get("region_code", "US")
    published_after = _iso(now - timedelta(hours=dc["lookback_hours"]))

    ids: list[str] = []
    metadata: dict[str, set[str]] = {}

    for topic in cfg["topics"]:
        for video_id in _search(
            topic,
            published_after,
            dc["results_per_topic"],
            region,
            key,
        ):
            if video_id not in ids:
                ids.append(video_id)
            metadata.setdefault(video_id, set()).add(topic)

    ids = ids[: dc["max_candidates"]]
    if not ids:
        return []

    out: list[dict] = []
    for start in range(0, len(ids), 50):
        batch = ids[start : start + 50]
        response = requests.get(
            f"{YOUTUBE_API}/videos",
            params={
                "part": "snippet,statistics,status",
                "id": ",".join(batch),
                "key": key,
            },
            timeout=30,
        )
        response.raise_for_status()

        for item in response.json().get("items", []):
            video_id = item["id"]
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            published = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )
            age_hours = max((now - published).total_seconds() / 3600, 1.0)
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            if views < dc["min_views"]:
                continue

            velocity = views / age_hours
            engagement = (likes + comments * 2) / max(views, 1)
            score = (
                math.log10(max(velocity, 1)) * 0.72
                + math.log10(max(views, 1)) * 0.18
                + engagement * 10
            )

            out.append(
                {
                    "source_type": "youtube",
                    "video_id": video_id,
                    "title": snippet["title"],
                    "channel_id": snippet["channelId"],
                    "channel_title": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "age_hours": round(age_hours, 2),
                    "velocity": round(velocity, 2),
                    "viral_score": round(score, 4),
                    "license": item.get("status", {}).get("license"),
                    "discovery_class": "trend",
                    "matched_topics": sorted(metadata.get(video_id, set())),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )

    return sorted(
        out,
        key=lambda candidate: candidate["viral_score"],
        reverse=True,
    )
