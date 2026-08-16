import subprocess

from src import media


def test_probe_remote_duration_uses_ffprobe(monkeypatch):
    captured = []

    def fake_run(command, **kwargs):
        captured.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="42.5\n", stderr="")

    monkeypatch.setattr(media.subprocess, "run", fake_run)

    duration = media.probe_remote_duration("https://upload.wikimedia.org/example.webm")

    assert duration == 42.5
    assert captured[0][0] == "ffprobe"
    assert "yt-dlp" not in captured[0]


def test_download_direct_segment_uses_ffmpeg_not_ytdlp(monkeypatch, tmp_path):
    captured = []

    def fake_run(command):
        captured.append(command)

    monkeypatch.setattr(media, "run", fake_run)

    result = media.download_direct_segment(
        "https://upload.wikimedia.org/example.webm",
        2.0,
        12.0,
        tmp_path,
    )

    assert result == tmp_path / "segment.mp4"
    command = captured[0]
    assert command[0] == "ffmpeg"
    assert "yt-dlp" not in command
    assert "https://upload.wikimedia.org/example.webm" in command
    assert "10.000" in command
    assert "libx264" in command
