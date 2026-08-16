import subprocess

from src import media, transcript


def test_transcript_metadata_uses_shared_provider_policy(monkeypatch):
    captured = []

    def fake_run(command):
        captured.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(transcript, "_run", fake_run)

    assert transcript._load_video_info("https://youtu.be/abc") == {}
    command = captured[0]
    assert command.count("--extractor-args") == 2
    assert "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416" in command
    assert "youtubepot-wpc:browser_path=/usr/bin/google-chrome" in command


def test_segment_download_uses_shared_provider_policy(monkeypatch, tmp_path):
    captured = []

    def fake_run(command):
        captured.append(command)

    monkeypatch.setattr(media, "run", fake_run)

    result = media.download_segment(
        "https://youtu.be/abc",
        1.0,
        5.0,
        tmp_path,
    )

    assert result == tmp_path / "segment.mp4"
    command = captured[0]
    assert command.count("--extractor-args") == 2
    assert "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416" in command
    assert "youtubepot-wpc:browser_path=/usr/bin/google-chrome" in command
