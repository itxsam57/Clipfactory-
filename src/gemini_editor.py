from __future__ import annotations

import json
import re

from google import genai
from google.genai import types

from .config import env


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Gemini did not return JSON")
    return json.loads(text[start : end + 1])


def _required_text(result: dict, key: str) -> str:
    value = str(result.get(key) or "").strip()
    if not value:
        raise ValueError(f"Gemini plan is missing required {key} text.")
    return value


def _clean_hashtags(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for raw in value[:8]:
        tag = str(raw or "").strip().replace(" ", "")
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = f"#{tag}"
        if tag not in out:
            out.append(tag[:80])
    return out


def _open_media_attribution(video: dict) -> str:
    title = str(video.get("title") or "Wikimedia Commons source").strip()
    creator = str(video.get("channel_title") or "Wikimedia Commons contributor").strip()
    license_name = str(video.get("license") or "").strip()
    source_page = str(video.get("source_page_url") or "").strip()
    license_url = str(video.get("license_url") or "").strip()

    parts = [f'Source footage: "{title}" — {creator}.']
    if license_name:
        parts.append(f"License: {license_name}.")
    if source_page:
        parts.append(f"Source: {source_page}")
    if license_url:
        parts.append(f"License terms: {license_url}")
    parts.append(
        "Footage edited/cropped for this Short; original narration, captions, and commentary added."
    )
    return " ".join(parts)


def finalize_open_plan(
    result: dict,
    video: dict,
    start_seconds: float,
    end_seconds: float,
) -> dict:
    """Validate model copy and attach non-AI-generated source attribution."""

    start = float(start_seconds)
    end = float(end_seconds)
    if start < 0 or end <= start:
        raise ValueError(f"Invalid open-media segment: {start}-{end}")

    plan = dict(result)
    plan["hook"] = _required_text(plan, "hook")
    plan["narration"] = _required_text(plan, "narration")
    plan["title"] = _required_text(plan, "title")[:100]
    base_description = _required_text(plan, "description")
    plan["hashtags"] = _clean_hashtags(plan.get("hashtags"))

    attribution = _open_media_attribution(video)
    plan["description"] = f"{base_description}\n\n{attribution}"[:5000]
    plan["start_seconds"] = start
    plan["end_seconds"] = end
    plan["source_creator"] = video["channel_title"]
    plan["source_url"] = video["source_page_url"]
    plan["source_license"] = video["license"]
    return plan


def plan_open_short(
    video: dict,
    cfg: dict,
    start_seconds: float,
    end_seconds: float,
) -> dict:
    """Create original commentary around rights-cleared open-media footage.

    YouTube trend titles are supplied only as audience-interest context. The
    model is explicitly forbidden from treating them as factual evidence.
    """

    client = genai.Client(api_key=env("GEMINI_API_KEY", required=True))
    model = env("GEMINI_MODEL", "gemini-2.5-flash")
    segment_seconds = max(1.0, float(end_seconds) - float(start_seconds))

    source_facts = {
        "title": video.get("title"),
        "creator": video.get("channel_title"),
        "description": video.get("description"),
        "credit": video.get("credit"),
        "license": video.get("license"),
        "matched_topics": video.get("matched_topics", []),
    }

    prompt = f"""
You are creating an ORIGINAL short-form educational/commentary video.

VERIFIED SOURCE FACTS
{json.dumps(source_facts, ensure_ascii=False)}

CURRENT YOUTUBE TREND SIGNALS
These are ONLY clues about current audience interest. They are NOT factual
sources, evidence, quotes, or permission to make claims about those videos.
{json.dumps(video.get('trend_context', []), ensure_ascii=False)}

The selected rights-cleared footage segment is approximately {segment_seconds:.1f} seconds long.

RULES
- Build a new explanation, insight, analysis, or educational angle.
- Use only VERIFIED SOURCE FACTS above as factual claims about the footage.
- Never invent what is visibly happening in frames you have not been shown.
- Never claim a trend title proves something or quote a trend creator.
- Do not impersonate the footage creator.
- Do not write license/source attribution; the application adds verified attribution itself.
- Narration must naturally fit about {segment_seconds:.0f} seconds at normal speech speed.
- Prefer a strong first sentence, clear payoff, and plain spoken English.
- Return JSON only.

JSON SHAPE
{{
  "hook": "short opening line",
  "narration": "original commentary narration",
  "title": "platform title",
  "description": "brief original description, without source/license attribution",
  "hashtags": ["#tag1", "#tag2", "#tag3"]
}}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )
    result = _extract_json(response.text)
    return finalize_open_plan(result, video, start_seconds, end_seconds)


def plan_short(video: dict, transcript: str, cfg: dict) -> dict:
    client = genai.Client(api_key=env("GEMINI_API_KEY", required=True))
    model = env("GEMINI_MODEL", "gemini-2.5-flash")
    lo = cfg["generation"]["target_seconds_min"]
    hi = cfg["generation"]["target_seconds_max"]

    prompt = f"""
You are editing an ORIGINAL short-form commentary/analysis video.

SOURCE METADATA
Title: {video['title']}
Creator: {video['channel_title']}
License gate result: {video.get('rights_reason')}
Current high-velocity trend signals (use only to understand audience interest; do not copy them):
{json.dumps(video.get('trend_context', []), ensure_ascii=False)}

RULES
- Do not merely summarize or repost.
- Create a new thesis, explanation, critique, educational angle, or analysis.
- The source footage is supporting evidence, not the final product.
- Never impersonate the source creator.
- Do not fabricate facts outside the supplied transcript.
- Select ONE source segment between {lo} and {hi} seconds.
- Narration should naturally fit approximately the same duration.
- For Creative Commons sources, attribution must name the creator and source video.
- Return JSON only.

JSON SHAPE
{{
  "start_seconds": 0,
  "end_seconds": 40,
  "hook": "short opening line",
  "narration": "original commentary narration",
  "title": "platform title",
  "description": "short description with source attribution",
  "hashtags": ["#tag1", "#tag2", "#tag3"]
}}

TRANSCRIPT WITH TIMESTAMPS
{transcript}
"""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )
    result = _extract_json(response.text)
    start = float(result["start_seconds"])
    end = float(result["end_seconds"])
    if end <= start or (end - start) < lo - 3 or (end - start) > hi + 8:
        raise ValueError(f"Invalid segment from editor: {start}-{end}")

    result["start_seconds"] = start
    result["end_seconds"] = end
    result["source_creator"] = video["channel_title"]
    result["source_url"] = video["url"]
    return result
