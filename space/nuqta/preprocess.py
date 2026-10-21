"""Image input policy: what the model saw in training, so what it should see at inference.

* Pages (page-shaped images: aspect <= 2 and short side >= 450 px) are enlarged to the training size, 2.4 MP.
  Small page renders (e.g. 612x792 PDF pages with ~10 px text) otherwise lose letters and loop; on our held-out
  page sets this never hurt and cut handwritten-page errors by 41%.
* Crops (words, lines, paragraphs, cards: everything not page-shaped) keep their size. Enlarging crops hurt
  (word crops: +90% CER at 2.4 MP).
* Every image is capped at 2.4 MP, the training cap.
* Transparent PNGs are composited onto white (a plain RGB conversion turns transparent pixels black).
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

TRAIN_PIXELS = 2_400_000
PAGE_MIN_SHORT_SIDE = 450
PAGE_MAX_ASPECT = 2.0


def load_image(src) -> Image.Image:
    """A path, bytes or a PIL image -> an RGB PIL image."""
    if isinstance(src, Image.Image):
        im = src
    elif isinstance(src, (bytes, bytearray)):
        im = Image.open(io.BytesIO(src))
    else:
        im = Image.open(Path(src))
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert("RGB")


def is_page(im: Image.Image) -> bool:
    w, h = im.size
    return max(w, h) / max(min(w, h), 1) <= PAGE_MAX_ASPECT and min(w, h) >= PAGE_MIN_SHORT_SIDE


def _scale_to(im: Image.Image, pixels: int) -> Image.Image:
    k = (pixels / (im.width * im.height)) ** 0.5
    return im.resize((max(32, int(im.width * k)), max(32, int(im.height * k))), Image.LANCZOS)


def prepare(im: Image.Image, enlarge_pages: bool = True) -> Image.Image:
    """The release input policy (see the module docstring)."""
    area = im.width * im.height
    if enlarge_pages and is_page(im) and area < TRAIN_PIXELS:
        return _scale_to(im, TRAIN_PIXELS)
    if area > TRAIN_PIXELS:
        return _scale_to(im, TRAIN_PIXELS)
    return im


def plain(im: Image.Image) -> Image.Image:
    """The fallback reading's input: native size, only capped."""
    return _scale_to(im, TRAIN_PIXELS) if im.width * im.height > TRAIN_PIXELS else im
