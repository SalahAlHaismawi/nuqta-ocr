"""Nuqta OCR: the main entry point."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from . import egyid, mrz
from .backends import MAX_NEW_TOKENS, make_backend
from .layout import Line
from .preprocess import load_image, plain, prepare
from .text import MODES, PROMPTS, clean, looped, trim_loops, validate_text


@dataclass
class Page:
    text: str
    looped: bool = False          # even the fallback reading repeated itself (text was trimmed)
    fallback: bool = False        # the page was re-read at native size because the first reading looped
    lines: list[Line] = field(default_factory=list)  # line text + bbox, layout=True only
    width: int = 0                # page size in pixels, needed by hOCR
    height: int = 0
    dpi: int = 200
    warnings: list[str] = field(default_factory=list)  # output validation, empty when clean


@dataclass
class Result:
    pages: list[Page]
    mode: str
    fields: dict = field(default_factory=dict)  # mode="id" only

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    def __str__(self) -> str:
        return self.text


def _pdf_pages(path: Path, dpi: int = 200) -> list[Image.Image]:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(path))
    pages = []
    for i in range(len(doc)):
        im = doc[i].render(scale=dpi / 72).to_pil().convert("RGB")
        im.info["dpi"] = (dpi, dpi)
        pages.append(im)
    return pages


def _image_dpi(im: Image.Image) -> int:
    dpi = im.info.get("dpi")
    try:
        return round(float(dpi[0])) if dpi else 200
    except (TypeError, ValueError, IndexError):
        return 200


def _one_line(text: str) -> str:
    """A line crop must come back as one line: collapse the model's wrapping."""
    return " ".join(clean(text).split())


MODELS = {"nuqta-0.8b": "SalahALHaismawi/Nuqta-Arabic-OCR-0.8B", "nuqta-4b": "SalahALHaismawi/Nuqta-Arabic-OCR-4B"}


class OCR:
    """Read Arabic documents.

        ocr = OCR("nuqta-0.8b")                   # or "nuqta-4b", a hub id or a local path
        ocr.read("page.jpg").text                 # as written: tashkeel only where printed
        ocr.read("scan.pdf", mode="markdown")     # headings, lists, HTML tables, every page
        ocr.read("passport.jpg", mode="id").fields

    Modes: as-written (default), bare (no tashkeel), markdown, id.
    backend: "auto" (vLLM when installed, else transformers), "transformers" or "vllm".
    """

    def __init__(self, model: str, backend: str = "auto", enlarge_pages: bool = True, **backend_kw):
        self.backend = make_backend(MODELS.get(model.lower(), model), backend, **backend_kw)
        self.enlarge_pages = enlarge_pages

    # -- reading
    def _read_images(self, images: list[Image.Image], prompt: str, max_new_tokens: int) -> list[Page]:
        first = [prepare(im, self.enlarge_pages) for im in images]
        outs = [clean(t) for t in self.backend.generate([(im, prompt) for im in first], max_new_tokens)]
        pages = [Page(t) for t in outs]
        # loop fallback: re-read a looping page at its native size (if that is a different input)
        redo = [i for i, t in enumerate(outs) if looped(t) and first[i].size != plain(images[i]).size]
        if redo:
            again = [clean(t) for t in self.backend.generate([(plain(images[i]), prompt) for i in redo], max_new_tokens)]
            for i, t in zip(redo, again):
                if not looped(t):
                    pages[i] = Page(t, fallback=True)
        for p in pages:
            if looped(p.text):
                p.text, p.looped = trim_loops(p.text), True
            p.warnings.extend(validate_text(p.text))
        return pages

    # -- line layout
    def _read_layout(self, images: list[Image.Image], prompt: str, max_new_tokens: int) -> list[Page]:
        """Segment each page into lines, transcribe the crops, map boxes back."""
        from .layout import crop_box, map_box, segment_page

        pages: list[Page] = []
        for im in images:
            segmented = segment_page(im)
            boxes = segmented.boxes
            crops = [
                crop_box(
                    segmented,
                    box,
                    above=boxes[i - 1] if i else None,
                    below=boxes[i + 1] if i + 1 < len(boxes) else None,
                )
                for i, box in enumerate(boxes)
            ]
            raw = self.backend.generate([(crop, prompt) for crop in crops], max_new_tokens) if crops else []
            lines: list[Line] = []
            warnings: list[str] = []
            for number, (box, text) in enumerate(zip(boxes, raw), 1):
                text = _one_line(text)
                issues = validate_text(text)
                if issues:
                    warnings.append(f"line {number}: {', '.join(issues)}")
                if text:
                    lines.append(Line(text, map_box(box, segmented.matrix, segmented.size)))
            pages.append(
                Page(
                    "\n".join(line.text for line in lines),
                    lines=lines,
                    width=im.width,
                    height=im.height,
                    dpi=_image_dpi(im),
                    warnings=warnings,
                )
            )
        return pages

    def read(self, src, mode: str = "as-written", max_new_tokens: int = MAX_NEW_TOKENS,
             layout: bool = False) -> Result:
        """Read one image (path, bytes or PIL image) or a PDF (every page).

        With ``layout=True`` the page is segmented into lines and each line is
        read separately; ``Result.pages[*].lines`` then holds text plus bbox in
        the original image, and ``Page.width/height/dpi`` make the result
        exportable as hOCR.  Layout is for the text modes (as-written, bare):
        markdown and id readings need the whole page.
        """
        return self.read_many([src], mode, max_new_tokens, layout)[0]

    def read_many(self, srcs: list, mode: str = "as-written", max_new_tokens: int = MAX_NEW_TOKENS,
                  layout: bool = False) -> list[Result]:
        """Read several files; with the vLLM backend they are batched."""
        if mode not in MODES + ("id",):
            raise ValueError(f"mode must be one of {MODES + ('id',)}")
        if layout and mode not in ("as-written", "bare"):
            raise ValueError("layout=True is only available for the as-written and bare modes")
        prompt = PROMPTS["markdown" if mode == "id" else mode]
        images, owner = [], []
        for k, src in enumerate(srcs):
            if isinstance(src, (str, Path)) and str(src).lower().endswith(".pdf"):
                ims = _pdf_pages(Path(src))
            else:
                ims = [load_image(src)]
            images += ims
            owner += [k] * len(ims)
        pages = (self._read_layout if layout else self._read_images)(images, prompt, max_new_tokens)
        results = [Result([], mode) for _ in srcs]
        for k, p in zip(owner, pages):
            results[k].pages.append(p)
        if mode == "id":
            for r in results:
                r.fields = read_fields(r.text)
        return results


def read_fields(text: str) -> dict:
    """Structured fields from an ID / passport reading, with validity checks.

    mrz:      the machine-readable zone (passports, visas, TD1 cards): fields + ICAO check digits ("valid") and
              whether the number and dates also appear in the printed zone.
    egyptian: Egyptian national ID fields; the 14-digit national number is decoded and cross-checked against the
              printed birth date and sex ("nid": verified / agreed / check). "check" = a digit is probably misread.
    A failed check means: send this field to a human. Nothing is corrected silently."""
    out: dict = {}
    m = mrz.parse_mrz(text)
    if m:
        out["mrz"] = {k: v for k, v in m.items() if k != "lines"}
    e = egyid.parse(text)
    if e:
        conf: dict = {}
        egyid.check(e, conf)
        out["egyptian"] = {"fields": e, "checks": conf}
    return out
