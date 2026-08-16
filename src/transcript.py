from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .ytdlp import build_ytdlp_command

_WHISPER_MODEL = None


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _log_failure(label: str, result: subprocess.CompletedProcess) -> None:
    detail = (result.stderr or result.stdout or "unknown error").strip()
    if len(detail) > 1200:
        detail = detail[-1200:]
    print(f"{label}: {detail}")


def _load_video_info(video_url: str) -> dict | None:
    result = _run(
        build_ytdlp_command(
            [
                "--skip-download",
                "--dump-single-json",
            ],
            video_url,
        )
    )
    if result.returncode != 0:
        _log_failure("yt-dlp metadata lookup failed", result)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"yt-dlp metadata JSON could not be parsed: {exc}")
        return None


def _preferred_caption_language(info: dict) -> str | None:
    manual = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}

    def useful(keys):
        return [
            key
            for key in keys
            if key and key != "live_chat" and not key.startswith("-live_chat")
        ]

    manual_keys = useful(manual.keys())
    automatic_keys = useful(automatic.keys())

    # Prefer English, but Gemini can understand other languages, so any available
    # caption track is better than throwing away a rights-cleared source.
    for pool in (manual_keys, automatic_keys):
        for exact in ("en", "en-US", "en-GB", "en-orig"):
            if exact in pool:
                return exact
        for language in pool:
            if language.lower().startswith("en"):
                return language

    if manual_keys:
        return manual_keys[0]
    if automatic_keys:
        return automatic_keys[0]
    return None


def _clean_vtt(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines: list[str] = []
    previous = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line == "WEBVTT"
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or line.startswith("NOTE")
        ):
            continue

        line = re.sub(r"<[^>]+>", "", line)
        if line == previous and "-->" not in line:
            continue
        lines.append(line)
        previous = line

    transcript = "\n".join(lines).strip()
    return transcript[:60000] if transcript else None


def _download_caption(video_url: str, language: str, workdir: Path) -> str | None:
    template = str(workdir / "caption.%(ext)s")
    result = _run(
        build_ytdlp_command(
            [
                "--skip-download",
                "--write-auto-subs",
                "--write-subs",
                "--sub-langs",
                language,
                "--sub-format",
                "vtt",
                "-o",
                template,
            ],
            video_url,
        )
    )
    if result.returncode != 0:
        _log_failure(f"Caption download failed for language {language}", result)
        return None

    vtts = sorted(workdir.glob("caption*.vtt"))
    if not vtts:
        print(f"Caption track {language} was advertised but no VTT file was produced.")
        return None
    return _clean_vtt(vtts[0])


def _download_audio(video_url: str, workdir: Path) -> Path | None:
    template = str(workdir / "source_audio.%(ext)s")
    result = _run(
        build_ytdlp_command(
            [
                "-f",
                "ba[abr<=96]/ba/b",
                "-x",
                "--audio-format",
                "wav",
                "-o",
                template,
            ],
            video_url,
        )
    )
    if result.returncode != 0:
        _log_failure("Audio fallback download failed", result)
        return None

    matches = sorted(workdir.glob("source_audio*.wav"))
    if not matches:
        print("Audio fallback finished but no WAV file was produced.")
        return None
    return matches[0]


def _format_time(seconds: float) -> str:
    milliseconds = int(max(0, seconds) * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


def _transcribe_audio(audio_path: Path) -> str | None:
    global _WHISPER_MODEL
    from faster_whisper import WhisperModel

    if _WHISPER_MODEL is None:
        print("No downloadable captions found; loading free local Whisper fallback.")
        _WHISPER_MODEL = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
        )

    segments, info = _WHISPER_MODEL.transcribe(
        str(audio_path),
        beam_size=1,
        temperature=0,
        vad_filter=True,
    )

    print(
        "Whisper fallback detected language "
        f"{info.language} (probability {info.language_probability:.2f})."
    )

    lines: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        lines.append(
            f"{_format_time(segment.start)} --> {_format_time(segment.end)}\n{text}"
        )
        if sum(len(line) for line in lines) >= 58000:
            break

    transcript = "\n".join(lines).strip()
    return transcript[:60000] if transcript else None


def fetch_subtitles(video_url: str, workdir: Path) -> str | None:
    """Return timestamped source speech without depending on creator captions.

    Fast path: use a creator/automatic caption track in any available language.
    Fallback: download audio and transcribe locally with faster-whisper on CPU.
    """

    info = _load_video_info(video_url)
    if not info:
        return None

    language = _preferred_caption_language(info)
    if language:
        transcript = _download_caption(video_url, language, workdir)
        if transcript:
            print(f"Using YouTube caption track: {language}")
            return transcript

    duration = float(info.get("duration") or 0)
    if duration <= 0:
        print("Source duration is unknown; not downloading unbounded audio.")
        return None
    if duration > 20 * 60:
        print(
            f"No captions and source is {duration / 60:.1f} minutes; "
            "skipping to keep the free runner lightweight."
        )
        return None

    audio = _download_audio(video_url, workdir)
    if not audio:
        return None
    return _transcribe_audio(audio)
