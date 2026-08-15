# Design notes

## Low hardware

The heavy work runs on `ubuntu-latest` GitHub Actions. Your PC is only needed for the one-time browser OAuth bootstrap.

## Subtitle-first

The system does not download an entire long video before deciding what it wants.

It gets subtitles first, selects a timestamp, then downloads only that permitted section.

## No face tracking by default

Center crop is deliberately used to keep CPU and dependencies low. Face-aware tracking can be added later if the channel earns enough to justify the extra complexity.

## Original narration

Narration is generated locally with Piper TTS rather than paying a voice API.

## Fail closed

If:
- rights are unclear,
- subtitles are missing,
- credentials are missing,
- a platform approval is not available,

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
