from __future__ import annotations
from datetime import datetime, timedelta, timezone
import math, requests
from .config import env

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def _search(topic: str, published_after: str, dc: dict, key: str, cc_only: bool) -> list[str]:
    params = {
        "part": "snippet",
        "type": "video",
        "q": topic,
        "publishedAfter": published_after,
        "order": "viewCount",
        "maxResults": min(50, dc["results_per_topic"]),
        "regionCode": dc.get("region_code", "US"),
        "key": key,
    }
    if cc_only:
        params["videoLicense"] = "creativeCommon"

    r = requests.get(f"{YOUTUBE_API}/search", params=params, timeout=30)
    r.raise_for_status()
    return [
        item["id"]["videoId"]
        for item in r.json().get("items", [])
        if item.get("id", {}).get("videoId")
    ]

def discover(cfg: dict) -> list[dict]:
    key = env("YOUTUBE_API_KEY", required=True)
    dc = cfg["discovery"]
    published_after = _iso(
        datetime.now(timezone.utc) - timedelta(hours=dc["lookback_hours"])
    )

    ids = []
    source_class = {}

    for topic in cfg["topics"]:
        # General high-performing videos = trend context.
        for vid in _search(topic, published_after, dc, key, cc_only=False):
            if vid not in ids:
                ids.append(vid)
            source_class.setdefault(vid, "trend")

        # CC search = pool we can potentially use as source evidence.
        for vid in _search(topic, published_after, dc, key, cc_only=True):
            if vid not in ids:
                ids.append(vid)
            source_class[vid] = "creative-commons-candidate"

    # General results and CC results share one metadata batch.
    ids = ids[: max(dc["max_candidates"], len(cfg["topics"]) * dc["results_per_topic"] * 2)]
    if not ids:
        return []

    out = []
    now = datetime.now(timezone.utc)

    # videos.list supports max 50 IDs per request.
    for start in range(0, len(ids), 50):
        batch = ids[start:start+50]
        r = requests.get(
            f"{YOUTUBE_API}/videos",
            params={
                "part": "snippet,statistics,status,contentDetails",
                "id": ",".join(batch),
                "key": key,
            },
            timeout=30,
        )
        r.raise_for_status()

        for item in r.json().get("items", []):
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            published = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )
            age_hours = max(
                (now - published).total_seconds() / 3600, 1.0
            )
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            if views < dc["min_views"]:
                continue

            velocity = views / age_hours
            engagement = (likes + comments * 2) / max(views, 1)

            # Keep the score explainable and cheap.
            score = (
                math.log10(max(velocity, 1)) * 0.72
                + math.log10(max(views, 1)) * 0.18
                + engagement * 10
            )

            out.append({
                "video_id": item["id"],
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
                "discovery_class": source_class.get(item["id"], "trend"),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
            })

    return sorted(out, key=lambda x: x["viral_score"], reverse=True)
