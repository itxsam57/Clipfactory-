from src.open_media import is_automation_safe_license, page_to_candidate


def _page(
    license_name="CC BY 4.0",
    *,
    mediatype="VIDEO",
    mime="video/webm",
    artist="Example Author",
    license_url="https://creativecommons.org/licenses/by/4.0/",
):
    return {
        "pageid": 123,
        "title": "File:Example technology.webm",
        "imageinfo": [
            {
                "url": "https://upload.wikimedia.org/example.webm",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example_technology.webm",
                "mediatype": mediatype,
                "mime": mime,
                "extmetadata": {
                    "LicenseShortName": {"value": license_name},
                    "LicenseUrl": {"value": license_url},
                    "Artist": {"value": artist},
                    "Credit": {"value": "Example credit"},
                    "ImageDescription": {"value": "A short technology demonstration."},
                    "AttributionRequired": {"value": "true"},
                },
            }
        ],
    }


def test_automation_safe_licenses_are_deliberately_narrow():
    assert is_automation_safe_license("Public domain")
    assert is_automation_safe_license("CC0")
    assert is_automation_safe_license("CC BY 4.0")
    assert is_automation_safe_license("CC BY 2.0")
    assert not is_automation_safe_license("CC BY-SA 4.0")
    assert not is_automation_safe_license("CC BY-NC 4.0")
    assert not is_automation_safe_license("Copyrighted")
    assert not is_automation_safe_license("")


def test_page_to_candidate_returns_direct_open_video():
    candidate = page_to_candidate(_page(), "technology explained", rank=0)

    assert candidate is not None
    assert candidate["source_type"] == "wikimedia_commons"
    assert candidate["video_id"] == "commons-123"
    assert candidate["url"].startswith("https://upload.wikimedia.org/")
    assert candidate["source_page_url"].startswith("https://commons.wikimedia.org/")
    assert candidate["license"] == "CC BY 4.0"
    assert candidate["channel_title"] == "Example Author"
    assert candidate["description"] == "A short technology demonstration."
    assert candidate["matched_topics"] == ["technology explained"]


def test_page_to_candidate_rejects_sharealike_and_non_video():
    assert page_to_candidate(_page("CC BY-SA 4.0"), "science", rank=0) is None
    assert page_to_candidate(_page(mediatype="BITMAP", mime="image/jpeg"), "science", rank=0) is None


def test_cc_by_requires_creator_and_license_url_for_automatic_attribution():
    assert page_to_candidate(_page(artist=""), "science", rank=0) is None
    assert page_to_candidate(_page(license_url=""), "science", rank=0) is None


def test_public_domain_does_not_require_cc_by_attribution_fields():
    candidate = page_to_candidate(
        _page("Public domain", artist="", license_url=""),
        "science",
        rank=0,
    )
    assert candidate is not None
    assert candidate["license"] == "Public domain"
