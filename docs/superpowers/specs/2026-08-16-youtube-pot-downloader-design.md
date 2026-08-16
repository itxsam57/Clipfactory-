# YouTube PO-Token Downloader Resilience Design

## Goal

Keep YouTube as ClipFactory's trend/source discovery layer while making downloads of already rights-cleared public YouTube sources resilient to YouTube PO-token/bot-attestation challenges on GitHub Actions.

## Non-goals

- Do not bypass ClipFactory's rights gate.
- Do not access private, members-only, DRM-protected, deleted, or otherwise restricted videos.
- Do not require the user's browser cookies or personal YouTube session.
- Do not change trend ranking, Gemini editorial logic, rendering, or publishing semantics.

## Architecture

Create a single downloader-command module used by every yt-dlp call in transcript and media paths. The module supplies a consistent YouTube extractor configuration and keeps provider-specific settings out of business logic.

GitHub Actions will install two yt-dlp PO-token provider plugins:

1. `bgutil-ytdlp-pot-provider` as the primary lightweight provider. A local BgUtils provider server will run on the runner and yt-dlp will discover the plugin automatically.
2. `yt-dlp-getpot-wpc` as an additional browser-based provider using the Chrome already present on GitHub-hosted Ubuntu runners. It can mint WebPoClient tokens when yt-dlp requests them.

Both providers are available to yt-dlp's PO-token framework. ClipFactory itself does not manufacture or persist tokens.

## Data flow

1. YouTube Data API discovers trends and verifies `creativeCommon` licensing as before.
2. Only a source that passes `rights.py` reaches transcript/media download.
3. Every yt-dlp command receives the shared hardened YouTube arguments.
4. yt-dlp selects an available PO-token provider when YouTube requires attestation.
5. Transcript extraction proceeds from captions first, then audio + faster-whisper fallback.
6. The selected time range is downloaded through the same hardened downloader configuration.
7. Existing Gemini, TTS, FFmpeg and YouTube upload stages continue unchanged.

## GitHub Actions setup

- Keep Python 3.12.
- Install `bgutil-ytdlp-pot-provider` and `yt-dlp-getpot-wpc` through `requirements.txt`.
- Clone a pinned release of `Brainicism/bgutil-ytdlp-pot-provider`, build its Node provider server, and start it on `127.0.0.1:4416` before the factory step.
- Verify provider registration before a live factory run with `yt-dlp -v` output or a plugin listing command that does not publish anything.
- Chrome/Chromium availability is validated before WPC is relied on.

## Error handling

- A provider failure is a source-download failure, not permission to weaken licensing checks.
- Source failures remain isolated: ClipFactory tries the next rights-cleared candidate.
- Logs report whether the provider service is healthy and whether yt-dlp sees external PO-token providers, without printing secrets.
- A factory run with no successful post must not mutate persistent state.

## Testing

- Unit-test shared yt-dlp command construction so transcript and media use the same provider-aware base arguments.
- Unit-test that the downloader does not add cookies or authentication flags.
- Run all existing rights tests.
- Run GitHub validation without posting.
- Run one controlled `[factory-test]` end-to-end job and inspect logs for successful source metadata/download before considering the integration complete.

## Safety and compliance

The downloader increases reliability only for public media that ClipFactory has independently determined is reusable under its configured rights policy. It does not make inaccessible content accessible and does not alter licensing decisions.
