"""Video validation, source sampling and drift-free terminal playback."""
import math
from pathlib import Path
import time
import warnings

import cv2

from .candle import Candle
from .converter import convert, dimensions
from .terminal import Terminal, terminal_size


def scheduled_index(elapsed: float, fps: float) -> int:
    """Latest frame due on an absolute monotonic timeline."""
    return max(0, math.floor(elapsed * fps + 1e-9))


def frame_delay(index: int, fps: float, elapsed: float) -> float:
    return max(0.0, index / fps - elapsed)


class Video:
    """A validated OpenCV source with sequential decode and frame skipping."""
    def __init__(self, path: Path, start: float = 0, end: float | None = None) -> None:
        if not path.is_file():
            raise ValueError(f"Video file does not exist: {path}")
        self.cap = cv2.VideoCapture(str(path))
        try:
            if not self.cap.isOpened():
                raise ValueError(f"Cannot open video (unsupported codec or corrupted file): {path}")
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            if not math.isfinite(self.fps) or self.fps <= 0:
                self.fps = 30.0
                warnings.warn("Source FPS is unavailable; assuming 30 FPS")
            self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if self.count <= 0:
                raise ValueError("Video has no readable frame count; try remuxing it to MP4")
            self.start = start
            self.end = min(end if end is not None else self.count/self.fps, self.count/self.fps)
            self.duration = self.end - start
            if self.duration <= 0:
                raise ValueError("Starting timestamp is beyond the video duration")
            self.next_index, self.last_index, self.last_frame = 0, -1, None
            first = self.frame_at(0)
            self.height, self.width = first.shape[:2]
        except BaseException:
            self.cap.release()
            raise

    def frame_at(self, seconds: float):
        target = min(self.count-1, int((self.start+seconds)*self.fps + 1e-8))
        if target == self.last_index:
            return self.last_frame
        if target < self.next_index or target - self.next_index > 120:
            if not self.cap.set(cv2.CAP_PROP_POS_FRAMES, target):
                raise ValueError(f"Video codec cannot seek to frame {target}")
            self.next_index = target
        while self.next_index < target:
            if not self.cap.grab():
                raise ValueError(f"Corrupted or truncated video near frame {self.next_index}")
            self.next_index += 1
        ok, frame = self.cap.read()
        if not ok:
            raise ValueError(f"Cannot decode video frame {target}; file may be corrupted")
        self.next_index = target + 1
        self.last_index, self.last_frame = target, frame
        return frame

    def close(self) -> None:
        self.cap.release()


def play(args) -> None:
    source = Video(args.video, args.start, args.end) if args.video else Candle()
    fps = args.fps or (source.fps if isinstance(source, Video) else 30)
    duration = source.duration if isinstance(source, Video) else (args.end-args.start if args.end else math.inf)
    try:
        with Terminal() as terminal:
            while True:
                origin, index = time.monotonic(), 0
                while index / fps < duration:
                    time.sleep(frame_delay(index, fps, time.monotonic()-origin))
                    index = max(index, scheduled_index(time.monotonic()-origin, fps))
                    if index/fps >= duration:
                        break
                    frame = source.frame_at(index/fps) if isinstance(source, Video) else source.frame(args.start+index/fps)
                    size = dimensions(source.width, source.height, args.width, args.height, terminal_size())
                    terminal.draw(convert(frame, size, args.charset, args.invert).terminal_text(args.color))
                    index += 1
                if math.isfinite(duration):
                    time.sleep(max(0.0, duration - (time.monotonic()-origin)))
                if not args.loop:
                    break
    finally:
        if isinstance(source, Video):
            source.close()
