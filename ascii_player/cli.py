"""Command-line validation and dispatch."""
import argparse
import math
from pathlib import Path
import sys

import cv2

from .converter import CHARSETS


def positive_int(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 1000:
        raise argparse.ArgumentTypeError("must be between 1 and 1000")
    return number


def finite_number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite, nonnegative number")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ascii-video", description="Play videos as colored ASCII art, or enjoy a flickering candle.",
        epilog="Examples: python ascii_video.py clip.mp4 --width 100 | python ascii_video.py --candle | python ascii_video.py clip.mp4 --export --output art.mp4")
    parser.add_argument("video", nargs="?", type=Path, help="local video file (omit for candle)")
    parser.add_argument("--width", type=positive_int, help="maximum character width (automatic by default)")
    parser.add_argument("--height", type=positive_int, help="maximum character height; preserves aspect ratio")
    parser.add_argument("--fps", type=finite_number, help="output FPS (resamples without changing duration)")
    parser.add_argument("--color", choices=["none", "ansi", "truecolor"], default="truecolor", help="color mode (default: truecolor)")
    parser.add_argument("--charset", choices=CHARSETS, default="standard", help="brightness ramp (default: standard)")
    parser.add_argument("--invert", action="store_true", help="reverse brightness-to-character mapping")
    parser.add_argument("--loop", action="store_true", help="replay indefinitely (terminal only)")
    parser.add_argument("--start", type=finite_number, default=0, help="start time in seconds")
    parser.add_argument("--end", type=finite_number, help="exclusive end time in seconds")
    parser.add_argument("--candle", action="store_true", help="show the built-in candle")
    parser.add_argument("--export", action="store_true", help="save MP4 instead of playing; candle defaults to 10 seconds")
    parser.add_argument("--output", type=Path, default=Path("ascii-output.mp4"), help="export destination (default: ascii-output.mp4)")
    parser.add_argument("--force", action="store_true", help="allow replacing an existing export")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.candle and args.video:
        parser.error("choose either a video file or --candle")
    if args.end is not None and args.end <= args.start:
        parser.error("--end must be greater than --start")
    if args.fps is not None and not 0 < args.fps <= 240:
        parser.error("--fps must be greater than zero and at most 240")
    if args.export and args.loop:
        parser.error("--loop cannot be used with a finite MP4 export")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.video and not args.export:
        print("ASCII Video Player · candle mode · Ctrl+C to stop\nTo play a video: python ascii_video.py video.mp4", file=sys.stderr)
    try:
        if args.export:
            from .exporter import export
            path, frames, audio = export(args)
            print(f"Exported {frames} frames to {path} ({'with audio' if audio else 'silent'})")
        else:
            from .player import play
            play(args)
    except KeyboardInterrupt:
        print("\nPlayback stopped.", file=sys.stderr)
        return 130
    except (ValueError, OSError, cv2.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0
