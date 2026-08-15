from __future__ import annotations
import re, subprocess
from pathlib import Path

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )

def fetch_subtitles(video_url: str, workdir: Path) -> str | None:
    template = str(workdir / "source.%(ext)s")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs", "en.*,en",
        "--sub-format", "vtt",
        "-o", template,
        video_url,
    ]
    result = _run(cmd)
    if result.returncode != 0:
        return None

    vtts = sorted(workdir.glob("source*.vtt"))
    if not vtts:
        return None

    text = vtts[0].read_text(encoding="utf-8", errors="ignore")
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line == "WEBVTT" or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        lines.append(line)
    return "\n".join(lines)[:60000]
