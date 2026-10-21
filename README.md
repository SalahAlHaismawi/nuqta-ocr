<p align="center"><img src="https://raw.githubusercontent.com/SalahAlHaismawi/nuqta-ocr/main/assets/nuqta_logo.png" alt="Nuqta OCR" width="440"></p>

# Nuqta OCR

Accurate Arabic document OCR with **faithful tashkeel**, in two open models: **Nuqta-OCR 4B** (#1 on KITAB-Bench and Misraj-DocOCR among published results) and **Nuqta-OCR 0.8B** (best for its size: ahead of Gemini-2.0-Flash, level with or slightly ahead of Baseer, runs on phones).

- Reads books, scans, official documents, tables, IDs and passports
- Copies the tashkeel printed on the page and almost never adds any (0.08–0.16 invented marks per 100 letters)
- Markdown output with HTML tables, in reading order
- Runs on-premises on a single GPU: your documents never leave your network

## Install

```bash
pip install "nuqta-ocr[vllm]"   # recommended: fast, batched (Linux + NVIDIA GPU)
pip install "nuqta-ocr[fast]"   # transformers + fast kernels (no vLLM needed)
pip install nuqta-ocr           # transformers only (slow on long pages)
```

## Quick start

```python
from nuqta import OCR

if __name__ == "__main__":          # required with the vLLM backend (it starts worker processes)
    ocr = OCR("nuqta-0.8b")              # or "nuqta-4b" (most accurate)

    print(ocr.read("page.jpg").text)                        # as written: tashkeel only where printed
    print(ocr.read("scan.pdf", mode="markdown").text)       # headings, lists, HTML tables; every page
    print(ocr.read("passport.jpg", mode="id").fields)       # MRZ fields + check digits

    results = ocr.read_many(["a.jpg", "b.png", "c.pdf"])    # batched with vLLM
```

Command line:

```bash
nuqta read page.jpg
nuqta read scan.pdf --mode markdown
nuqta read passport.jpg --mode id --json
```

## Modes

| mode | output |
|---|---|
| `as-written` (default) | the text exactly as printed, tashkeel only where it is printed |
| `bare` | the text without any tashkeel |
| `markdown` | headings, paragraphs, lists and tables (HTML) in reading order |
| `id` | `markdown` reading + structured fields: passport / visa / ID-card MRZ with ICAO check digits; Egyptian national ID fields cross-checked against the national number |

## What the library does for you

- **Page rule:** full pages are shown to the model at its training resolution (2.4 MP); word, line and card crops keep their size. Small page renders (e.g. 72-dpi PDF pages) otherwise lose letters.
- **Loop guard:** if a page reading repeats itself, the page is re-read at its native size; any repetition left is trimmed (`Page.looped` tells you).
- **PDFs:** every page rendered at 200 dpi.
- **ID checks:** a failed check digit or an inconsistent national number is reported, never silently "fixed". Send those fields to a human.

## Speed (0.8B, one 24 GB GPU)

| | vLLM | transformers + `[fast]` |
|---|---|---|
| text line | ~0.2 s | ~1 s |
| book page | ~3 s | ~3.5 s |
| markdown document page | ~3 s | ~6 s |

## Results

| | KITAB-Bench CER ↓ | Misraj-DocOCR MARS ↑ |
|---|---|---|
| **Nuqta-OCR 4B** | **0.106** | **82.8** |
| **Nuqta-OCR 0.8B** | **0.117** | **77.1** |
| Previous best (Gemini-2.0-Flash / Baseer) | 0.13 | 76.9 |

Recommended input size (what the library does). The 0.8B's lead over Baseer is within the benchmark's noise.

Full tables, confidence intervals and disclosures are in the model cards; the full benchmarks are
[KITAB-Bench](https://github.com/mbzuai-oryx/KITAB-Bench) and [Misraj-DocOCR](https://huggingface.co/datasets/Misraj/Misraj-DocOCR).

## License

Code: Apache-2.0. Models: see their model cards.

## Contributors

Salah AlHaismawi · Mohamed Saleh Tulib · Ahmed ElSayed Mohamed Ibrahim
