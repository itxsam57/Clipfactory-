from src import main


def _cfg():
    return {
        "topics": ["science"],
        "rights": {
            "allow_creative_commons": True,
            "allowed_channel_ids": [],
            "trend_only_channel_ids": [],
        },
        "generation": {
            "target_seconds_min": 30,
            "target_seconds_max": 55,
            "min_days_before_source_reuse": 30,
            "voice": "en_US-lessac-medium",
            "source_audio_volume": 0.10,
            "max_posts_per_run": 1,
        },
        "publishing": {
            "youtube": False,
            "instagram": False,
            "facebook": False,
            "tiktok": False,
        },
    }


def _source():
    return {
        "source_type": "wikimedia_commons",
        "video_id": "commons-1",
        "title": "Open science video",
        "channel_id": "wikimedia-commons",
        "channel_title": "Commons Author",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "url": "https://upload.wikimedia.org/open.webm",
        "source_page_url": "https://commons.wikimedia.org/wiki/File:Open.webm",
        "description": "A science demonstration.",
        "matched_topics": ["science"],
        "viral_score": 2.0,
        "discovery_class": "open-media-source",
    }


def test_choose_candidates_separates_youtube_trends_from_open_media(monkeypatch):
    trend = {
        "source_type": "youtube",
        "video_id": "yt-1",
        "title": "Fresh science trend",
        "channel_id": "yt-channel",
        "channel_title": "Trend Creator",
        "license": "youtube",
        "viral_score": 99.0,
        "matched_topics": ["science"],
        "discovery_class": "trend",
    }

    monkeypatch.setattr(main, "discover", lambda cfg: [trend])
    monkeypatch.setattr(main, "discover_open_media", lambda cfg: [_source()])

    chosen = main.choose_candidates(_cfg(), {"used_sources": {}})

    assert len(chosen) == 1
    assert chosen[0]["video_id"] == "commons-1"
    assert chosen[0]["rights_reason"] == "wikimedia-cc-by"
    assert chosen[0]["trend_context"][0]["title"] == "Fresh science trend"


def test_open_media_dry_run_never_requests_youtube_transcript(monkeypatch):
    video = _source()
    video["rights_reason"] = "wikimedia-cc-by"
    video["trend_context"] = []

    monkeypatch.setattr(
        main,
        "fetch_subtitles",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("open media must not use YouTube transcript extraction")
        ),
    )
    monkeypatch.setattr(main, "probe_remote_duration", lambda url: 50.0)
    monkeypatch.setattr(
        main,
        "plan_open_short",
        lambda video, cfg, start, end: {
            "start_seconds": start,
            "end_seconds": end,
            "hook": "Hook",
            "narration": "Original narration",
            "title": "Title",
            "description": "Description",
            "hashtags": [],
            "source_creator": video["channel_title"],
            "source_url": video["source_page_url"],
        },
    )

    result = main.process_one(video, _cfg(), dry_run=True)

    assert result["video"]["source_type"] == "wikimedia_commons"
    assert result["plan"]["end_seconds"] > result["plan"]["start_seconds"]
