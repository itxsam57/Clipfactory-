from __future__ import annotations

import tempfile
from pathlib import Path

from src.config import load_config
from src.media import download_direct_segment, probe_remote_duration
from src.open_media import discover_open_media
from src.rights import is_download_allowed


def main() -> None:
    cfg = load_config()
    candidates = discover_open_media(cfg)
    if not candidates:
        raise RuntimeError("Wikimedia Commons returned no automation-safe video candidates.")

    failures: list[str] = []
    for candidate in candidates[:10]:
        allowed, reason = is_download_allowed(candidate, cfg)
        if not allowed:
            failures.append(f"{candidate['video_id']}: rights={reason}")
            continue

        try:
            duration = probe_remote_duration(candidate["url"])
            if duration < 3.0:
                failures.append(
                    f"{candidate['video_id']}: source too short ({duration:.2f}s)"
                )
                continue

            end = min(duration, 5.0)
            with tempfile.TemporaryDirectory(prefix="clipfactory-smoke-") as td:
                output = download_direct_segment(
                    candidate["url"], 0.0, end, Path(td)
                )
                if not output.exists() or output.stat().st_size < 1024:
                    raise RuntimeError("FFmpeg did not produce a usable segment file.")

            print(
                "OPEN MEDIA SMOKE PASS: "
                f"{candidate['video_id']} | {candidate['license']} | "
                f"duration={duration:.2f}s | {candidate['source_page_url']}"
            )
            return
        except Exception as exc:
            failures.append(f"{candidate['video_id']}: {exc}")

    detail = "\n".join(failures[-10:])
    raise RuntimeError(
        "No Commons candidate survived live probe + FFmpeg segment extraction.\n"
        + detail
    )


if __name__ == "__main__":
    main()
