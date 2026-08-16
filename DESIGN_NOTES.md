# Design notes

## Low hardware

The heavy work runs on `ubuntu-latest` GitHub Actions. The user's PC is not part of the ongoing rendering pipeline.

## Separate trend intelligence from footage acquisition

YouTube is the production **trend sensor**, not the production media downloader. The YouTube Data API supplies fresh titles, view velocity, engagement, creators and matched topics.

Reusable footage is discovered independently from Wikimedia Commons through its MediaWiki API. ClipFactory requests direct media URLs plus machine-readable license and attribution metadata.

This separation avoids a brittle dependency on YouTube player extraction from cloud-hosted IP addresses while preserving the ability to react to current YouTube audience interest.

## Strict open-media rights

Automated production intentionally supports a narrower license set than the full Commons catalog:

- Public Domain
- CC0
- CC BY

ShareAlike, NonCommercial, NoDerivatives and unclear licenses fail closed. CC BY attribution is built from verified Commons metadata in application code rather than invented by Gemini.

## Direct media path

A Commons source is probed with FFprobe and a bounded segment is read directly by FFmpeg from `upload.wikimedia.org`, then transcoded to a predictable H.264/AAC MP4 before the vertical rendering step.

The production path does not require yt-dlp, browser cookies, PO tokens, a personal YouTube session, or local Whisper transcription.

The old yt-dlp/EJS/PO-token stack is retained only in `requirements-youtube-experimental.txt` for optional future/local explicitly permitted sources.

## Original narration

Gemini receives verified source metadata as the factual basis and YouTube trend titles only as audience-interest context. The model is told not to use trend titles as factual evidence. Piper generates narration locally on the GitHub runner rather than using a paid voice API.

## No face tracking by default

Center crop is deliberately used to keep CPU and dependencies low. Face-aware tracking can be considered after the pipeline proves it can earn enough to justify additional compute and complexity.

## CI safety

Normal pushes to `main` install dependencies and run tests only; they do not publish content. Scheduled runs and manual runs execute the live factory. A commit tagged `[factory-test]` is reserved for a deliberate controlled end-to-end integration run.

Persistent state changes only after a publisher returns a successful post, avoiding false duplicate history and no-op state commits.

## Fail closed

The system skips/fails rather than weakening safeguards when:

- license metadata is missing or unsupported,
- a direct media source cannot be decoded,
- credentials are missing,
- Gemini cannot produce a valid plan,
- or a destination platform approval is unavailable.

## Phase 2

After the first successful live posts, add:

- YouTube performance retrieval for published Shorts
- per-topic and per-hook performance
- automatic ranking-weight adjustment
- OAuth/token-health checks
- source-quality ranking based on successful renders and retention
- Meta Facebook Reels live-tested adapter
- TikTok adapter only if the developer app is approved
