"""Vectorized image sampling and terminal color encoding."""
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

CHARSETS = {
    "simple": " .:-=+*#%@",
    "standard": " .,:;irsXA253hMHGS#9B&@",
    "detailed": " .`'^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
}


def dimensions(source_width: int, source_height: int, width: int | None = None,
               height: int | None = None, bounds: tuple[int, int] = (120, 60),
               cell_ratio: float = 0.5) -> tuple[int, int]:
    """Fit a character grid into bounds; both dimensions are a bounding box."""
    if min(source_width, source_height, *bounds) < 1 or cell_ratio <= 0:
        raise ValueError("Image and terminal dimensions must be positive")
    if (width is not None and width < 1) or (height is not None and height < 1):
        raise ValueError("Width and height must be positive")
    max_w, max_h = min(width or bounds[0], bounds[0]), min(height or bounds[1], bounds[1])
    aspect = source_height / source_width * cell_ratio
    w = max(1, min(max_w, round(max_h / aspect)))
    h = max(1, min(max_h, round(w * aspect)))
    return w, h


def brightness_indices(gray: NDArray, length: int, invert: bool = False) -> NDArray:
    """Map 0..255 luminance to a ramp without uint8 overflow."""
    values = 255 - gray if invert else gray
    return np.minimum(values.astype(np.float32) * length / 256, length - 1).astype(np.int32)


def ansi_indices(rgb: NDArray) -> NDArray:
    """Choose the nearest xterm color cube or grayscale entry."""
    values = rgb.astype(np.int32)
    levels = np.array([0, 95, 135, 175, 215, 255])
    cube = np.abs(values[..., None] - levels).argmin(axis=-1)
    cube_rgb = levels[cube]
    gray = np.clip(np.rint((values.mean(axis=-1) - 8) / 10), 0, 23).astype(int)
    gray_rgb = 8 + gray * 10
    use_gray = ((values - gray_rgb[..., None]) ** 2).sum(-1) < ((values - cube_rgb) ** 2).sum(-1)
    return np.where(use_gray, 232 + gray, 16 + 36*cube[..., 0] + 6*cube[..., 1] + cube[..., 2])


def palette_rgb(indices: NDArray) -> NDArray:
    """Decode the cube/grayscale portion of the xterm palette."""
    levels = np.array([0, 95, 135, 175, 215, 255], dtype=np.uint8)
    cube = np.clip(indices - 16, 0, 215)
    rgb = np.stack([levels[cube//36], levels[cube//6 % 6], levels[cube % 6]], axis=-1)
    return np.where((indices >= 232)[..., None], (8 + (indices - 232)*10)[..., None], rgb).astype(np.uint8)


@dataclass
class AsciiFrame:
    """Character and RGB arrays shared by terminal and image renderers."""
    chars: NDArray
    rgb: NDArray

    def terminal_text(self, color: str) -> str:
        """Build one buffered frame, coalescing consecutive color runs."""
        if color == "none":
            return "\r\n".join("".join(row) for row in self.chars)
        colors = ansi_indices(self.rgb) if color == "ansi" else self.rgb
        lines = []
        for row, shades in zip(self.chars, colors):
            parts, previous = [], None
            for char, shade in zip(row, shades):
                key = int(shade) if color == "ansi" else tuple(int(x) for x in shade)
                if key != previous:
                    parts.append(f"\x1b[38;5;{key}m" if color == "ansi" else f"\x1b[38;2;{key[0]};{key[1]};{key[2]}m")
                    previous = key
                parts.append(str(char))
            lines.append("".join(parts) + "\x1b[0m")
        return "\r\n".join(lines)


def convert(frame: NDArray, size: tuple[int, int], charset: str = "standard",
            invert: bool = False) -> AsciiFrame:
    """Resize a BGR frame and map its luminance into printable characters."""
    resized = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    ramp = np.array(list(CHARSETS[charset]))
    return AsciiFrame(ramp[brightness_indices(gray, len(ramp), invert)],
                      cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
