from src.ytdlp import base_ytdlp_args, build_ytdlp_command


def test_base_args_are_public_and_provider_ready():
    args = base_ytdlp_args()

    assert "--no-playlist" in args
    assert args.count("--extractor-args") == 2
    assert "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416" in args
    assert "youtubepot-wpc:browser_path=/usr/bin/google-chrome" in args

    assert "--cookies" not in args
    assert "--cookies-from-browser" not in args
    assert "--username" not in args
    assert "--password" not in args


def test_build_command_wraps_operation_and_url():
    command = build_ytdlp_command(
        ["--skip-download", "--dump-single-json"],
        "https://youtu.be/abc",
    )

    assert command[0] == "yt-dlp"
    assert command.count("--extractor-args") == 2
    assert "--skip-download" in command
    assert "--dump-single-json" in command
    assert command[-1] == "https://youtu.be/abc"


def test_segment_command_keeps_provider_configuration():
    command = build_ytdlp_command(
        ["--download-sections", "*1.000-5.000"],
        "https://youtu.be/abc",
    )

    assert "--extractor-args" in command
    assert "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416" in command
    assert "youtubepot-wpc:browser_path=/usr/bin/google-chrome" in command
    assert "--download-sections" in command
