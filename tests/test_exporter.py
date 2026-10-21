import cv2
import numpy as np
import pytest

from ascii_player.cli import parse_args
from ascii_player.exporter import export
from ascii_player.player import Video


@pytest.fixture
def clip(tmp_path):
    path = tmp_path/"source.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64,48))
    assert writer.isOpened()
    for index in range(10):
        writer.write(np.full((48,64,3), index*25, dtype=np.uint8))
    writer.release()
    return path


def test_export_resample_trim_and_protect(clip, tmp_path, monkeypatch):
    monkeypatch.setattr("ascii_player.exporter.shutil.which", lambda _: None)
    output = tmp_path/"result.mp4"
    args = parse_args([str(clip), "--export", "--output", str(output), "--width", "12",
                       "--start", "0.2", "--end", "0.8", "--fps", "20"])
    with pytest.warns(UserWarning, match="silent"):
        _, count, audio = export(args)
    assert count == 12 and not audio
    cap = cv2.VideoCapture(str(output))
    assert cap.get(cv2.CAP_PROP_FPS) == 20
    assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == 12
    assert cap.read()[0]
    cap.release()
    before = output.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        export(args)
    assert output.read_bytes() == before
    args.force = True
    with pytest.warns(UserWarning, match="silent"):
        assert export(args)[1] == 12


def test_source_cannot_be_overwritten(clip):
    args = parse_args([str(clip), "--export", "--output", str(clip), "--force"])
    with pytest.raises(ValueError, match="source"):
        export(args)


def test_video_forward_backward_and_invalid_range(clip):
    source = Video(clip)
    try:
        assert source.frame_at(.8).mean() > source.frame_at(.1).mean()
    finally:
        source.close()
    with pytest.raises(ValueError, match="beyond"):
        Video(clip, 5)


def test_corrupt_file(tmp_path):
    path = tmp_path/"broken.mp4"
    path.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="Cannot open"):
        Video(path)
