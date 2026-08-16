from src import open_media


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _page(pageid, license_name="CC BY 4.0", index=1):
    return {
        "pageid": pageid,
        "index": index,
        "title": f"File:Technology demo {pageid}.webm",
        "imageinfo": [
            {
                "url": f"https://upload.wikimedia.org/demo-{pageid}.webm",
                "descriptionurl": f"https://commons.wikimedia.org/wiki/File:Technology_demo_{pageid}.webm",
                "mediatype": "VIDEO",
                "mime": "video/webm",
                "extmetadata": {
                    "LicenseShortName": {"value": license_name},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                    "Artist": {"value": "Demo Author"},
                    "ImageDescription": {"value": "Technology demonstration"},
                },
            }
        ],
    }


def test_search_open_media_uses_video_search_and_filters_unsafe(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {
                "query": {
                    "pages": [
                        _page(2, "CC BY-SA 4.0", index=1),
                        _page(1, "CC BY 4.0", index=2),
                    ]
                }
            }
        )

    monkeypatch.setattr(open_media.requests, "get", fake_get)

    results = open_media.search_open_media("technology explained", max_results=5)

    assert len(results) == 1
    assert results[0]["video_id"] == "commons-1"
    assert captured["url"] == open_media.COMMONS_API
    assert captured["params"]["gsrnamespace"] == "6"
    assert "filetype:video" in captured["params"]["gsrsearch"]
    assert "extmetadata" in captured["params"]["iiprop"]
    assert "ClipFactory" in captured["headers"]["User-Agent"]


def test_discover_open_media_deduplicates_and_merges_topics(monkeypatch):
    def fake_search(topic, max_results):
        base = {
            "source_type": "wikimedia_commons",
            "video_id": "commons-10",
            "title": "Shared source",
            "channel_id": "wikimedia-commons",
            "channel_title": "Author",
            "license": "CC BY 4.0",
            "url": "https://upload.wikimedia.org/shared.webm",
            "source_page_url": "https://commons.wikimedia.org/wiki/File:Shared.webm",
            "description": "Shared demo",
            "matched_topics": [topic],
            "viral_score": 2.0 if topic == "science" else 1.0,
        }
        return [base]

    monkeypatch.setattr(open_media, "search_open_media", fake_search)
    cfg = {
        "topics": ["science", "technology"],
        "discovery": {"open_media_results_per_topic": 4, "max_open_media_candidates": 10},
    }

    results = open_media.discover_open_media(cfg)

    assert len(results) == 1
    assert results[0]["matched_topics"] == ["science", "technology"]
    assert results[0]["viral_score"] == 2.0
