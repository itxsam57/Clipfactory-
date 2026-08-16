from src.gemini_editor import finalize_open_plan


def _video():
    return {
        "title": "Example science footage",
        "channel_title": "Example Author",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "source_page_url": "https://commons.wikimedia.org/wiki/File:Example.webm",
    }


def test_finalize_open_plan_adds_deterministic_attribution():
    raw = {
        "hook": "A small detail changes the whole picture.",
        "narration": "This is an original educational explanation grounded in the supplied source metadata.",
        "title": "A Better Way to See This Idea",
        "description": "Original commentary using open footage.",
        "hashtags": ["#science", "#explained"],
    }

    plan = finalize_open_plan(raw, _video(), 2.0, 42.0)

    assert plan["start_seconds"] == 2.0
    assert plan["end_seconds"] == 42.0
    assert plan["source_creator"] == "Example Author"
    assert plan["source_url"].startswith("https://commons.wikimedia.org/")
    assert plan["source_license"] == "CC BY 4.0"
    assert "Example science footage" in plan["description"]
    assert "CC BY 4.0" in plan["description"]
    assert "creativecommons.org/licenses/by/4.0" in plan["description"]
    assert "commons.wikimedia.org/wiki/File:Example.webm" in plan["description"]
    assert "Footage edited" in plan["description"]
    assert "original narration" in plan["description"]


def test_finalize_open_plan_rejects_empty_narration():
    raw = {
        "hook": "Hook",
        "narration": "   ",
        "title": "Title",
        "description": "Description",
        "hashtags": [],
    }

    try:
        finalize_open_plan(raw, _video(), 0.0, 30.0)
    except ValueError as exc:
        assert "narration" in str(exc).lower()
    else:
        raise AssertionError("empty narration should be rejected")
