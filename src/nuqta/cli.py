"""nuqta read FILE [FILE ...] [--mode as-written|bare|markdown|id] [--model PATH_OR_HUB_ID] [--json]"""
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
    r.add_argument("--json", action="store_true", help="one JSON object per file (text, pages, fields)")
    a = ap.parse_args(argv)

    from .ocr import OCR

    ocr = OCR(a.model, backend=a.backend, enlarge_pages=not a.no_enlarge)
    for f, res in zip(a.files, ocr.read_many(a.files, mode=a.mode)):
        if a.json:
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
