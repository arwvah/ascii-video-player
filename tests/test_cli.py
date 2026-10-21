from pathlib import Path
import pytest
from ascii_player.cli import parse_args, main


def test_defaults():
    args = parse_args([])
    assert args.video is None
    assert args.color == "truecolor"


def test_video_options():
    args = parse_args(["video.mp4", "--width", "100", "--fps", "24", "--charset", "detailed"])
    assert args.video == Path("video.mp4")
    assert args.width == 100
    assert args.fps == 24


@pytest.mark.parametrize("arguments", [
    ["--width","0"], ["--height","-2"], ["--fps","0"], ["--fps","nan"],
    ["--start","inf"], ["--start","5","--end","2"], ["x.mp4","--candle"],
    ["--export","--loop"], ["--color","blue"],
])
def test_invalid(arguments):
    with pytest.raises(SystemExit) as error:
        parse_args(arguments)
    assert error.value.code == 2


def test_missing_file(capsys):
    assert main(["/definitely/missing/video.mp4"]) == 1
    assert "does not exist" in capsys.readouterr().err
