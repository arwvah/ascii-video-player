"""Build static README previews from the actual ASCII conversion pipeline.

Run from the project root after installing the project: python scripts/make_readme_assets.py
These are rendered output previews with decorative framing, not desktop captures.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ascii_player.candle import Candle
from ascii_player.converter import convert, dimensions
from ascii_player.exporter import Rasterizer, load_font

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "images"
BG = "#0b1018"
MUTED = "#94a3b8"
WHITE = "#e8edf5"
TEAL = "#66e3cf"


def font(size: int):
    return ImageFont.truetype(str(load_font().path), size)


def label(image, xy, text, size=18, color=WHITE):
    ImageDraw.Draw(image).text(xy, text, font=font(size), fill=color)


def ascii_image(frame, width=60, color="truecolor"):
    raster = Rasterizer("standard")
    h, w = frame.shape[:2]
    size = dimensions(w, h, width, bounds=(width, 160),
                      cell_ratio=raster.cell_width/raster.cell_height)
    pixels = raster.render(convert(frame, size), color)
    return Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))


def terminal(image, xy, content, title):
    x, y = xy
    w, h = content.size
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((x-1, y-1, x+w+1, y+h+45), radius=12, fill="#1c2736")
    draw.rounded_rectangle((x, y, x+w, y+h+44), radius=12, fill="#111925")
    for offset, color in enumerate(["#ff6b6b", "#f4c66b", "#66d9a0"]):
        draw.ellipse((x+16+offset*20, y+16, x+25+offset*20, y+25), fill=color)
    label(image, (x+88,y+12), title, 13, MUTED)
    image.paste(content, (x, y+44))


def source_frame():
    """A reproducible synthetic video-style scene, no downloaded assets."""
    y, x = np.mgrid[:360, :640]
    rgb = np.zeros((360,640,3), dtype=np.float64)
    rgb[:] = [7,14,28]
    for cx, cy, radius, color in [(230,170,120,[50,220,210]), (415,200,95,[244,110,72])]:
        distance = np.sqrt((x-cx)**2 + (y-cy)**2)
        glow = np.exp(-(distance/radius)**4)
        rgb += glow[...,None]*np.array(color)
    rgb = np.clip(rgb,0,255).astype(np.uint8)
    cv2.putText(rgb,"ASCII",(155,215),cv2.FONT_HERSHEY_DUPLEX,2.5,(245,248,255),5,cv2.LINE_AA)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    hero = Image.new("RGB", (1400,650), BG)
    label(hero,(64,70),"VIDEO IN. CHARACTERS OUT.",18,TEAL)
    label(hero,(60,130),"ASCII",78)
    label(hero,(60,220),"VIDEO PLAYER",60)
    label(hero,(64,325),"A little cinema for your terminal.",23,MUTED)
    label(hero,(64,395),"24-bit color  /  Smooth playback",18,TEAL)
    label(hero,(64,430),"Flickering candle  /  MP4 export",18,TEAL)
    ImageDraw.Draw(hero).rounded_rectangle((64,502,728,564),radius=10,fill="#142031")
    label(hero,(84,521),"$ python ascii_video.py --candle",21)
    candle = ascii_image(Candle(seed=42).frame(.4), 44)
    terminal(hero,(850,28),candle,"built-in candle")
    hero.save(ASSETS/"hero.png",optimize=True)

    frame = source_frame()
    comparison = Image.new("RGB",(1400,560),BG)
    label(comparison,(40,26),"SAME FRAME. A DIFFERENT LANGUAGE.",22,TEAL)
    original = Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
    result = ascii_image(frame,64)
    terminal(comparison,(40,90),original,"source pixels / synthetic scene")
    terminal(comparison,(720,90),result,"ASCII / truecolor / 64 columns")
    label(comparison,(40,510),"Actual converter output. Terminal-style frames added for presentation.",16,MUTED)
    comparison.save(ASSETS/"comparison.png",optimize=True)

    gallery = Image.new("RGB",(1400,420),BG)
    label(gallery,(40,25),"PICK YOUR PALETTE",22,TEAL)
    for index, mode in enumerate(["none","ansi","truecolor"]):
        result = ascii_image(frame,42,mode)
        x = 40+index*450
        terminal(gallery,(x,85),result,"--color "+mode)
        label(gallery,(x,378),["Just the characters.","256-color terminal palette.","Full 24-bit RGB."][index],16,MUTED)
    gallery.save(ASSETS/"color-modes.png",optimize=True)
    for path in sorted(ASSETS.glob("*.png")):
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
