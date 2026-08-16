# Open-Media Production Implementation Plan

**Goal:** Remove YouTube media extraction from ClipFactory's production critical path while retaining YouTube trend discovery.

## Task 1 — Commons source model and rights

- Implement `src/open_media.py` with strict license normalization and MediaWiki page-to-candidate conversion.
- Extend `src/rights.py` for Public Domain/CC0/CC BY Wikimedia sources.
- Run `tests/test_open_media.py` and `tests/test_rights.py` to green.

## Task 2 — Real Commons discovery

- Add `search_open_media(topic, max_results)` using the Wikimedia Commons MediaWiki API.
- Add `discover_open_media(cfg)` with topic merging, duplicate removal, and bounded results.
- Keep YouTube `discover()` focused on fresh trend signals only.
- Add mocked API tests for search normalization and dedupe.

## Task 3 — Direct-media processing

- Add FFprobe duration probing for direct HTTP media.
- Add FFmpeg direct segment extraction/transcoding to MP4.
- Add tests proving the command path does not invoke yt-dlp.

## Task 4 — Open-media editorial path

- Add `plan_open_short()` to Gemini editor.
- Use only source title/description/credit as source facts; trend titles are context, not evidence.
- Append deterministic license attribution to description.
- Add validation for narration/title/description/segment duration.

## Task 5 — Main pipeline integration

- `choose_candidates()` obtains YouTube trends plus Wikimedia footage separately.
- Apply central rights and duplicate checks to Wikimedia candidates.
- `process_one()` routes Wikimedia sources through direct-media planning and extraction.
- Preserve existing publishing and state semantics.

## Task 6 — Remove dead production dependencies

- Remove bgutil/WPC/EJS provider packages from default runtime once open-media path is proven.
- Keep the shared yt-dlp code only for optional explicitly-permitted/local YouTube sources if it remains useful; it must not be required by scheduled production.
- Restore workflow push trigger to `main` only before merge.

## Task 7 — Verification

- Full pytest suite green.
- Normal branch validation green with live factory skipped.
- Add a non-publishing live Commons smoke test on GitHub Actions: search, select, HEAD/probe direct URL, and FFmpeg a short segment.
- Only then run one controlled `[factory-test]` end-to-end publish.
- Inspect logs/artifact and confirm state changes only after successful publication.
