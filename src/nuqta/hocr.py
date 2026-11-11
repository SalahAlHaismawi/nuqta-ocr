"""hOCR export for line-level Nuqta readings.

hOCR is the interchange format used by OCRmyPDF and other PDF text-layer
tools: an HTML document in which every element carries a ``title`` attribute
with a pixel bounding box.  Nuqta finds line boxes with :mod:`nuqta.layout`,
so this module writes one ``ocr_line`` per box.

Each line also contains one ``ocrx_word`` spanning the whole line.  That is
not cosmetic: OCRmyPDF's hOCR parser drops a line that has no word children,
so a line-only file would produce an empty text layer.  Word-level boxes are
left for a later version; the text and the box are still at line granularity.
"""
from __future__ import annotations

from html import escape
from typing import Protocol
from xml.etree import ElementTree as ET


class _PageLike(Protocol):
    width: int
    height: int
    dpi: int
    lines: list


class _ResultLike(Protocol):
    pages: list[_PageLike]


def _bbox(box: tuple[int, int, int, int]) -> str:
    x0, y0, x1, y1 = box
    return f'bbox {x0} {y0} {x1} {y1}'


def to_hocr(
    result: _ResultLike,
    *,
    title: str = 'Nuqta OCR',
    lang: str = 'ar',
    dpi: int | None = None,
) -> str:
    """Render a line reading as one hOCR document.

    Any object with ``pages`` whose pages expose ``width``, ``height``,
    ``dpi`` and ``lines`` works; :class:`nuqta.LineResult` and the line layout
    API produce exactly that. Pages without a size raise ``ValueError``.
    """
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE html>',
        f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{escape(lang)}" lang="{escape(lang)}" dir="rtl">',
        '<head>',
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />',
        '<meta name="ocr-system" content="nuqta" />',
        '<meta name="ocr-capabilities" content="ocr_page ocr_line ocrx_word" />',
        f'<title>{escape(title)}</title>',
        '</head>',
        '<body>',
    ]
    for page_number, page in enumerate(result.pages):
        width, height = int(page.width), int(page.height)
        if width <= 0 or height <= 0:
            raise ValueError(
                'hOCR needs the page size; use nuqta.read_lines, whose pages '
                'record their width and height'
            )
        page_dpi = int(dpi) if dpi is not None else int(page.dpi or 0)
        scan_res = f'; scan_res {page_dpi} {page_dpi}' if page_dpi > 0 else ''
        lines.append(
            f'<div class="ocr_page" id="page_{page_number + 1}" '
            f'title="bbox 0 0 {width} {height}; ppageno {page_number}{scan_res}" '
            f'lang="{escape(lang)}" dir="rtl">'
        )
        visible = [line for line in page.lines if line.text.strip()]
        for line_number, line in enumerate(visible, 1):
            x0, y0, x1, y1 = line.bbox
            line_id = f'line_{page_number + 1}_{line_number}'
            word_id = f'word_{page_number + 1}_{line_number}_1'
            text = escape(line.text.strip())
            lines.append(f'<p class="ocr_par" lang="{escape(lang)}" dir="rtl">')
            lines.append(
                f'<span class="ocr_line" id="{line_id}" '
                f'title="{_bbox(line.bbox)}" lang="{escape(lang)}" dir="rtl">'
            )
            lines.append(
                f'<span class="ocrx_word" id="{word_id}" '
                f'title="{_bbox((x0, y0, x1, y1))}">{text}</span>'
            )
            lines.append('</span>')
            lines.append('</p>')
        lines.append('</div>')
    lines += ['</body>', '</html>', '']
    return '\n'.join(lines)


_BBOX = '{http://www.w3.org/1999/xhtml}'


def validate_hocr(document: str) -> None:
    """Raise ``ValueError`` if *document* is not usable line-level hOCR.

    This is intentionally strict about the things OCRmyPDF relies on and
    lenient about optional properties (confidence, baseline, fonts).
    """
    try:
        root = ET.fromstring(document)
    except ET.ParseError as exc:
        raise ValueError(f'hOCR is not well-formed XML: {exc}') from exc

    pages = root.findall(f'.//{_BBOX}div[@class="ocr_page"]')
    if not pages:
        raise ValueError('hOCR has no ocr_page element')
    def check_bbox(element, kind: str) -> None:
        title = element.get('title', '')
        if 'bbox' not in title:
            raise ValueError(f'{kind} is missing a bbox')
        numbers = title.split('bbox', 1)[1].split(';', 1)[0].split()
        if len(numbers) != 4 or not all(part.isdigit() for part in numbers):
            raise ValueError(f'non-integer bbox in {kind}: {title!r}')

    for page in pages:
        check_bbox(page, 'ocr_page')
        for line in page.findall(f'.//{_BBOX}span[@class="ocr_line"]'):
            check_bbox(line, 'ocr_line')
            words = line.findall(f'.//{_BBOX}span[@class="ocrx_word"]')
            if not words:
                raise ValueError(
                    'ocr_line has no ocrx_word child; OCRmyPDF will discard it'
                )
            for word in words:
                check_bbox(word, 'ocrx_word')
    if 'ocr_page' not in document:
        raise ValueError('hOCR is missing the ocr_page/ocr_line classes')
