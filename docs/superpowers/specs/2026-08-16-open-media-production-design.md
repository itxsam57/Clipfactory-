# Open-Media Production Source Design

## Goal

Make ClipFactory reliable on GitHub-hosted runners by separating **trend discovery** from **footage acquisition**:

- YouTube Data API supplies fresh trend signals only.
- Wikimedia Commons supplies reusable video footage through direct file URLs and machine-readable license metadata.

This removes YouTube media extraction from the production critical path while preserving the original product goal: create original commentary/educational Shorts around current audience interests.

## Rights policy

Automated reuse is deliberately narrower than the full Commons catalog. A source is eligible only when its machine-readable license is one of:

- Public Domain
- CC0
- CC BY (any version)

ClipFactory rejects CC BY-SA, CC BY-NC, CC BY-ND, unclear, or copyrighted media. This keeps automated obligations simple and avoids silently creating ShareAlike, non-commercial, or no-derivatives conflicts.

## Components

### `discover.py`

Discovers only fresh YouTube trends and scores them by velocity/engagement. It does not search YouTube for downloadable footage.

### `open_media.py`

Queries the Wikimedia Commons MediaWiki API using file-namespace search plus `filetype:video`. It requests `imageinfo` with direct URL, MIME/media type, and extended metadata. It converts only automation-safe video files into normalized ClipFactory source candidates.

### `rights.py`

Keeps the existing YouTube rules for explicitly allowed sources, and adds strict Wikimedia decisions for Public Domain/CC0/CC BY. Open-media candidates never bypass this second rights check.

### `gemini_editor.py`

Adds an open-media planning path. It receives source title/description plus current YouTube trend context. It must create original narration without treating unrelated trend titles as factual evidence. Attribution is appended from source metadata, not invented by the model.

### `media.py`

Adds direct-media probing and segment extraction using FFprobe/FFmpeg against the Commons direct URL. No yt-dlp, cookies, browser session, or YouTube player endpoint is involved.

### `main.py`

Builds trend context from YouTube, obtains open-media candidates from Commons, applies rights/dedupe checks, then runs open-media planning -> direct segment -> Piper -> FFmpeg -> publishing.

## Data flow

1. Fetch fresh YouTube trend signals.
2. Search Commons for video footage matching configured topics.
3. Read machine-readable license, creator, credit, description, source-page URL, and direct media URL.
4. Reject unsupported licenses or non-video files.
5. Apply the central rights gate and source-reuse state gate.
6. Probe source duration and pick a bounded segment.
7. Ask Gemini for an original script based on source metadata, with trends used only as audience-interest context.
8. Extract the direct-media segment with FFmpeg.
9. Synthesize narration with Piper and render the vertical Short.
10. Publish through the existing platform adapter.
11. Persist state only after successful publication.

## Failure handling

- If Commons search/API fails for one topic, log it and continue other topics.
- If a direct media URL is unreachable, malformed, too short, or cannot be decoded, skip that source and try the next one.
- If license metadata is missing or unsupported, fail closed.
- No successful published post means no persistent state change.

## Testing

- Unit tests for license normalization and candidate conversion.
- Rights tests for accepted and rejected Commons licenses.
- Unit tests for direct-media FFmpeg command construction.
- GitHub validation run with factory skipped on normal pushes.
- Controlled `[factory-test]` only after validation is green.
- Completion requires evidence that a real Commons direct video is found and processed on the GitHub runner; a green unit-test-only run is not enough.

## YouTube downloader experiment

The PO-token stack (`bgutil-ytdlp-pot-provider`, WPC, Node/EJS, `mweb`) remains documented as an experiment, but it is not part of the production critical path. On GitHub/Azure egress, YouTube returned `LOGIN_REQUIRED` before token-backed media extraction could proceed. ClipFactory therefore does not depend on that unstable cloud-IP behavior for unattended production.
