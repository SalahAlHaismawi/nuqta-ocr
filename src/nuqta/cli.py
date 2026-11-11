"""nuqta read FILE [FILE ...] [--mode as-written|bare|markdown|id] [--format text|json|hocr]"""
from __future__ import annotations

import argparse
import json
import sys

from .text import MODES

DEFAULT_MODEL = "nuqta-0.8b"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="nuqta", description="Nuqta OCR: Arabic document OCR with faithful tashkeel")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read", help="read images / PDFs and print the text")
    r.add_argument("files", nargs="+")
    r.add_argument("--mode", default="as-written", choices=MODES + ("id",))
    r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--backend", default="auto", choices=["auto", "transformers", "vllm"])
    r.add_argument("--no-enlarge", action="store_true", help="read pages at their native size")
    r.add_argument("--format", default="text", choices=["text", "json", "hocr"],
                   help="output format; hocr implies line layout")
    r.add_argument("--json", action="store_true", help="alias for --format json")
    a = ap.parse_args(argv)
    if a.json and a.format != "text":
        ap.error("--json cannot be combined with --format")
    out_format = "json" if a.json else a.format
    if out_format == "hocr" and a.mode not in ("as-written", "bare"):
        ap.error("--format hocr needs --mode as-written or bare")

    from .ocr import OCR

    ocr = OCR(a.model, backend=a.backend, enlarge_pages=not a.no_enlarge)
    if out_format == "hocr":
        from .hocr import to_hocr
        from .layout import LineResult, read_lines

        line_results = read_lines(ocr, a.files, mode=a.mode)
        pages = [page for result in line_results for page in result.pages]
        print(to_hocr(LineResult(pages=pages, mode=a.mode), title=", ".join(a.files)))
        return
    results = ocr.read_many(a.files, mode=a.mode)
    for f, res in zip(a.files, results):
        if out_format == "json":
            print(json.dumps({"file": f, "mode": res.mode, "text": res.text, "fields": res.fields,
                              "pages": [vars(p) for p in res.pages]}, ensure_ascii=False, default=str))
        else:
            if len(a.files) > 1:
                print(f"==> {f} <==")
            print(res.text)
            if res.fields:
                print(json.dumps(res.fields, ensure_ascii=False, indent=1, default=str))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
