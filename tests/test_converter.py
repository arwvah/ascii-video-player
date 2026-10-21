import numpy as np
import pytest

from ascii_player.converter import brightness_indices, convert, dimensions, ansi_indices, palette_rgb


def test_brightness_endpoints_and_inversion():
    values = np.array([0, 128, 255], dtype=np.uint8)
    assert brightness_indices(values, 10).tolist() == [0, 5, 9]
    assert brightness_indices(values, 10, True).tolist() == [9, 4, 0]


@pytest.mark.parametrize("source,bounds,expected", [
    ((1920,1080),(100,50),(100,28)),
    ((1080,1920),(100,40),(45,40)),
    ((1920,1080),(1,1),(1,1)),
])
def test_dimensions(source, bounds, expected):
    assert dimensions(*source, bounds=bounds) == expected


def test_width_height_and_invalid_sizes():
    assert dimensions(100,100,80,10) == (20,10)
    with pytest.raises(ValueError):
        dimensions(0,10)


def test_convert_and_color():
    image = np.full((8,16,3), (0,0,255), dtype=np.uint8)
    frame = convert(image, (4,2), "simple")
    assert frame.chars.shape == (2,4)
    assert frame.rgb[0,0].tolist() == [255,0,0]
    assert "\x1b" not in frame.terminal_text("none")
    assert "\x1b[38;2;255;0;0m" in frame.terminal_text("truecolor")
    assert "\x1b[38;5;196m" in frame.terminal_text("ansi")


def test_palette_roundtrip():
    colors = np.array([[[255,0,0], [128,128,128], [0,255,0]]], dtype=np.uint8)
    assert palette_rgb(ansi_indices(colors)).tolist() == colors.tolist()
