"""Single-column text-line segmentation and deskew (optional OpenCV/NumPy).

Nuqta reads whole pages, but a text layer (hOCR, searchable PDFs) also needs
the position of each line.  This module finds those positions with classical
image processing: Otsu binarization, a projection-profile deskew, and a
horizontal projection profile for the lines themselves.  No second model and
no training data are involved.

The module is deliberately standalone: :mod:`nuqta` does not import it, and
NumPy/OpenCV are optional extras (``pip install "nuqta-ocr[layout]"``).  The
public surface is small and works on PIL images:

    page = segment_page(image)          # deskewed image + line boxes
    for box in page.boxes:
        crop = crop_box(page, box, above=..., below=...)
        ...                             # transcribe crop with Nuqta
    original = map_box(box, page.matrix, page.size)   # back to input pixels

Boxes are ``(x0, y0, x1, y1)`` with integer, half-open coordinates in pixels,
origin at the top left.  Line boxes are returned top to bottom, which is the
reading order of a single-column Arabic page.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Integral

from PIL import Image

Box = tuple[int, int, int, int]

OPTIONAL_DEPS_HINT = (
    'line segmentation needs NumPy and OpenCV; install them with '
    '`pip install "nuqta-ocr[layout]"` or `pip install numpy opencv-python-headless`'
)

# Tuning constants.  They are deliberately conservative: a missed line is
# worse than an extra one, because every extra crop costs a model call.
_MIN_LINE_HEIGHT = 8          # px; below this it is noise or a rule
_MAX_LINE_FRACTION = 0.12     # a "line" taller than this shares of the page is a block
_MIN_INK_PIXELS = 20
_MERGE_GAP_FRACTION = 0.18    # of the median line height
_MARGIN_Y = 0.40              # of line height, added above and below for the crop
_MARGIN_X = 0.25              # of line height, added left and right


def _deps():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(OPTIONAL_DEPS_HINT) from exc
    return cv2, np


@dataclass(frozen=True)
class Line:
    """One recognized line: its text and its box in the *original* image."""

    text: str
    bbox: Box

    def __post_init__(self) -> None:
        if not all(isinstance(v, Integral) for v in self.bbox):
            raise TypeError('bbox coordinates must be integers')
        object.__setattr__(self, 'bbox', tuple(int(v) for v in self.bbox))
        x0, y0, x1, y1 = self.bbox
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f'invalid bbox {self.bbox!r}')


@dataclass
class SegmentedPage:
    """A deskewed page image plus its line boxes.

    ``image`` is the deskewed image the crops must be taken from.  ``boxes``
    are in that image's coordinates; use :func:`map_box` with ``matrix`` to
    get boxes in the original input image.
    """

    image: Image.Image
    boxes: list[Box]
    angle: float
    matrix: object                    # 2x3 affine matrix (NumPy array)
    size: tuple[int, int]             # original (width, height)


def _otsu(gray, cv2, np):
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def _clean_specks(binary, cv2, np, min_area: int = 3):
    """Drop isolated pixels while keeping Arabic dots (typically 10+ px)."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    if count <= 1:
        return binary
    keep = np.zeros(count, dtype=bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
    return np.where(keep[labels], 255, 0).astype(np.uint8)


def _remove_rules(binary, width: int, cv2, np):
    """Erase long horizontal rules before profiling rows.

    A printed rule can bridge the gap between a heading and its underline, or
    inflate a line box.  Opening with a very wide 1-pixel kernel keeps only
    horizontal runs that are almost certainly graphics, never a text line.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, width // 3), 1))
    rules = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    if not rules.any():
        return binary
    rules = cv2.dilate(rules, np.ones((3, 1), np.uint8))
    return cv2.subtract(binary, rules)


def _profile_angle(gray, cv2, np) -> float:
    """Deskew angle in degrees from the variance of the row projection.

    Text rows produce sharp peaks in the horizontal projection; the angle that
    maximizes the variance of that projection is the one that lines up the
    baselines.  A coarse pass (1 degree) is followed by a fine pass (0.1
    degree) around the best coarse angle.
    """
    h, w = gray.shape
    scale = min(1.0, 800.0 / max(h, w))
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    binary = _otsu(small, cv2, np)
    binary = _remove_rules(binary, binary.shape[1], cv2, np)
    # Ignore a 2% border: scanner edges and binding shadows are not text.
    bh, bw = binary.shape
    my, mx = int(bh * 0.02), int(bw * 0.02)
    if bh - 2 * my < 10 or bw - 2 * mx < 10:
        return 0.0
    binary[:my, :] = 0
    binary[-my:, :] = 0
    binary[:, :mx] = 0
    binary[:, -mx:] = 0

    def score(angle: float) -> float:
        matrix = cv2.getRotationMatrix2D((bw / 2.0, bh / 2.0), angle, 1.0)
        rotated = cv2.warpAffine(
            binary, matrix, (bw, bh), flags=cv2.INTER_NEAREST, borderValue=0
        )
        projection = rotated.sum(axis=1, dtype=np.float64)
        return float(projection.var())

    coarse = max(np.arange(-4.0, 4.01, 1.0), key=score)
    fine = max(np.arange(coarse - 1.0, coarse + 1.01, 0.1), key=score)
    # Very large angles mean the projection locked onto a graphic, not text;
    # sub-0.15 degree corrections only add interpolation blur.
    return float(fine) if 0.15 <= abs(fine) <= 5.0 else 0.0


def _rotate(gray, angle: float, cv2):
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
    rotated = cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_LINEAR, borderValue=255
    )
    return rotated, matrix


def _runs(mask, min_len: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start = None
    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if index - start >= min_len:
                out.append((start, index))
            start = None
    if start is not None and len(mask) - start >= min_len:
        out.append((start, len(mask)))
    return out


def _merge_runs(runs: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in runs:
        if merged and start - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def _ink_extent(binary, y0: int, y1: int, np) -> tuple[int, int, int]:
    """Tight horizontal extent and ink count of a row band."""
    band = binary[y0:y1]
    columns = band.sum(axis=0, dtype=np.int64)
    ink = int(band.sum(dtype=np.int64) // 255)
    xs = np.flatnonzero(columns)
    if xs.size == 0:
        return 0, 0, 0
    return int(xs[0]), int(xs[-1]) + 1, ink


def _split_tall_band(binary, y0: int, y1: int, median_height: float, cv2, np):
    """Split a merged block at a clear row-profile valley, if there is one."""
    if y1 - y0 <= 1.9 * median_height:
        return [(y0, y1)]
    profile = binary[y0:y1].sum(axis=1, dtype=np.float64)
    smooth = np.convolve(profile, np.ones(3) / 3.0, mode='same')
    lo, hi = int((y1 - y0) * 0.25), int((y1 - y0) * 0.75)
    if hi - lo < 3:
        return [(y0, y1)]
    cut = lo + int(np.argmin(smooth[lo:hi]))
    if smooth[cut] > 0.55 * float(smooth.mean()):
        return [(y0, y1)]
    return _split_tall_band(binary, y0, y0 + cut, median_height, cv2, np) + _split_tall_band(
        binary, y0 + cut, y1, median_height, cv2, np
    )


def _detect_boxes(binary, width: int, height: int, cv2, np) -> list[Box]:
    profile = binary.sum(axis=1, dtype=np.float64) / 255.0
    smooth = np.convolve(profile, np.ones(5) / 5.0, mode='same')
    if float(smooth.max()) <= 0:
        return []
    threshold = max(1.0, float(smooth.max()) * 0.035)
    runs = _runs(smooth > threshold, _MIN_LINE_HEIGHT)
    if not runs:
        return []
    heights = sorted(end - start for start, end in runs)
    median_height = heights[len(heights) // 2]
    runs = _merge_runs(runs, max(3, int(median_height * _MERGE_GAP_FRACTION)))

    boxes: list[Box] = []
    for start, end in runs:
        for y0, y1 in _split_tall_band(binary, start, end, median_height, cv2, np):
            if y1 - y0 < _MIN_LINE_HEIGHT or (y1 - y0) > height * _MAX_LINE_FRACTION:
                continue
            x0, x1, ink = _ink_extent(binary, y0, y1, np)
            if ink < _MIN_INK_PIXELS or x1 <= x0:
                continue
            box_width, box_height = x1 - x0, y1 - y0
            # A long, dense, thin band is a printed rule, not a text line.
            density = ink / max(box_width * box_height, 1)
            if (
                box_height <= max(12, int(height * 0.009))
                and box_width >= width * 0.3
                and density >= 0.35
            ):
                continue
            # Tight boxes: the projection band is already a little generous,
            # but one pixel of padding protects the tops of diacritics.
            boxes.append((x0, max(0, y0 - 1), x1, min(height, y1 + 1)))
    boxes.sort(key=lambda box: (box[1], box[0]))
    return boxes


def map_box(box: Box, matrix, size: tuple[int, int]) -> Box:
    """Map a box from the deskewed image back to the original image."""
    import numpy as np

    x0, y0, x1, y1 = box
    corners = np.array([[x0, y0, 1], [x1, y0, 1], [x1, y1, 1], [x0, y1, 1]], dtype=np.float64)
    inverse = np.linalg.inv(np.vstack([matrix, [0, 0, 1]]))[:2]
    mapped = corners @ inverse.T
    xs, ys = mapped[:, 0], mapped[:, 1]
    width, height = size
    return (
        max(0, min(width, math.floor(xs.min()))),
        max(0, min(height, math.floor(ys.min()))),
        max(0, min(width, math.ceil(xs.max()))),
        max(0, min(height, math.ceil(ys.max()))),
    )


def segment_page(image: Image.Image, *, deskew: bool = True) -> SegmentedPage:
    """Find text lines in a single-column page.

    Args:
        image: an RGB or grayscale PIL image of the page.
        deskew: estimate and correct a small rotation (up to 5 degrees).

    Returns:
        SegmentedPage: the deskewed image, line boxes top to bottom, the
        (estimated) angle and the affine matrix needed by :func:`map_box`.
    """
    cv2, np = _deps()
    if image.mode != 'L':
        gray = cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2GRAY)
    else:
        gray = np.asarray(image)
    gray = np.ascontiguousarray(gray)
    angle = _profile_angle(gray, cv2, np) if deskew else 0.0
    if angle:
        gray, matrix = _rotate(gray, angle, cv2)
    else:
        matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    binary = _clean_specks(_otsu(gray, cv2, np), cv2, np)
    binary = _remove_rules(binary, gray.shape[1], cv2, np)
    boxes = _detect_boxes(binary, gray.shape[1], gray.shape[0], cv2, np)
    deskewed = Image.fromarray(gray) if image.mode == 'L' else Image.fromarray(
        cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    )
    return SegmentedPage(
        image=deskewed,
        boxes=boxes,
        angle=angle,
        matrix=matrix,
        size=image.size,
    )


def crop_box(
    page: SegmentedPage,
    box: Box,
    *,
    above: Box | None = None,
    below: Box | None = None,
) -> Image.Image:
    """Crop one line with a vertical margin for diacritics.

    ``above`` and ``below`` are the neighbouring line boxes (in the deskewed
    image).  The margin is clamped to the midpoint between lines so a crop
    never swallows the neighbouring line; that is the most context the model
    can get without being shown someone else's text.
    """
    x0, y0, x1, y1 = box
    height = max(y1 - y0, 1)
    margin_y = round(height * _MARGIN_Y)
    margin_x = round(height * _MARGIN_X)
    top = y0 - margin_y
    bottom = y1 + margin_y
    if above is not None:
        top = max(top, (above[3] + y0) // 2)
    if below is not None:
        bottom = min(bottom, (y1 + below[1]) // 2)
    top = max(0, min(top, y0))
    bottom = min(page.image.height, max(bottom, y1))
    left = max(0, x0 - margin_x)
    right = min(page.image.width, x1 + margin_x)
    return page.image.crop((left, top, right, bottom))


def segment_lines(image: Image.Image, *, deskew: bool = True) -> list[Line]:
    """Convenience wrapper: line boxes in the original image, text empty."""
    page = segment_page(image, deskew=deskew)
    return [
        Line('', map_box(box, page.matrix, page.size)) for box in page.boxes
    ]
