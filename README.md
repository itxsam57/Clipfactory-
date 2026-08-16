# ClipFactory Zero

Zero-budget, low-hardware automated short-form video pipeline.

## Production flow

```text
YouTube Data API trend discovery
→ viral velocity score
→ Wikimedia Commons open-video search
→ strict machine-readable rights gate
→ Gemini original commentary angle
→ FFmpeg direct selected segment
→ Piper narration
→ FFmpeg 9:16 render + captions
→ publish
→ save state only after a successful post
```

## Why this version is different

ClipFactory does not depend on downloading viral YouTube videos for production footage.

YouTube is used as a **trend sensor**: fresh public titles and performance signals help identify what audiences are currently interested in. Those trend titles are context only; they are not treated as factual evidence or reusable footage.

Production footage comes from Wikimedia Commons direct media URLs and must pass a deliberately strict automated rights policy:

- Public Domain — allowed
- CC0 — allowed
- CC BY — allowed with deterministic attribution
- CC BY-SA — blocked
- CC BY-NC — blocked
- CC BY-ND — blocked
- unclear/copyrighted media — blocked

This keeps the unattended pipeline much more reliable on GitHub-hosted runners and avoids building the product around YouTube player/bot-attestation behavior.

## Original-content rule

ClipFactory is designed around:

```text
rights-cleared supporting footage
+ original thesis/explanation
+ original narration
+ current trend context
+ verified source attribution
```

not:

```text
someone else's viral clip + captions
```

Gemini receives Commons source metadata as the factual basis for the script. YouTube trend titles are explicitly labeled as audience-interest context and must not be used as evidence or quoted as facts.

## Zero-cost components

- GitHub Actions: hosted compute and scheduling on a public repo
- YouTube Data API: fresh trend discovery
- Wikimedia Commons API: rights-cleared source discovery and direct media URLs
- Gemini API free tier: original commentary planning
- FFmpeg/FFprobe: direct segment extraction, transcoding and 9:16 rendering
- Piper: local narration on the runner
- YouTube Data API OAuth: upload
- repository JSON: duplicate/post state
- Cloudflare R2 free tier: optional temporary Meta media staging

## YouTube downloader experiment

`requirements-youtube-experimental.txt` preserves the yt-dlp + EJS + PO-token provider experiment (`bgutil-ytdlp-pot-provider` and `yt-dlp-getpot-wpc`) for future/local explicitly permitted sources.

It is **not** part of scheduled production. On GitHub/Azure runners, YouTube returned `LOGIN_REQUIRED` before token-backed media extraction could reliably proceed, so ClipFactory does not claim arbitrary unattended YouTube downloading from those cloud IPs.

## One-time local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env`.

Generate the YouTube OAuth refresh token if you are not using an existing valid one:

```powershell
python scripts\youtube_oauth_bootstrap.py
```

Test discovery/editor without rendering:

```powershell
python -m src.main --dry-run
```

Render without upload:

```powershell
python -m src.main --render-only
```

Full local run:

```powershell
python -m src.main
```

Live-check only the Commons direct-media source path:

```powershell
python scripts\smoke_open_media.py
```

## GitHub mode

The included workflow runs twice daily:

```text
03:17 UTC
15:17 UTC
```

Default limit:

```text
1 short per run
```

So the starting configuration publishes at most two Shorts per day.

Normal pushes to `main` are validation-only. Scheduled/manual runs execute the live factory. A commit containing `[factory-test]` is reserved for a deliberate end-to-end integration run.

## Platform defaults

```text
YouTube     ON
Instagram   OFF until Meta credentials are tested
Facebook    OFF until Page Reels adapter is live-tested
TikTok      OFF until approved API use case
X           OFF because API isn't $0
```

See `ACCOUNT_SETUP.md` for account and credential setup.
