import io

import numpy as np
import pytest

from ascii_player.candle import Candle
from ascii_player.terminal import Terminal, terminal_size


def test_candle_flickers_and_is_reproducible():
    candle = Candle(seed=42)
    first = candle.frame(0)
    assert first.shape == (300,240,3)
    assert first.dtype == np.uint8
    assert np.array_equal(first, Candle(seed=42).frame(0))
    assert not np.array_equal(first, candle.frame(.5))


def test_terminal_restored_on_interrupt(monkeypatch):
    class Tty(io.StringIO):
        def isatty(self):
            return True
    output = Tty()
    monkeypatch.setattr("ascii_player.terminal.sys.stdout", output)
    monkeypatch.setattr("ascii_player.terminal.os.name", "posix")
    with pytest.raises(KeyboardInterrupt):
        with Terminal() as terminal:
            terminal.draw("hello")
            raise KeyboardInterrupt
    assert output.getvalue().endswith("\x1b[0m\x1b[?25h\x1b[?1049l")


def test_terminal_size_extremes(monkeypatch):
    import os
    monkeypatch.setattr("ascii_player.terminal.shutil.get_terminal_size", lambda _: os.terminal_size((0,0)))
    assert terminal_size() == (1,1)
    monkeypatch.setattr("ascii_player.terminal.shutil.get_terminal_size", lambda _: os.terminal_size((10000,10000)))
    assert terminal_size() == (300,150)
