from src.rights import is_download_allowed

CFG = {
    "rights": {
        "allow_creative_commons": True,
        "allowed_channel_ids": ["allowed"],
        "trend_only_channel_ids": [],
    }
}


def _valid_cc_by():
    return {
        "source_type": "wikimedia_commons",
        "channel_id": "wikimedia-commons",
        "channel_title": "Example Author",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "source_page_url": "https://commons.wikimedia.org/wiki/File:Example.webm",
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


def test_wikimedia_cc_by_allowed():
    allowed, reason = is_download_allowed(_valid_cc_by(), CFG)
    assert allowed
    assert reason == "wikimedia-cc-by"


def test_wikimedia_cc_by_requires_complete_attribution_metadata():
    base = _valid_cc_by()

    for broken in (
        dict(base, channel_title=""),
        dict(base, license_url=""),
        dict(base, source_page_url=""),
    ):
        allowed, reason = is_download_allowed(broken, CFG)
        assert not allowed
        assert reason == "incomplete-cc-by-attribution"


def test_wikimedia_public_domain_allowed():
    allowed, reason = is_download_allowed(
        {
            "source_type": "wikimedia_commons",
            "channel_id": "wikimedia-commons",
            "license": "Public domain",
        },
        CFG,
    )
    assert allowed
    assert reason == "wikimedia-public-domain"


def test_wikimedia_sharealike_blocked():
    allowed, reason = is_download_allowed(
        {
            "source_type": "wikimedia_commons",
            "channel_id": "wikimedia-commons",
            "license": "CC BY-SA 4.0",
        },
        CFG,
    )
    assert not allowed
    assert reason == "unsupported-open-media-license"
