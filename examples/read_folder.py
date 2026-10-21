"""Read every image / PDF in a folder to markdown files next to them.   python examples/read_folder.py <folder> [model]"""
import sys
from pathlib import Path

from nuqta import OCR

if __name__ == "__main__":
    folder = Path(sys.argv[1])
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".pdf"})
    ocr = OCR(sys.argv[2] if len(sys.argv) > 2 else "nuqta-0.8b")
    for f, r in zip(files, ocr.read_many(files, mode="markdown")):
        f.with_suffix(".md").write_text(r.text, encoding="utf-8")
        print(f"{f.name}: {len(r.pages)} page(s){'  (repetition trimmed)' if any(p.looped for p in r.pages) else ''}")
