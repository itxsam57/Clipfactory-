# Account setup checklist

## GitHub

- [ ] Create a **public** repository, e.g. `clipfactory-zero`.
- [ ] Upload this project.
- [ ] Enable GitHub Actions.
- [ ] Add repository secrets from `.env.example`.
- [ ] Keep workflow `contents: write` permission so `data/state.json` can persist.

Public repositories can use standard GitHub-hosted Actions runners without Actions compute charges.

GitHub can automatically disable a scheduled workflow in a public repository after 60 days without repository activity. This project normally writes state changes back to the repository after productive runs, but GitHub scheduling remains an external platform dependency.

## Google Cloud / YouTube

- [ ] Create Google Cloud project.
- [ ] Enable **YouTube Data API v3**.
- [ ] Create API key → `YOUTUBE_API_KEY`.
- [ ] Configure OAuth consent screen.
- [ ] Create Desktop OAuth client.
- [ ] Put client ID and client secret in local `.env`.
- [ ] Run `python scripts/youtube_oauth_bootstrap.py`.
- [ ] Save printed refresh token as `YOUTUBE_REFRESH_TOKEN`.
- [ ] Create/prepare the YouTube channel.
- [ ] Connect AdSense only when/if YPP eligibility is reached.

## Gemini

- [ ] Open Google AI Studio.
- [ ] Create a Gemini API/auth key.
- [ ] Save as `GEMINI_API_KEY`.
- [ ] Default is the stable `gemini-2.5-flash`, which currently has free-tier text input/output; change `GEMINI_MODEL` later if needed.

The pipeline sends transcript text instead of full video to minimize quota use.

## Meta / Instagram

- [ ] Create Facebook Page.
- [ ] Change Instagram to Professional (Creator or Business).
- [ ] Create Meta developer app.
- [ ] Configure the current Instagram publishing permissions.
- [ ] Save token as `META_ACCESS_TOKEN`.
- [ ] Save Instagram user ID as `META_IG_USER_ID`.
- [ ] Save Facebook Page ID as `META_PAGE_ID`.
- [ ] Set `META_GRAPH_VERSION` to the version tested with your app.
- [ ] Only then set `publishing.instagram` to `true`.

The Instagram adapter is included. Facebook Reels is intentionally fail-closed until its Page Reels upload flow is live-tested against your actual Meta app/version.

## Cloudflare R2

Needed for the Meta API to pull the rendered video from a public URL.

- [ ] Create Cloudflare account.
- [ ] Create R2 **Standard** bucket.
- [ ] Create R2 S3 API credentials.
- [ ] Enable public `r2.dev` URL or a public custom domain.
- [ ] Add:
  - `R2_ACCOUNT_ID`
  - `R2_ACCESS_KEY_ID`
  - `R2_SECRET_ACCESS_KEY`
  - `R2_BUCKET`
  - `R2_PUBLIC_BASE_URL`

Rendered media is staged temporarily and then deleted.

## TikTok

- [ ] Create TikTok developer app.
- [ ] Apply for Content Posting API.
- [ ] Read the current Content Posting guidelines.
- [ ] Complete audit if your actual use case qualifies.
- [ ] Keep `publishing.tiktok=false` until approved.

TikTok's official rules restrict unaudited Direct Post clients and reject a use case that is simply copying arbitrary content from other platforms.

## X

Excluded from strict-zero-budget mode because the official API is pay-per-use in 2026.

## Rights configuration

Creative Commons:

```json
"allow_creative_commons": true
```

Creators who explicitly gave you reuse permission:

```json
"allowed_channel_ids": [
  "UCxxxxxxxxxxxxxxxxxxxxxx"
]
```

High performers you only want to study as trend signals:

```json
"trend_only_channel_ids": [
  "UCxxxxxxxxxxxxxxxxxxxxxx"
]
```
