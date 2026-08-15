# ClipFactory Zero

Zero-budget, low-hardware automated short-form video pipeline.

## What it does

```text
YouTube discovery
→ viral velocity score
→ rights gate
→ subtitles only
→ Gemini original angle
→ download only selected permitted segment
→ Piper narration
→ FFmpeg 9:16 render
→ publish
→ save state
```

## Why this version is different

It does not build a straight clipping/repost farm.

Source footage can be downloaded only when:

1. YouTube reports the video as Creative Commons, or
2. you explicitly allow-list a creator/channel you have permission to reuse.

Other high-performing creators can still be used as **trend signals** without downloading their footage.

This makes the system much more suitable for monetization policies that reject minimally changed reused content.

## Zero-cost components

- GitHub Actions: rendering/scheduling on a public repo
- YouTube Data API: discovery/licensing/upload/metrics
- Gemini API free tier: text analysis
- yt-dlp: subtitles + selected permitted segment
- FFmpeg: rendering
- Piper: narration
- repository JSON: state/database
- Cloudflare R2 free tier: optional temporary Meta media staging

## One-time local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env`.

Generate the YouTube OAuth refresh token:

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

## GitHub mode

Push the project to a **public** repo and configure Actions secrets.

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

## Platform defaults

```text
YouTube     ON
Instagram   OFF until Meta credentials are tested
Facebook    OFF until Page Reels adapter is live-tested
TikTok      OFF until approved API use case
X           OFF because API isn't $0
```

## Recommended content format

Avoid:

```text
someone else's clip + captions
```

Use:

```text
permitted evidence
+ original thesis
+ original narration
+ explanation/context
+ attribution
```

Example:

```text
"The 3-second editing decision that makes this giveaway feel huge"
```

rather than simply reposting the giveaway.

See `ACCOUNT_SETUP.md` for every account/credential you need.
