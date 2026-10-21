"""Generate a reproducible two-second test clip without external assets."""
import argparse
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("sample.mp4"))
    parser.add_argument("--portrait", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    width, height = (180, 320) if args.portrait else (320, 180)
    writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*"mp4v"), 24, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Cannot initialize MP4 encoder")
    y, x = np.mgrid[:height, :width]
    try:
        for index in range(48):
            frame = np.stack([x/width*255, y/height*255, np.full_like(x, 70+index*3)], -1).astype(np.uint8)
            cv2.circle(frame, (int(25+(width-50)*index/47), height//2), 22, (30, 220, 255), -1)
            cv2.putText(frame, "ASCII", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 2)
            writer.write(frame)
    finally:
        writer.release()
    print(args.output)


if __name__ == "__main__":
    main()
