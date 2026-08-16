from src.gemini_editor import DEFAULT_GEMINI_MODEL


def test_default_gemini_model_is_current_free_tier_flash():
    assert DEFAULT_GEMINI_MODEL == "gemini-3.5-flash"
