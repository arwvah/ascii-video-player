import pytest
from ascii_player.player import scheduled_index, frame_delay


def test_skip_late_frames():
    assert scheduled_index(0.5,30) == 15
    assert scheduled_index(3600,30) == 108000
    assert frame_delay(10,30,0.5) == 0


def test_absolute_deadline():
    assert frame_delay(30,30,0.9) == pytest.approx(0.1)
    assert scheduled_index(-1,30) == 0
    assert scheduled_index(1/30,30) == 1
