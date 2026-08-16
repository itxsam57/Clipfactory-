from __future__ import annotations


def base_ytdlp_args() -> list[str]:
    """Arguments shared by every public YouTube yt-dlp operation.

    PO-token plugins are installed by the runner. These extractor arguments
    point the primary BgUtils provider at its local service and tell the WPC
    fallback where Chrome lives on GitHub-hosted Ubuntu runners.
    """

    return [
        "--no-playlist",
        "--extractor-args",
        "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416",
        "--extractor-args",
        "youtubepot-wpc:browser_path=/usr/bin/google-chrome",
    ]


def build_ytdlp_command(extra_args: list[str], video_url: str) -> list[str]:
    """Build a yt-dlp command without cookies or account authentication."""

    return ["yt-dlp", *base_ytdlp_args(), *extra_args, video_url]
