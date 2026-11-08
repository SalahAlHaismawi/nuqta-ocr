"""Nuqta OCR: accurate Arabic document OCR with faithful tashkeel."""
from .hocr import to_hocr, validate_hocr
from .layout import Line, segment_lines, segment_page
from .ocr import OCR, Page, Result, read_fields
from .preprocess import is_page, prepare
from .text import MODES, PROMPTS, looped, trim_loops, validate_text

__all__ = ["OCR", "Page", "Result", "read_fields", "is_page", "prepare", "MODES", "PROMPTS", "looped",
           "trim_loops", "validate_text", "Line", "segment_page", "segment_lines", "to_hocr", "validate_hocr"]
__version__ = "0.2.0"
