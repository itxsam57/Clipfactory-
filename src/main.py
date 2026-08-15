from __future__ import annotations

import argparse
import json
import tempfile
import traceback
from pathlib import Path

from .config import load_config
from .discover import discover
from .rights import is_download_allowed, source_recently_used
from .transcript import fetch_subtitles
from .gemini_editor import plan_short
from .tts import synthesize
from .media import download_segment, render_vertical
from .state import load_state, save_state, mark_source_used
from .publishers import youtube as youtube_pub
from .publishers import meta as meta_pub
from .publishers import tiktok as tiktok_pub


def choose_candidates(cfg, state):
    candidates = discover(cfg)
    chosen = []
    reuse_days = cfg["generation"]["min_days_before_source_reuse"]

    # Only genuinely fresh discovery results may influence the current-trend context.
    # Older Creative Commons material exists only as an evidence/source pool.
    trend_candidates = [
        candidate
        for candidate in candidates
        if candidate.get("discovery_class")
        in {"trend", "trend-and-creative-commons"}
    ]
    trend_context = [
        {
            "title": candidate["title"],
            "creator": candidate["channel_title"],
            "score": candidate["viral_score"],
            "matched_topics": candidate.get("matched_topics", []),
        }
        for candidate in trend_candidates[:10]
    ]

    source_pool_count = 0
    for candidate in candidates:
        candidate["trend_context"] = trend_context
        allowed, reason = is_download_allowed(candidate, cfg)
        candidate["download_allowed"] = allowed
        candidate["rights_reason"] = reason

        if not allowed:
            if candidate.get("discovery_class") in {
                "trend",
                "trend-and-creative-commons",
            }:
                print(f"TREND ONLY: {candidate['title']} ({reason})")
            continue

        source_pool_count += 1
        if source_recently_used(candidate["video_id"], state, reuse_days):
            print(f"SKIP RECENT SOURCE: {candidate['video_id']}")
            continue

        chosen.append(candidate)

    print(
        "DISCOVERY SUMMARY: "
        f"{len(trend_candidates)} fresh trend signals, "
        f"{source_pool_count} rights-cleared source candidates, "
        f"{len(chosen)} available after duplicate checks."
    )
    return chosen


def process_one(video, cfg, dry_run=False, render_only=False):
    print(
        f"SELECTED: {video['title']} | {video['rights_reason']} "
        f"| score={video['viral_score']}"
    )

    with tempfile.TemporaryDirectory(prefix="clipfactory-") as td:
        workdir = Path(td)
        transcript = fetch_subtitles(video["url"], workdir)
        if not transcript:
            raise RuntimeError(
                "No usable English subtitles; skipping to keep the pipeline lightweight."
            )

        plan = plan_short(video, transcript, cfg)
        print("PLAN:", json.dumps(plan, indent=2))

        if dry_run:
            return {"video": video, "plan": plan, "posts": []}

        segment = download_segment(
            video["url"], plan["start_seconds"], plan["end_seconds"], workdir
        )
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
        print("No rights-cleared candidates found this run.")
        save_state(state)
        return

    limit = cfg["generation"]["max_posts_per_run"]
    completed = 0

    for video in candidates:
        if completed >= limit:
            break
        try:
            result = process_one(
                video, cfg, dry_run=args.dry_run, render_only=args.render_only
            )
            if not args.dry_run:
                mark_source_used(
                    state,
                    video["video_id"],
                    {
                        "source_video_id": video["video_id"],
                        "source_url": video["url"],
                        "rights_reason": video["rights_reason"],
                        "posts": result.get("posts", []),
                        "file": result.get("file"),
                    },
                )
            completed += 1
        except Exception as exc:
            print(f"FAILED {video['video_id']}: {exc}")
            traceback.print_exc()

    save_state(state)


if __name__ == "__main__":
    main()
