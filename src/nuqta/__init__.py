"""Nuqta OCR: accurate Arabic document OCR with faithful tashkeel."""
from .ocr import OCR, Page, Result, read_fields
from .preprocess import is_page, prepare
from .text import MODES, PROMPTS, looped, trim_loops

__all__ = ["OCR", "Page", "Result", "read_fields", "is_page", "prepare", "MODES", "PROMPTS", "looped", "trim_loops"]
__version__ = "0.1.1"
