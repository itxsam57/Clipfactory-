from __future__ import annotations

import argparse
import json
import tempfile
import traceback
from pathlib import Path

from .config import load_config
from .discover import discover
from .open_media import discover_open_media
from .rights import is_download_allowed, source_recently_used
from .transcript import fetch_subtitles
from .gemini_editor import plan_short, plan_open_short
from .tts import synthesize
from .media import (
    download_segment,
    download_direct_segment,
    probe_remote_duration,
    render_vertical,
)
from .state import load_state, save_state, mark_source_used
from .publishers import youtube as youtube_pub
from .publishers import meta as meta_pub
from .publishers import tiktok as tiktok_pub


def _trend_context(trends: list[dict], limit: int = 10) -> list[dict]:
    return [
        {
            "title": candidate["title"],
            "creator": candidate["channel_title"],
            "score": candidate["viral_score"],
            "matched_topics": candidate.get("matched_topics", []),
        }
        for candidate in trends[:limit]
    ]


def choose_candidates(cfg, state):
    """Combine fresh YouTube interest signals with independent open footage."""

    try:
        trends = discover(cfg)
    except Exception as exc:
        print(f"TREND DISCOVERY FAILED: {exc}")
        trends = []

    sources = discover_open_media(cfg)
    trend_context = _trend_context(trends)
    reuse_days = cfg["generation"]["min_days_before_source_reuse"]

    for trend in trends[:10]:
        print(f"TREND SIGNAL: {trend['title']} | score={trend['viral_score']}")

    chosen: list[dict] = []
    rights_cleared = 0
    for candidate in sources:
        candidate["trend_context"] = trend_context
        allowed, reason = is_download_allowed(candidate, cfg)
        candidate["download_allowed"] = allowed
        candidate["rights_reason"] = reason

        if not allowed:
            print(
                f"BLOCK OPEN SOURCE: {candidate.get('video_id')} "
                f"({reason})"
            )
            continue

        rights_cleared += 1
        if source_recently_used(candidate["video_id"], state, reuse_days):
            print(f"SKIP RECENT SOURCE: {candidate['video_id']}")
            continue

        chosen.append(candidate)

    chosen.sort(
        key=lambda candidate: (
            len(candidate.get("matched_topics", [])),
            float(candidate.get("viral_score", 0)),
        ),
        reverse=True,
    )

    print(
        "DISCOVERY SUMMARY: "
        f"{len(trends)} fresh YouTube trend signals, "
        f"{len(sources)} open-media candidates, "
        f"{rights_cleared} rights-cleared, "
        f"{len(chosen)} available after duplicate checks."
    )
    return chosen


def _open_segment_bounds(duration: float, cfg: dict) -> tuple[float, float]:
    lo = float(cfg["generation"]["target_seconds_min"])
    hi = float(cfg["generation"]["target_seconds_max"])
    duration = float(duration)

    if duration < max(5.0, lo - 3.0):
        raise RuntimeError(
            f"Open-media source is too short ({duration:.1f}s) for the "
            f"{lo:.0f}-{hi:.0f}s target."
        )

    target = min(hi, duration)
    if duration <= target:
        start = 0.0
    else:
        # Skip a small intro portion on longer files while keeping the choice
        # deterministic and safely within the source duration.
        start = min(duration - target, duration * 0.10)

    end = min(duration, start + target)
    return round(start, 3), round(end, 3)


def _plan_and_segment_open_media(video: dict, cfg: dict, workdir: Path, dry_run: bool):
    duration = probe_remote_duration(video["url"])
    start, end = _open_segment_bounds(duration, cfg)
    plan = plan_open_short(video, cfg, start, end)
    print("PLAN:", json.dumps(plan, indent=2, ensure_ascii=False))

    if dry_run:
        return plan, None

    segment = download_direct_segment(video["url"], start, end, workdir)
    return plan, segment


def _plan_and_segment_youtube(video: dict, cfg: dict, workdir: Path, dry_run: bool):
    """Optional legacy path for an explicitly permitted YouTube source.

    Scheduled production discovery does not place YouTube videos in the source
    pool; this remains only for future/local explicitly permitted use.
    """

    transcript = fetch_subtitles(video["url"], workdir)
    if not transcript:
        raise RuntimeError("No usable speech transcript could be produced.")

    plan = plan_short(video, transcript, cfg)
    print("PLAN:", json.dumps(plan, indent=2, ensure_ascii=False))

    if dry_run:
        return plan, None

    segment = download_segment(
        video["url"], plan["start_seconds"], plan["end_seconds"], workdir
    )
    return plan, segment


def process_one(video, cfg, dry_run=False, render_only=False):
    print(
        f"SELECTED: {video['title']} | {video['rights_reason']} "
        f"| source={video.get('source_type', 'youtube')} "
        f"| score={video['viral_score']}"
    )

    with tempfile.TemporaryDirectory(prefix="clipfactory-") as td:
        workdir = Path(td)

        if video.get("source_type") == "wikimedia_commons":
            plan, segment = _plan_and_segment_open_media(
                video, cfg, workdir, dry_run=dry_run
            )
        else:
            plan, segment = _plan_and_segment_youtube(
                video, cfg, workdir, dry_run=dry_run
            )

        if dry_run:
            return {"video": video, "plan": plan, "posts": []}

        if segment is None:
            raise RuntimeError("Media segment was not produced.")

        narration = synthesize(
            plan["narration"], cfg["generation"]["voice"], workdir
        )
        final = render_vertical(
            segment,
            narration,
            plan["narration"],
            workdir,
            source_volume=cfg["generation"].get("source_audio_volume", 0.10),
        )

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        permanent = output_dir / f"{video['video_id']}.mp4"
        permanent.write_bytes(final.read_bytes())

        posts = []
        if render_only:
            return {
                "video": video,
                "plan": plan,
                "file": str(permanent),
                "posts": posts,
            }

        pub = cfg["publishing"]

        if pub.get("youtube"):
            posts.append(youtube_pub.upload(permanent, plan))

        staged_url = None
        staged_key = None
        if pub.get("instagram") or pub.get("facebook"):
            staged_url, staged_key = meta_pub.stage_public(permanent)
            try:
                if pub.get("instagram"):
                    posts.append(meta_pub.publish_instagram_reel(staged_url, plan))
                if pub.get("facebook"):
                    posts.append(meta_pub.publish_facebook_reel(staged_url, plan))
            finally:
                if staged_key:
                    meta_pub.cleanup(staged_key)

        if pub.get("tiktok"):
            posts.append(tiktok_pub.upload(permanent, plan))

        return {
            "video": video,
            "plan": plan,
            "file": str(permanent),
            "posts": posts,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    state = load_state()
    candidates = choose_candidates(cfg, state)

    if not candidates:
        print("No rights-cleared open-media candidates found this run.")
        return

    limit = cfg["generation"]["max_posts_per_run"]
    completed = 0
    state_dirty = False

    for video in candidates:
        if completed >= limit:
            break
        try:
            result = process_one(
                video, cfg, dry_run=args.dry_run, render_only=args.render_only
            )
            if (
                not args.dry_run
                and not args.render_only
                and result.get("posts")
            ):
                mark_source_used(
                    state,
                    video["video_id"],
                    {
                        "source_video_id": video["video_id"],
                        "source_url": video.get("source_page_url", video["url"]),
                        "rights_reason": video["rights_reason"],
                        "license": video.get("license"),
                        "posts": result.get("posts", []),
                        "file": result.get("file"),
                    },
                )
                state_dirty = True
            completed += 1
        except Exception as exc:
            print(f"FAILED {video['video_id']}: {exc}")
            traceback.print_exc()

    if state_dirty:
        save_state(state)
    else:
        print("No successful published post changed persistent state.")


if __name__ == "__main__":
    main()
