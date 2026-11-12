"""Nuqta OCR: accurate Arabic document OCR with faithful tashkeel."""
from .hocr import to_hocr, validate_hocr
from .layout import Line, LinePage, LineResult, read_lines, segment_lines, segment_page
from .ocr import OCR, Page, Result, read_fields
from .preprocess import is_page, prepare
from .text import MODES, PROMPTS, looped, trim_loops

__all__ = ["OCR", "Page", "Result", "read_fields", "is_page", "prepare", "MODES", "PROMPTS", "looped",
           "trim_loops", "Line", "LinePage", "LineResult", "read_lines", "segment_page", "segment_lines",
           "to_hocr", "validate_hocr"]
__version__ = "0.3.0"
