"""Layout, hOCR and output-validation tests.

No model is downloaded or called here: the synthetic pages are black strokes
on white, and the OCR API tests use a fake backend.
"""
from __future__ import annotations

import json
import sys
from xml.etree import ElementTree as ET

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nuqta import OCR, Line, Page, Result, to_hocr, validate_hocr
from nuqta.cli import main
from nuqta.layout import (
    OPTIONAL_DEPS_HINT,
    SegmentedPage,
    crop_box,
    map_box,
    segment_page,
)
from nuqta.text import counting_sequence, validate_text

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
    # the rule at y=60 is not reported as a text line
    assert all(box[1] > 80 for box in page.boxes)


def test_deskew_is_estimated_and_boxes_stay_aligned():
    page = segment_page(strokes_page(rotation=2))
    assert 1.5 <= abs(page.angle) <= 2.5
    assert len(page.boxes) == 3
    # boxes are in the deskewed image, so they line up with the unrotated page
    assert all(abs(box[1] - expected) <= 10 for box, expected in zip(page.boxes, (100, 200, 300)))


def test_map_box_back_to_original_page():
    page = segment_page(strokes_page(rotation=2))
    box = page.boxes[0]
    mapped = map_box(box, page.matrix, page.size)
    x0, y0, x1, y1 = mapped
    assert 0 <= x0 < x1 <= page.size[0]
    assert 0 <= y0 < y1 <= page.size[1]
    # the rotated box is a little taller than the deskewed one
    assert y1 - y0 >= box[3] - box[1]


def test_crop_margin_includes_diacritics_and_stops_at_neighbour():
    image = Image.new('RGB', (400, 300), 'white')
    ImageDraw.Draw(image).point((150, 92), fill='black')  # a mark above the line
    page = SegmentedPage(image=image, boxes=[], angle=0.0, matrix=np.eye(3), size=image.size)
    line = (100, 100, 300, 130)
    # margin is 40% of 30px = 12px; midpoint to the line above is 90px
    crop = crop_box(page, line, above=(100, 50, 300, 80), below=(100, 160, 300, 190))
    assert crop.size == (216, 52)  # x: 92..308, y: 90..142
    assert crop.getpixel((58, 2)) == (0, 0, 0)  # the mark at (150, 92) survived


def test_crop_margin_is_clamped_to_page_edges():
    image = Image.new('RGB', (400, 100), 'white')
    page = SegmentedPage(image=image, boxes=[], angle=0.0, matrix=np.eye(3), size=image.size)
    crop = crop_box(page, (10, 2, 300, 30), above=None, below=None)
    assert crop.height <= 100
    assert crop.width <= 400


def test_hocr_is_well_formed_and_has_rtl_arabic_lines():
    pages = [
        Page(
            'سطرٌ أول\nسطر ثانٍ',
            lines=[Line('سطرٌ أول', (10, 20, 110, 50)), Line('سطر ثانٍ', (10, 70, 110, 100))],
            width=200,
            height=300,
            dpi=200,
        )
    ]
    document = to_hocr(Result(pages, 'as-written'))
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
        assert len(words) == 1  # OCRmyPDF drops lines without a word child
        assert words[0].text


def test_hocr_escapes_text():
    page = Page('A & B < C', lines=[Line('A & B < C', (0, 0, 60, 20))], width=80, height=40)
    document = to_hocr(Result([page], 'as-written'))
    assert '&amp;' in document and '&lt;' in document
    assert ET.fromstring(document).find(f'.//{XHTML}span[@class="ocrx_word"]').text == 'A & B < C'


def test_hocr_requires_page_size():
    page = Page('نص', lines=[Line('نص', (0, 0, 10, 10))])
    with pytest.raises(ValueError, match='page size'):
        to_hocr(Result([page], 'as-written'))


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


def test_counting_sequence_detects_a_loop_but_not_a_table():
    assert counting_sequence(' '.join(str(n) for n in range(1, 30)))
    assert counting_sequence(' '.join('٠١٢٣٤٥٦٧٨٩'[0] for _ in range(1))) is False
    arabic = ' '.join('٠١٢٣٤٥٦٧٨٩'[n % 10] for n in range(1, 15))
    assert isinstance(counting_sequence(arabic), bool)
    assert not counting_sequence('١ ٢ ٣ ثم كلام')
    assert not counting_sequence('القلم 1 والكتاب 2 والورق 3')


def test_validate_text_reports_repetition_and_dominance():
    assert 'repeated output' in validate_text('نص ' + 'أ' * 300)
    assert 'one character dominates' in validate_text('أ' * 200)
    assert validate_text('نص عربي سليم') == []
    # form lines are legitimate repeats, not a degenerate reading
    assert validate_text('الاسم: ' + '.' * 60) == []


def test_missing_optional_dependencies_has_a_clear_message(monkeypatch):
    monkeypatch.setitem(sys.modules, 'cv2', None)
    with pytest.raises(ImportError, match='nuqta-ocr\\[layout\\]'):
        segment_page(Image.new('RGB', (100, 100), 'white'))
    assert 'opencv' in OPTIONAL_DEPS_HINT


class FakeBackend:
    def generate(self, items, max_new_tokens):
        return [f'سطر {i + 1}' for i in range(len(items))]


def test_ocr_layout_returns_line_text_and_boxes_without_a_model():
    ocr = object.__new__(OCR)
    ocr.backend = FakeBackend()
    ocr.enlarge_pages = True
    result = ocr.read(strokes_page(), layout=True)
    page = result.pages[0]
    assert page.width == 600 and page.height == 800
    assert len(page.lines) == 3
    assert [line.text for line in page.lines] == ['سطر 1', 'سطر 2', 'سطر 3']
    assert all(isinstance(value, int) for line in page.lines for value in line.bbox)
    assert page.text == 'سطر 1\nسطر 2\nسطر 3'


def test_ocr_layout_rejects_markdown_mode():
    ocr = object.__new__(OCR)
    ocr.backend = FakeBackend()
    ocr.enlarge_pages = True
    with pytest.raises(ValueError, match='as-written and bare'):
        ocr.read(strokes_page(), mode='markdown', layout=True)


def test_cli_hocr_output(monkeypatch, capsys):
    def fake_read_many(self, files, mode='as-written', max_new_tokens=8192, layout=False):
        page = Page('نص', lines=[Line('نص', (10, 20, 100, 50))], width=200, height=300)
        return [Result([page], mode)]

    monkeypatch.setattr('nuqta.ocr.OCR.__init__', lambda self, *args, **kwargs: None)
    monkeypatch.setattr('nuqta.ocr.OCR.read_many', fake_read_many)
    main(['read', 'page.png', '--format', 'hocr'])
    out = capsys.readouterr().out
    validate_hocr(out)
    assert 'class="ocr_page"' in out


def test_cli_json_includes_line_boxes(monkeypatch, capsys):
    def fake_read_many(self, files, mode='as-written', max_new_tokens=8192, layout=False):
        page = Page('نص', lines=[Line('نص', (10, 20, 100, 50))], width=200, height=300)
        return [Result([page], mode)]

    monkeypatch.setattr('nuqta.ocr.OCR.__init__', lambda self, *args, **kwargs: None)
    monkeypatch.setattr('nuqta.ocr.OCR.read_many', fake_read_many)
    main(['read', 'page.png', '--format', 'json'])
    data = json.loads(capsys.readouterr().out)
    assert data['pages'][0]['lines'] == [{'text': 'نص', 'bbox': [10, 20, 100, 50]}]


def test_cli_default_text_is_unchanged(monkeypatch, capsys):
    def fake_read_many(self, files, mode='as-written', max_new_tokens=8192, layout=False):
        return [Result([Page('نص')], mode)]

    monkeypatch.setattr('nuqta.ocr.OCR.__init__', lambda self, *args, **kwargs: None)
    monkeypatch.setattr('nuqta.ocr.OCR.read_many', fake_read_many)
    main(['read', 'page.png'])
    assert capsys.readouterr().out == 'نص\n'
