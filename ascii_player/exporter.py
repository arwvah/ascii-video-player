"""Rasterize a glyph atlas into MP4, optionally muxing original audio."""
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import warnings

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .candle import Candle
from .converter import CHARSETS, ansi_indices, convert, dimensions, palette_rgb
from .player import Video


def load_font() -> ImageFont.FreeTypeFont:
    """Find a monospaced system font on Linux, macOS or Windows."""
    candidates = [
        "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/liberation/LiberationMono-Regular.ttf",
        "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf",
        str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/consola.ttf"),
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, 16)
        except OSError:
            pass
    raise ValueError("No monospaced font found. Install DejaVu Sans Mono (see README)")


class Rasterizer:
    """Render an entire character grid using a precomputed antialiased atlas."""
    def __init__(self, charset: str) -> None:
        self.ramp = CHARSETS[charset]
        font = load_font()
        self.cell_width = math.ceil(font.getlength("M"))
        ascent, descent = font.getmetrics()
        self.cell_height = ascent + descent
        masks = []
        for char in self.ramp:
            tile = Image.new("L", (self.cell_width, self.cell_height))
            ImageDraw.Draw(tile).text((0, 0), char, font=font, fill=255)
            masks.append(np.asarray(tile))
        self.atlas = np.stack(masks)
        self.lookup = np.zeros(128, dtype=np.int32)
        for index, char in enumerate(self.ramp):
            self.lookup[ord(char)] = index

    def render(self, frame, color: str) -> np.ndarray:
        codes = np.frombuffer("".join(frame.chars.ravel()).encode("ascii"), dtype=np.uint8).reshape(frame.chars.shape)
        masks = self.atlas[self.lookup[codes]]
        rgb = frame.rgb if color == "truecolor" else palette_rgb(ansi_indices(frame.rgb))
        if color == "none":
            rgb = np.full_like(frame.rgb, 235)
        pixels = (masks[..., None].astype(np.uint16) * rgb[:, :, None, None, :]) // 255
        rows, cols = frame.chars.shape
        image = pixels.transpose(0, 2, 1, 3, 4).reshape(rows*self.cell_height, cols*self.cell_width, 3).astype(np.uint8)
        # MP4 encoders require even pixel dimensions. Padding does not stretch text.
        image = np.pad(image, ((0, image.shape[0] % 2), (0, image.shape[1] % 2), (0, 0)))
        return np.ascontiguousarray(image[..., ::-1])


def export(args) -> tuple[Path, int, bool]:
    """Export transactionally: failures never leave a partial destination."""
    output = args.output.expanduser().absolute()
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output must have an .mp4 extension")
    if args.video and args.video.resolve() == output.resolve():
        raise ValueError("Output must not replace the source video")
    if output.exists() and not args.force:
        raise ValueError(f"Output already exists: {output}. Use --force to replace it")
    if not output.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {output.parent}")
    source = Video(args.video, args.start, args.end) if args.video else Candle(seed=42)
    writer = None
    try:
        fps = args.fps or (source.fps if isinstance(source, Video) else 30)
        duration = source.duration if isinstance(source, Video) else ((args.end or args.start+10)-args.start)
        count = math.ceil(duration*fps - 1e-9)
        raster = Rasterizer(args.charset)
        size = dimensions(source.width, source.height, args.width, args.height,
                          (args.width or 120, args.height or 240),
                          raster.cell_width/raster.cell_height)
        # A practical memory limit for the vectorized atlas rasterizer.
        if size[0]*size[1] > 100_000:
            raise ValueError("Export grid exceeds 100,000 characters; reduce width or height")
        with tempfile.TemporaryDirectory(prefix=".ascii-export-", dir=output.parent) as temp:
            silent = Path(temp)/"silent.mp4"
            for index in range(count):
                frame = source.frame_at(index/fps) if isinstance(source, Video) else source.frame(args.start+index/fps)
                pixels = raster.render(convert(frame, size, args.charset, args.invert), args.color)
                if writer is None:
                    writer = cv2.VideoWriter(str(silent), cv2.VideoWriter_fourcc(*"mp4v"), fps,
                                             (pixels.shape[1], pixels.shape[0]))
                    if not writer.isOpened():
                        raise ValueError("OpenCV cannot encode MP4 on this system; install an FFmpeg-enabled OpenCV wheel")
                writer.write(pixels)
            writer.release()
            writer = None
            check = cv2.VideoCapture(str(silent))
            try:
                ok, _ = check.read()
                if not ok or int(check.get(cv2.CAP_PROP_FRAME_COUNT)) != count:
                    raise ValueError("MP4 encoder produced an incomplete file")
            finally:
                check.release()
            result, audio = silent, False
            ffmpeg = shutil.which("ffmpeg")
            if args.video:
                if not ffmpeg:
                    warnings.warn("FFmpeg is unavailable: exported video will be silent")
                else:
                    muxed = Path(temp)/"audio.mp4"
                    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent),
                               "-ss", str(args.start), "-i", str(args.video.resolve()),
                               "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy", "-c:a", "aac",
                               "-t", str(count/fps), "-movflags", "+faststart", str(muxed)]
                    completed = subprocess.run(command, capture_output=True, text=True)
                    if completed.returncode == 0:
                        result = muxed
                        # Optional mapping also succeeds for silent source videos.
                        probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(muxed)], capture_output=True, text=True)
                        audio = "Audio:" in probe.stderr
                    else:
                        warnings.warn("Audio attachment failed; exporting silent video: " + completed.stderr[-600:])
            if args.force:
                os.replace(result, output)
            else:
                # Exclusive creation protects against another process creating the target.
                created = False
                try:
                    with output.open("xb") as destination:
                        created = True
                        with result.open("rb") as stream:
                            shutil.copyfileobj(stream, destination)
                except BaseException:
                    if created:
                        output.unlink(missing_ok=True)
                    raise
        return output, count, audio
    finally:
        if writer is not None:
            writer.release()
        if isinstance(source, Video):
            source.close()
