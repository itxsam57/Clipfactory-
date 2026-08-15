# Design notes

## Low hardware

The heavy work runs on `ubuntu-latest` GitHub Actions. Your PC is only needed for the one-time browser OAuth bootstrap.

## Transcript-first, transcription fallback

The system tries creator/automatic caption tracks first because they are fast and cheap. If a rights-cleared source has no usable caption track, it downloads audio and transcribes locally on the GitHub runner with CPU Whisper instead of depending on a paid speech API.

## No face tracking by default

Center crop is deliberately used to keep CPU and dependencies low. Face-aware tracking can be added later after the pipeline proves it can earn.

## Original narration

Narration is generated locally with Piper TTS rather than paying a voice API.

## CI safety

Normal pushes to `main` install dependencies and run tests only. They do not publish content. Scheduled runs and manual runs execute the live factory. A commit tagged `[factory-test]` is reserved for a deliberate controlled end-to-end integration run.

Persistent state changes only after a successful published post, avoiding no-op state commits and reducing Git races.

## Fail closed

If:
- rights are unclear,
- credentials are missing,
- source speech cannot be transcribed,
- or a platform approval is not available,

the system skips/fails rather than trying to bypass a platform.

## Phase 2

After the first successful live posts, add:

- YouTube performance retrieval
- per-topic performance
- per-hook performance
- automatic ranking-weight adjustment
- token-health checks
- Meta Facebook Reels live-tested adapter
- TikTok adapter only if the developer app is approved
