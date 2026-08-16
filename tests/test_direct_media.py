import subprocess

from src import media


def test_probe_remote_duration_uses_ffprobe_and_user_agent(monkeypatch):
    captured = []

    def fake_run(command, **kwargs):
        captured.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="42.5\n", stderr="")

    monkeypatch.setattr(media.subprocess, "run", fake_run)

    duration = media.probe_remote_duration("https://upload.wikimedia.org/example.webm")

    assert duration == 42.5
    assert captured[0][0] == "ffprobe"
    assert "-user_agent" in captured[0]
    assert media.MEDIA_USER_AGENT in captured[0]
    assert "yt-dlp" not in captured[0]


def test_probe_remote_duration_retries_transient_failure(monkeypatch):
    calls = []
    responses = [
        subprocess.CompletedProcess(["ffprobe"], 1, stdout="", stderr="HTTP error 429"),
        subprocess.CompletedProcess(["ffprobe"], 0, stdout="30.25\n", stderr=""),
    ]

    def fake_run(command, **kwargs):
        calls.append(command)
        return responses.pop(0)

    monkeypatch.setattr(media.subprocess, "run", fake_run)
    monkeypatch.setattr(media.time, "sleep", lambda _: None)

    duration = media.probe_remote_duration("https://upload.wikimedia.org/example.webm")

    assert duration == 30.25
    assert len(calls) == 2


def test_probe_remote_duration_raises_descriptive_error_after_retries(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="HTTP error 503")

    monkeypatch.setattr(media.subprocess, "run", fake_run)
    monkeypatch.setattr(media.time, "sleep", lambda _: None)

    try:
        media.probe_remote_duration("https://upload.wikimedia.org/example.webm")
    except RuntimeError as exc:
        assert "503" in str(exc)
        assert "3 attempts" in str(exc)
    else:
        raise AssertionError("persistent ffprobe failure should raise RuntimeError")

    assert len(calls) == 3


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
    assert "-user_agent" in command
    assert media.MEDIA_USER_AGENT in command
    assert "https://upload.wikimedia.org/example.webm" in command
    assert "10.000" in command
    assert "libx264" in command
