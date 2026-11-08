"""Layout, hOCR and CLI tests.

No model is downloaded or called: synthetic black strokes stand in for text and
a fake OCR object implements only the public ``read_many`` call.
"""
from __future__ import annotations

import inspect
import json
import sys
from xml.etree import ElementTree as ET

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nuqta import OCR, Page, Result, to_hocr, validate_hocr
from nuqta.cli import main
from nuqta.layout import (
    OPTIONAL_DEPS_HINT,
    Line,
    LinePage,
    LineResult,
    SegmentedPage,
    crop_box,
    map_box,
    read_lines,
    segment_page,
)

XHTML = '{http://www.w3.org/1999/xhtml}'


def strokes_page(rotation: float = 0) -> Image.Image:
    """Three text-like lines (vertical strokes, not solid bars) plus a rule."""
    image = Image.new('RGB', (600, 800), 'white')
    draw = ImageDraw.Draw(image)
    for y in (100, 200, 300):
        for x in range(80, 520, 20):
            draw.rectangle((x, y, x + 8, y + 30), fill='black')
    draw.rectangle((60, 60, 540, 63), fill='black')  # a printed rule: must be ignored
    if rotation:
        image = image.rotate(rotation, resample=Image.BICUBIC, fillcolor='white')
    return image


def test_segment_lines_finds_lines_top_to_bottom_and_skips_rules():
    page = segment_page(strokes_page())
    assert len(page.boxes) == 3
    assert [box[1] for box in page.boxes] == sorted(box[1] for box in page.boxes)
    assert all(80 <= box[0] and box[2] <= 520 for box in page.boxes)
    assert all(box[1] > 80 for box in page.boxes)


def test_blank_page_has_no_lines():
    page = segment_page(Image.new('RGB', (600, 800), 'white'))
    assert page.boxes == []


def test_deskew_is_estimated_and_boxes_stay_aligned():
    page = segment_page(strokes_page(rotation=2))
    assert 1.5 <= abs(page.angle) <= 2.5
    assert len(page.boxes) == 3
    assert all(abs(box[1] - expected) <= 10 for box, expected in zip(page.boxes, (100, 200, 300)))


def test_map_box_back_to_original_page():
    page = segment_page(strokes_page(rotation=2))
    box = page.boxes[0]
    mapped = map_box(box, page.matrix, page.size)
    x0, y0, x1, y1 = mapped
    assert 0 <= x0 < x1 <= page.size[0]
    assert 0 <= y0 < y1 <= page.size[1]
    assert y1 - y0 >= box[3] - box[1]


def test_crop_margin_includes_diacritics_and_stops_at_neighbour():
    image = Image.new('RGB', (400, 300), 'white')
    ImageDraw.Draw(image).point((150, 92), fill='black')
    page = SegmentedPage(image=image, boxes=[], angle=0.0, matrix=np.eye(3), size=image.size)
    line = (100, 100, 300, 130)
    crop = crop_box(page, line, above=(100, 50, 300, 80), below=(100, 160, 300, 190))
    assert crop.size == (216, 52)
    assert crop.getpixel((58, 2)) == (0, 0, 0)


def test_crop_margin_is_clamped_to_page_edges():
    image = Image.new('RGB', (400, 100), 'white')
    page = SegmentedPage(image=image, boxes=[], angle=0.0, matrix=np.eye(3), size=image.size)
    crop = crop_box(page, (10, 2, 300, 30), above=None, below=None)
    assert crop.height <= 100
    assert crop.width <= 400


def test_hocr_is_well_formed_and_has_rtl_arabic_lines():
    pages = [
        LinePage(
            'سطرٌ أول\nسطر ثانٍ',
            lines=[Line('سطرٌ أول', (10, 20, 110, 50)), Line('سطر ثانٍ', (10, 70, 110, 100))],
            width=200,
            height=300,
            dpi=200,
        )
    ]
    document = to_hocr(LineResult(pages, 'as-written'))
    validate_hocr(document)
    root = ET.fromstring(document)
    page_div = root.find(f'.//{XHTML}div[@class="ocr_page"]')
    assert page_div is not None
    assert 'scan_res 200 200' in page_div.get('title')
    lines = root.findall(f'.//{XHTML}span[@class="ocr_line"]')
    assert len(lines) == 2
    assert all(line.get('lang') == 'ar' and line.get('dir') == 'rtl' for line in lines)
    for line in lines:
        numbers = line.get('title').split('bbox', 1)[1].split()
        assert len(numbers) == 4 and all(number.isdigit() for number in numbers)
        words = line.findall(f'.//{XHTML}span[@class="ocrx_word"]')
        assert len(words) == 1
        assert words[0].text


def test_hocr_escapes_text():
    page = LinePage('A & B < C', lines=[Line('A & B < C', (0, 0, 60, 20))], width=80, height=40)
    document = to_hocr(LineResult([page], 'as-written'))
    assert '&amp;' in document and '&lt;' in document
    assert ET.fromstring(document).find(f'.//{XHTML}span[@class="ocrx_word"]').text == 'A & B < C'


def test_hocr_requires_page_size():
    page = LinePage('نص', lines=[Line('نص', (0, 0, 10, 10))], width=0, height=0)
    with pytest.raises(ValueError, match='page size'):
        to_hocr(LineResult([page], 'as-written'))


def test_validate_hocr_rejects_a_line_without_words():
    document = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
    <div class="ocr_page" title="bbox 0 0 10 10"><p class="ocr_par">
    <span class="ocr_line" title="bbox 1 1 9 9">text</span></p></div></body></html>"""
    with pytest.raises(ValueError, match='no ocrx_word'):
        validate_hocr(document)


def test_validate_hocr_rejects_bad_bbox():
    document = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
    <div class="ocr_page" title="bbox 0 0 10 10"><p class="ocr_par">
    <span class="ocr_line" title="bbox 1 1 9 9"><span class="ocrx_word"
    title="bbox a b c d">text</span></span></p></div></body></html>"""
    with pytest.raises(ValueError, match='non-integer'):
        validate_hocr(document)


def test_missing_optional_dependencies_has_a_clear_message(monkeypatch):
    monkeypatch.setitem(sys.modules, 'cv2', None)
    with pytest.raises(ImportError, match='nuqta-ocr\\[layout\\]'):
        segment_page(Image.new('RGB', (100, 100), 'white'))
    assert 'opencv' in OPTIONAL_DEPS_HINT


class FakeOCR:
    """Implements the one public method layout code is allowed to call."""

    def __init__(self):
        self.calls = []

    def read_many(self, srcs, mode='as-written', max_new_tokens=8192):
        self.calls.append((len(srcs), mode, max_new_tokens))
        return [Result([Page(f'سطر {index + 1}')], mode) for index in range(len(srcs))]


def test_read_lines_returns_text_and_boxes_without_a_model():
    ocr = FakeOCR()
    result = read_lines(ocr, [strokes_page()])[0]
    page = result.pages[0]
    assert page.width == 600 and page.height == 800
    assert len(page.lines) == 3
    assert [line.text for line in page.lines] == ['سطر 1', 'سطر 2', 'سطر 3']
    assert all(isinstance(value, int) for line in page.lines for value in line.bbox)
    assert page.text == 'سطر 1\nسطر 2\nسطر 3'
    assert ocr.calls == [(3, 'as-written', 8192)]


def test_read_lines_rejects_markdown_mode():
    with pytest.raises(ValueError, match='as-written and bare'):
        read_lines(FakeOCR(), [strokes_page()], mode='markdown')


def test_core_inference_api_is_unchanged():
    assert 'layout' not in inspect.signature(OCR.read).parameters
    assert list(Page.__dataclass_fields__) == ['text', 'looped', 'fallback']


def test_cli_hocr_output(monkeypatch, capsys):
    def fake_read_lines(ocr, files, *, mode='as-written', max_new_tokens=8192):
        page = LinePage('نص', lines=[Line('نص', (10, 20, 100, 50))], width=200, height=300)
        return [LineResult([page], mode)]

    monkeypatch.setattr('nuqta.ocr.OCR.__init__', lambda self, *args, **kwargs: None)
    monkeypatch.setattr('nuqta.layout.read_lines', fake_read_lines)
    main(['read', 'page.png', '--format', 'hocr'])
    out = capsys.readouterr().out
    validate_hocr(out)
    assert 'class="ocr_page"' in out


def test_cli_default_text_is_unchanged(monkeypatch, capsys):
    def fake_read_many(self, files, mode='as-written', max_new_tokens=8192):
        return [Result([Page('نص')], mode)]

    monkeypatch.setattr('nuqta.ocr.OCR.__init__', lambda self, *args, **kwargs: None)
    monkeypatch.setattr('nuqta.ocr.OCR.read_many', fake_read_many)
    main(['read', 'page.png'])
    assert capsys.readouterr().out == 'نص\n'


def test_cli_json_is_unchanged(monkeypatch, capsys):
    def fake_read_many(self, files, mode='as-written', max_new_tokens=8192):
        return [Result([Page('نص')], mode)]

    monkeypatch.setattr('nuqta.ocr.OCR.__init__', lambda self, *args, **kwargs: None)
    monkeypatch.setattr('nuqta.ocr.OCR.read_many', fake_read_many)
    main(['read', 'page.png', '--format', 'json'])
    data = json.loads(capsys.readouterr().out)
    assert data == {
        'file': 'page.png',
        'mode': 'as-written',
        'text': 'نص',
        'fields': {},
        'pages': [{'text': 'نص', 'looped': False, 'fallback': False}],
    }
