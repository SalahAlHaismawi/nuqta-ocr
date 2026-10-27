<p align="center"><img src="https://raw.githubusercontent.com/SalahAlHaismawi/nuqta-ocr/main/assets/nuqta_logo.png" alt="Nuqta OCR" width="440"></p>

# Nuqta OCR: open-source Arabic OCR

Accurate Arabic document OCR with **faithful tashkeel**, in two open models: **Nuqta-Arabic-OCR 4B** (#1 on KITAB-Bench and Misraj-DocOCR among published results) and **Nuqta-Arabic-OCR 0.8B** (best for its size: ahead of Gemini-2.0-Flash on KITAB-Bench, just behind Misraj's Baseer v2 on Misraj-DocOCR, runs on phones).

- Reads books, scans, official documents, tables, IDs and passports
- Copies the tashkeel printed on the page and almost never adds any (0.08–0.16 invented marks per 100 letters)
- Markdown output with HTML tables, in reading order
- Runs on-premises on a single GPU, or fully offline on Android and iPhone: your documents never leave your network

Website: [https://salahalhaismawi.github.io/nuqta-ocr/](https://salahalhaismawi.github.io/nuqta-ocr/) · [Arabic OCR benchmarks compared](https://salahalhaismawi.github.io/nuqta-ocr/best-arabic-ocr/) · [guides](https://salahalhaismawi.github.io/nuqta-ocr/guides/) · [demo](https://huggingface.co/spaces/SalahALHaismawi/Nuqta-Arabic-OCR)

<div dir="rtl">

**بالعربية:** «نقطة» مكتبة ونماذج مفتوحة المصدر للتعرف الضوئي على النص العربي (OCR عربي). تحوّل صور الصفحات والمستندات الممسوحة
ضوئيًا وملفات PDF إلى نص أو Markdown، وتستخرج الجداول، وتقرأ البطاقات الشخصية وجوازات السفر، وتنقل التشكيل المطبوع كما هو.
النموذج 4B هو الأول على معياري KITAB-Bench وMisraj-DocOCR بين النتائج المنشورة. [جرّبه مجانًا](https://huggingface.co/spaces/SalahALHaismawi/Nuqta-Arabic-OCR).

</div>

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

## On phones and laptops, offline

- **Android and iPhone apps:** [`apps/`](apps) has two small apps that run the 0.8B entirely on the phone (CPU on
  Android, GPU on iPhone), with the first words in about 2 seconds. Build steps are in [apps/README.md](apps/README.md).
- **GGUF for llama.cpp, LM Studio, Ollama and other local apps:**
  [Nuqta-Arabic-OCR-0.8B-GGUF](https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-0.8B-GGUF) (560 MB at 4-bit) and
  [Nuqta-Arabic-OCR-4B-GGUF](https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B-GGUF) (2.9 GB). The files carry the reading
  settings (greedy decoding, thinking off, a minimum image size), so most apps read well without setup; the cards
  list the settings to check in apps that override them.

## Speed (0.8B, one 24 GB GPU)

| | vLLM | transformers + `[fast]` |
|---|---|---|
| text line | ~0.2 s | ~1 s |
| book page | ~3 s | ~3.5 s |
| markdown document page | ~3 s | ~6 s |

## Results

| | KITAB-Bench CER ↓ | Misraj-DocOCR MARS ↑ |
|---|---|---|
| **Nuqta-Arabic-OCR 4B** | **0.106** | **82.8** |
| **Nuqta-Arabic-OCR 0.8B** | **0.117** | 77.1 |
| Best other published result | 0.13 (Gemini-2.0-Flash) | 77.8 (Baseer v2, Misraj, Sept 2026) |

Recommended input size (what the library does). The 4B is first on both; the 0.8B is ahead of every other published
KITAB-Bench result and third on Misraj-DocOCR, just behind Baseer v2. Our Misraj-DocOCR scorer reproduces Misraj's own published
score for Qwen3-VL-8B to within a point (MARS 52.5 vs 51.8), and our exact predictions are in
[benchmarks/predictions](benchmarks/predictions/misraj_dococr) for anyone to re-score. Other models' figures are the ones published by
the KITAB-Bench authors and by Misraj ([Baseer paper](https://arxiv.org/abs/2509.18174),
[September 2026 results table](https://misraj.ai/en/blogs/baseer-arabic-document-ocr-vlm-misraj)).

Full tables, confidence intervals and disclosures are in the model cards; the full benchmarks are
[KITAB-Bench](https://github.com/mbzuai-oryx/KITAB-Bench) and [Misraj-DocOCR](https://huggingface.co/datasets/Misraj/Misraj-DocOCR).

## License

Code: Apache-2.0. Models: see their model cards.

## Contributors

Salah AlHaismawi · Mohamed Saleh Tulib · Ahmed ElSayed Mohamed Ibrahim
