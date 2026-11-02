"""nuqta-mcp [--model nuqta-0.8b|nuqta-4b|PATH_OR_HUB_ID] [--backend auto|transformers|vllm]

MCP server (stdio) that lets Claude Desktop, Claude Code, Cursor and other MCP clients read Arabic documents with
Nuqta. The model loads on the first call and stays loaded. NUQTA_MODEL and NUQTA_BACKEND set the same options from
the environment; the flags win.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
from pathlib import Path

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp 1.x: same API under its old name
    from mcp.server.fastmcp import FastMCP as MCPServer
    from mcp.server.fastmcp.exceptions import ToolError

from .cli import DEFAULT_MODEL
from .text import MODES

ALL_MODES = MODES + ("id",)

server = MCPServer(
    "nuqta-ocr",
    instructions="Arabic OCR for images and PDFs on this computer. Call read_document with an absolute file path.",
)
_config = {"model": os.environ.get("NUQTA_MODEL", DEFAULT_MODEL), "backend": os.environ.get("NUQTA_BACKEND", "auto")}
_ocr = None
_lock = threading.Lock()  # one model, one reading at a time


def _get_ocr():
    global _ocr
    if _ocr is None:
        from .ocr import OCR

        _ocr = OCR(_config["model"], backend=_config["backend"])
    return _ocr


def _page_numbers(spec: str, n: int) -> list[int]:
    """'1-3,5' -> [0, 1, 2, 4] (1-based, inclusive ranges, checked against n pages)."""
    out = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        a, _, b = part.partition("-")
        try:
            lo, hi = int(a), int(b or a)
        except ValueError:
            raise ToolError(f"pages must look like '1-3,5', got {spec!r}") from None
        if not 1 <= lo <= hi <= n:
            raise ToolError(f"pages {part!r} out of range: the PDF has {n} page(s)")
        out += range(lo - 1, hi)
    return sorted(set(out))


def _pdf_pages(path: Path, spec: str | None, dpi: int = 200):
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(path))
    idx = _page_numbers(spec, len(doc)) if spec else range(len(doc))
    return [(i + 1, doc[i].render(scale=dpi / 72).to_pil().convert("RGB")) for i in idx]


@server.tool()
def read_document(path: str, mode: str = "as-written", pages: str | None = None) -> str:
    """Read the text of an Arabic document (image or PDF) on this computer with Nuqta OCR.

    Nuqta is an OCR model for Arabic: books, scans, official documents, tables, ID cards and passports. Mixed
    Arabic/English pages are fine. Tashkeel (diacritics) is copied only where it is printed on the page; it is never
    added.

    Args:
        path: absolute path to a local image (jpg, png, webp, tiff, ...) or PDF.
        mode: "as-written" (default): the text exactly as printed.
              "bare": the text with all tashkeel removed.
              "markdown": headings, paragraphs, lists and tables (as HTML) in reading order.
              "id": the markdown reading plus a JSON block of structured fields for passports, visas and ID cards
              (MRZ with ICAO check digits; Egyptian national ID fields). A failed check means a human should look.
        pages: PDF only, 1-based pages to read, e.g. "1-3,5". Default: every page. A page takes a few seconds.
    """
    if mode not in ALL_MODES:
        raise ToolError(f"mode must be one of {', '.join(ALL_MODES)}; got {mode!r}")
    p = Path(path).expanduser()
    if not p.is_absolute():
        raise ToolError(f"path must be absolute (the server's working directory is {os.getcwd()}); got {path!r}")
    if not p.exists():
        raise ToolError(f"file not found: {p}")
    if not p.is_file():
        raise ToolError(f"not a file: {p}")
    is_pdf = p.suffix.lower() == ".pdf"

    from .ocr import read_fields

    with _lock:
        try:
            src = _pdf_pages(p, pages) if is_pdf else [(None, str(p))]
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"cannot open {p.name} as a PDF: {e}") from e
        try:
            got = _get_ocr().read_many([s for _, s in src], mode=mode)
        except (OSError, ValueError) as e:  # PIL: unreadable or unsupported image
            raise ToolError(f"cannot read {p.name}: {e}") from e
    read = [r.pages[0] for r in got]  # one image per input, so one page each

    parts = []
    for (num, _), page in zip(src, read):
        head = f"--- page {num} ---\n" if is_pdf and len(src) > 1 else ""
        note = "\n[note: the reading of this page repeated itself; the repetition was cut]" if page.looped else ""
        parts.append(head + page.text + note)
    out = "\n\n".join(parts)
    if mode == "id":
        fields = read_fields("\n\n".join(pg.text for pg in read))
        out += "\n\n```json\n" + json.dumps(fields, ensure_ascii=False, indent=1, default=str) + "\n```"
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="nuqta-mcp", description="Nuqta OCR as an MCP server (stdio)")
    ap.add_argument("--model", default=_config["model"], help=f"nuqta-0.8b, nuqta-4b, a hub id or a local path "
                                                                f"(default {DEFAULT_MODEL}, or $NUQTA_MODEL)")
    ap.add_argument("--backend", default=_config["backend"], choices=["auto", "transformers", "vllm"])
    a = ap.parse_args(argv)
    _config.update(model=a.model, backend=a.backend)
    server.run()


if __name__ == "__main__":
    main()
