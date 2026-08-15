from src.rights import is_download_allowed

CFG = {
    "rights": {
        "allow_creative_commons": True,
        "allowed_channel_ids": ["allowed"],
        "trend_only_channel_ids": [],
    }
}

def test_creative_commons_allowed():
    allowed, reason = is_download_allowed(
        {"channel_id": "x", "license": "creativeCommon"}, CFG
    )
    assert allowed
    assert reason == "youtube-creative-commons"

def test_explicit_channel_allowed():
    allowed, reason = is_download_allowed(
        {"channel_id": "allowed", "license": "youtube"}, CFG
    )
    assert allowed
    assert reason == "explicit-channel-allowlist"

def test_normal_youtube_is_trend_only():
    allowed, reason = is_download_allowed(
        {"channel_id": "other", "license": "youtube"}, CFG
    )
    assert not allowed
    assert reason == "trend-signal-only"
