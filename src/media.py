from __future__ import annotations

import subprocess
from pathlib import Path

from .ytdlp import build_ytdlp_command


def run(cmd: list[str]) -> None:
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)


def download_segment(video_url: str, start: float, end: float, workdir: Path) -> Path:
    out = workdir / "segment.mp4"
    run(
        build_ytdlp_command(
            [
                "--download-sections",
                f"*{start:.3f}-{end:.3f}",
                "--force-keyframes-at-cuts",
                "-f",
                "bv*[height<=1080]+ba/b[height<=1080]",
                "--merge-output-format",
                "mp4",
                "-o",
                str(out),
            ],
            video_url,
        )
    )
    return out


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def make_srt(text: str, duration: float, path: Path) -> Path:
    words = text.split()
    groups = [words[i:i+7] for i in range(0, len(words), 7)]
    total_words = max(len(words), 1)
    cursor = 0.0
    lines = []
    for i, group in enumerate(groups, 1):
        seg = max(duration * (len(group) / total_words), 0.7)
        end = min(duration, cursor + seg)
        lines += [
            str(i),
            f"{_srt_time(cursor)} --> {_srt_time(end)}",
            " ".join(group),
            ""
        ]
        cursor = end
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def probe_duration(path: Path) -> float:
    cp = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ], text=True, stdout=subprocess.PIPE, check=True)
    return float(cp.stdout.strip())


def render_vertical(segment: Path, narration: Path, narration_text: str,
                    workdir: Path, source_volume: float = 0.10) -> Path:
    duration = probe_duration(narration)
    srt = make_srt(narration_text, duration, workdir / "captions.srt")
    out = workdir / "final.mp4"
    escaped_srt = str(srt).replace("\\", "/").replace(":", r"\:")

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles='{escaped_srt}':"
        "force_style='FontSize=18,Outline=2,Alignment=2,MarginV=120'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(segment),
        "-i", str(narration),
        "-filter_complex",
        f"[0:a]volume={source_volume}[bg];[bg][1:a]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-map", "0:v:0", "-map", "[a]",
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(out)
    ]
    try:
        run(cmd)
    except subprocess.CalledProcessError:
        run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(segment),
            "-i", str(narration),
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf,
            "-t", f"{duration:.3f}",
            "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart",
            str(out)
        ])
    return out
