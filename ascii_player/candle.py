"""A seeded, smoothly flickering procedural candle, rendered as BGR frames."""
import numpy as np
from numpy.typing import NDArray


class Candle:
    width, height = 240, 300

    def __init__(self, seed: int | None = None) -> None:
        rng = np.random.default_rng(seed)
        self.phases = rng.uniform(0, 2*np.pi, 4)
        self.y, self.x = np.mgrid[0:self.height, 0:self.width].astype(float)

    def frame(self, seconds: float) -> NDArray:
        """Combine an amber halo, tapered flame, wax body, wick and base."""
        x, y = self.x, self.y
        waves = np.sin(seconds * np.array([3.1, 5.3, 8.7, 13.1]) + self.phases)
        sway = waves @ np.array([5, 3, 2, 1])
        flame_height = 78 + waves @ np.array([5, 3, 2, 1])
        z = (160-y) / flame_height
        center = 120 + sway * np.clip(z, 0, 1)**1.5
        radius = 21 * np.sin(np.pi * np.clip(z, 0, 1))**0.7
        distance = np.abs(x-center) / np.maximum(radius, 0.1)
        halo = np.exp(-((x-120)**2/3300 + (y-125)**2/4700))
        rgb = halo[..., None] * np.array([32, 13, 3])
        flame = (z > 0) & (z < 1) & (distance < 1)
        hot = np.clip(1-distance, 0, 1)
        flame_rgb = np.stack([np.full_like(x, 255), 90+160*hot, 12+160*hot**3], -1)
        rgb[flame] = flame_rgb[flame]
        body = (x >= 95) & (x <= 145) & (y >= 169) & (y <= 260)
        shade = 0.62 + 0.38*np.cos((x-112)/42)
        rgb[body] = (shade[..., None]*np.array([215, 178, 119]))[body]
        rim = ((x-120)/25)**2 + ((y-169)/5)**2 < 1
        rgb[rim] = [250, 217, 150]
        wick = (np.abs(x-120) < 2) & (y > 155) & (y < 171)
        rgb[wick] = [110, 56, 24]
        plate = ((x-120)/52)**2 + ((y-266)/6)**2 < 1
        rgb[plate] = [91, 76, 66]
        return np.clip(rgb[..., ::-1], 0, 255).astype(np.uint8)
