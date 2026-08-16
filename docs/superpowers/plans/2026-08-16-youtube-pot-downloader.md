# YouTube PO-Token Downloader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every ClipFactory yt-dlp call use a shared PO-token-aware downloader configuration and provision bgutil + WPC providers on GitHub Actions without weakening the rights gate.

**Architecture:** Add a focused `src/ytdlp.py` module that owns common yt-dlp arguments. Transcript and media code consume that interface instead of building independent YouTube commands. GitHub Actions installs the two provider plugins, starts a local BgUtils provider server, verifies provider availability, then runs the existing controlled factory flow.

**Tech Stack:** Python 3.12, yt-dlp, bgutil-ytdlp-pot-provider, yt-dlp-getpot-wpc, Node.js 24 on GitHub Actions, Chrome/Chromium, pytest.

## Global Constraints

- Preserve the existing `rights.py` source-eligibility gate unchanged.
- Never add browser cookies, account cookies, private-video access, or DRM circumvention.
- Keep ordinary pushes validation-only; real factory execution remains schedule/manual/`[factory-test]` controlled.
- Do not change trend ranking, Gemini prompt behavior, FFmpeg layout, or YouTube upload semantics.
- Provider failure must fail that source cleanly and allow the next rights-cleared candidate.

---

### Task 1: Shared yt-dlp command policy

**Files:**
- Create: `src/ytdlp.py`
- Create: `tests/test_ytdlp.py`

**Interfaces:**
- Produces: `base_ytdlp_args() -> list[str]`
- Produces: `build_ytdlp_command(extra_args: list[str], video_url: str) -> list[str]`

- [ ] **Step 1: Write failing tests**

```python
from src.ytdlp import base_ytdlp_args, build_ytdlp_command


def test_base_args_are_public_and_provider_ready():
    args = base_ytdlp_args()
    assert "--no-playlist" in args
    assert "--no-warnings" not in args
    assert "--cookies" not in args
    assert "--cookies-from-browser" not in args


def test_build_command_wraps_extra_args_and_url():
    command = build_ytdlp_command(["--skip-download", "--dump-single-json"], "https://youtu.be/abc")
    assert command[0] == "yt-dlp"
    assert "--skip-download" in command
    assert command[-1] == "https://youtu.be/abc"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_ytdlp.py -q`
Expected: FAIL because `src.ytdlp` does not exist.

- [ ] **Step 3: Implement the minimal shared command builder**

```python
from __future__ import annotations


def base_ytdlp_args() -> list[str]:
    return [
        "--no-playlist",
        "--extractor-args",
        "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416;youtubepot-wpc:browser_path=/usr/bin/google-chrome",
    ]


def build_ytdlp_command(extra_args: list[str], video_url: str) -> list[str]:
    return ["yt-dlp", *base_ytdlp_args(), *extra_args, video_url]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_ytdlp.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ytdlp.py tests/test_ytdlp.py
git commit -m "feat: centralize yt-dlp provider configuration"
```

---

### Task 2: Route transcript and media downloads through the shared policy

**Files:**
- Modify: `src/transcript.py`
- Modify: `src/media.py`
- Modify: `tests/test_ytdlp.py`

**Interfaces:**
- Consumes: `build_ytdlp_command(extra_args, video_url)`

- [ ] **Step 1: Extend tests to verify all major operation shapes**

```python
from src.ytdlp import build_ytdlp_command


def test_metadata_command_keeps_provider_args():
    command = build_ytdlp_command(["--skip-download", "--dump-single-json"], "u")
    assert "--extractor-args" in command
    assert "--dump-single-json" in command


def test_segment_command_keeps_provider_args():
    command = build_ytdlp_command(["--download-sections", "*1.000-5.000"], "u")
    assert "--extractor-args" in command
    assert "--download-sections" in command
```

- [ ] **Step 2: Replace inline command construction in transcript code**

Import `build_ytdlp_command` and use it in `_load_video_info`, `_download_caption`, and `_download_audio`.

- [ ] **Step 3: Replace inline command construction in media code**

Import `build_ytdlp_command` and use it in `download_segment`.

- [ ] **Step 4: Run focused and full tests**

Run: `pytest tests/test_ytdlp.py tests/test_rights.py -q`
Expected: all PASS.

Run: `pytest -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/transcript.py src/media.py tests/test_ytdlp.py
git commit -m "refactor: use shared yt-dlp policy everywhere"
```

---

### Task 3: Provision PO-token providers in GitHub Actions

**Files:**
- Modify: `requirements.txt`
- Modify: `.github/workflows/factory.yml`

**Interfaces:**
- Runtime service: BgUtils provider on `http://127.0.0.1:4416`
- Browser fallback: `/usr/bin/google-chrome`

- [ ] **Step 1: Add Python provider plugins**

Append:

```text
bgutil-ytdlp-pot-provider>=1.3,<2
yt-dlp-getpot-wpc>=0.4,<2
```

- [ ] **Step 2: Add provider setup after Python dependency installation**

```yaml
      - name: Start YouTube PO-token provider
        run: |
          git clone --depth 1 --branch 1.3.1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /tmp/bgutil-pot
          cd /tmp/bgutil-pot/server
          npm ci
          npx tsc
          nohup node build/main.js > /tmp/bgutil-provider.log 2>&1 &
          echo $! > /tmp/bgutil-provider.pid
          for i in {1..20}; do
            if curl -fsS http://127.0.0.1:4416 >/dev/null 2>&1; then
              break
            fi
            sleep 1
          done
          test -s /tmp/bgutil-provider.pid
          command -v google-chrome
```

- [ ] **Step 3: Add a non-publishing provider verification step**

```yaml
      - name: Verify yt-dlp PO-token plugins
        run: |
          yt-dlp --verbose --skip-download --simulate "https://www.youtube.com/watch?v=jNQXAC9IVRw" 2>&1 | tee /tmp/ytdlp-provider-check.log || true
          grep -E "PO Token Providers:.*(bgutil|wpc)" /tmp/ytdlp-provider-check.log
```

This step verifies plugin discovery; it does not publish content.

- [ ] **Step 4: Keep live factory gating unchanged**

Confirm `Run factory`, `Persist state`, and artifact upload retain the existing event/`[factory-test]` conditions.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .github/workflows/factory.yml
git commit -m "ci: provision YouTube PO-token providers"
```

---

### Task 4: Validate without publishing, then controlled end-to-end test

**Files:**
- No production code changes unless validation exposes a root-cause issue.

**Interfaces:**
- GitHub Actions validation run on `main`
- Controlled live run via `[factory-test]`

- [ ] **Step 1: Verify normal push workflow**

Expected: dependency install PASS, provider setup PASS, provider verification PASS, unit tests PASS, factory SKIPPED.

- [ ] **Step 2: Inspect provider verification logs**

Expected: log contains at least one `bgutil` provider and the `wpc` provider registration.

- [ ] **Step 3: Trigger one controlled factory test**

Create a no-op commit whose message contains `[factory-test]` only after validation is green.

- [ ] **Step 4: Inspect the factory log**

Success criteria:
- At least one rights-cleared source gets past yt-dlp metadata retrieval.
- Caption or audio acquisition succeeds.
- Segment download succeeds.
- The pipeline reaches Gemini/TTS/render/upload, or any later failure is diagnosed separately from YouTube bot attestation.

- [ ] **Step 5: Run final verification**

Run/fetch evidence for:
- full pytest suite green;
- provider setup green;
- provider discovery confirmed;
- no state commit if no upload occurred;
- if an upload occurs, state is persisted exactly once.
