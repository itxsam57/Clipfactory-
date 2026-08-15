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
    *,
    cc_only: bool,
) -> list[str]:
    params = {
        "part": "snippet",
        "type": "video",
        "q": topic,
        "publishedAfter": published_after,
        "order": "viewCount",
        "maxResults": min(50, max_results),
        "regionCode": region_code,
        "key": key,
    }
    if cc_only:
        params["videoLicense"] = "creativeCommon"

    response = requests.get(f"{YOUTUBE_API}/search", params=params, timeout=30)
    response.raise_for_status()
    return [
        item["id"]["videoId"]
        for item in response.json().get("items", [])
        if item.get("id", {}).get("videoId")
    ]


def discover(cfg: dict) -> list[dict]:
    """Discover two intentionally separate pools.

    Trend pool:
        Very recent, high-performing YouTube videos. These are signals only unless
        they independently pass the rights gate.

    Source pool:
        A wider Creative Commons search window. These videos can provide source
        evidence while the fresh trend pool tells Gemini what audiences are
        responding to now.

    Keeping these pools separate avoids the bad assumption that a currently viral
    video must itself be reusable for ClipFactory to make a timely original Short.
    """

    key = env("YOUTUBE_API_KEY", required=True)
    dc = cfg["discovery"]
    now = datetime.now(timezone.utc)
    region = dc.get("region_code", "US")

    trend_after = _iso(now - timedelta(hours=dc["lookback_hours"]))
    source_after = _iso(now - timedelta(days=dc.get("source_lookback_days", 730)))

    trend_ids: list[str] = []
    source_ids: list[str] = []
    metadata: dict[str, dict] = {}

    for topic in cfg["topics"]:
        for video_id in _search(
            topic,
            trend_after,
            dc["results_per_topic"],
            region,
            key,
            cc_only=False,
        ):
            if video_id not in trend_ids:
                trend_ids.append(video_id)
            meta = metadata.setdefault(video_id, {"topics": set(), "classes": set()})
            meta["topics"].add(topic)
            meta["classes"].add("trend")

        for video_id in _search(
            topic,
            source_after,
            dc.get("source_results_per_topic", dc["results_per_topic"]),
            region,
            key,
            cc_only=True,
        ):
            if video_id not in source_ids:
                source_ids.append(video_id)
            meta = metadata.setdefault(video_id, {"topics": set(), "classes": set()})
            meta["topics"].add(topic)
            meta["classes"].add("creative-commons-candidate")

    trend_ids = trend_ids[: dc["max_candidates"]]
    source_ids = source_ids[: dc.get("max_source_candidates", 40)]

    ids = trend_ids + [video_id for video_id in source_ids if video_id not in trend_ids]
    if not ids:
        return []

    out: list[dict] = []

    # videos.list accepts at most 50 IDs at a time.
    for start in range(0, len(ids), 50):
        batch = ids[start : start + 50]
        response = requests.get(
            f"{YOUTUBE_API}/videos",
            params={
                "part": "snippet,statistics,status,contentDetails",
                "id": ",".join(batch),
                "key": key,
            },
            timeout=30,
        )
        response.raise_for_status()

        for item in response.json().get("items", []):
            video_id = item["id"]
            source_meta = metadata.get(video_id, {"topics": set(), "classes": set()})
            classes = source_meta["classes"]
            is_source_candidate = "creative-commons-candidate" in classes

            snippet = item["snippet"]
            stats = item.get("statistics", {})
            published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            age_hours = max((now - published).total_seconds() / 3600, 1.0)
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            minimum_views = (
                dc.get("source_min_views", 100)
                if is_source_candidate
                else dc["min_views"]
            )
            if views < minimum_views:
                continue

            velocity = views / age_hours
            engagement = (likes + comments * 2) / max(views, 1)
            score = (
                math.log10(max(velocity, 1)) * 0.72
                + math.log10(max(views, 1)) * 0.18
                + engagement * 10
            )

            if is_source_candidate and "trend" in classes:
                discovery_class = "trend-and-creative-commons"
            elif is_source_candidate:
                discovery_class = "creative-commons-candidate"
            else:
                discovery_class = "trend"

            out.append(
                {
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
                    "discovery_class": discovery_class,
                    "matched_topics": sorted(source_meta["topics"]),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )

    # The filter in choose_candidates separates trend signals from reusable sources.
    # Sorting once here keeps both pools deterministic.
    return sorted(out, key=lambda candidate: candidate["viral_score"], reverse=True)
