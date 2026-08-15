from __future__ import annotations
import json, re
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
    return json.loads(text[start:end+1])

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
