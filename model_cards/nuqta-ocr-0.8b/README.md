---
license: apache-2.0
language:
- ar
base_model: Qwen/Qwen3.5-0.8B
pipeline_tag: image-text-to-text
library_name: transformers
tags:
- ocr
- arabic
- arabic-ocr
- tashkeel
- diacritics
- diacritization
- handwriting
- document-understanding
- document-ai
- pdf-to-markdown
- table-recognition
- id-card
- passport
- mrz
- markdown
- text-recognition
- image-to-text
- arabic-nlp
- pdf
model-index:
- name: Nuqta-Arabic-OCR 0.8B
  results:
  - task:
      type: image-to-text
      name: Arabic OCR
    dataset:
      name: KITAB-Bench (OCR, 13 datasets)
      type: KITAB-Bench
    metrics:
    - type: cer
      value: 0.117
      name: CER (macro, recommended input size)
    source:
      name: KITAB-Bench
      url: https://github.com/mbzuai-oryx/KITAB-Bench
  - task:
      type: image-to-text
      name: Arabic document OCR
    dataset:
      name: Misraj-DocOCR
      type: Misraj/Misraj-DocOCR
    metrics:
    - type: cer
      value: 0.13
      name: CER
    - type: chrf
      value: 87.4
      name: chrF
    - type: teds
      value: 66.8
      name: TEDS (tables)
    - type: mars
      value: 77.1
      name: MARS
    source:
      name: Misraj-DocOCR / Baseer
      url: https://huggingface.co/datasets/Misraj/Misraj-DocOCR
---

<p align="center"><img src="nuqta_logo.png" alt="Nuqta OCR" width="440"></p>

# Nuqta-Arabic-OCR 0.8B

Open-source **Arabic OCR** model with under 1B parameters, small enough for a phone. It is ahead of Gemini-2.0-Flash, AIN-7B and GPT-4o on KITAB-Bench and on Misraj-DocOCR it is just behind Misraj's own Baseer v2 and ahead of Gemini-2.5-Pro and GPT-5 (recommended input size).

**Nuqta-Arabic-OCR 0.8B** is an open-weights **Arabic OCR** model. It converts Arabic scans, photos and PDFs (books, official
documents, research papers, tables, forms, IDs and passports) into clean text or Markdown with HTML tables, in reading
order, and it **copies the tashkeel printed on the page and almost never adds any** (0.08–0.16 invented marks per 100
letters on undiacritized text).

Part of the [Nuqta OCR](https://huggingface.co/collections/SalahALHaismawi/nuqta-ocr-6ad4af255195b706ac93d1d4) family ·
[Nuqta-Arabic-OCR 4B](https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B) · [demo](https://huggingface.co/spaces/SalahALHaismawi/Nuqta-Arabic-OCR) ·
[library and benchmark code](https://github.com/SalahAlHaismawi/nuqta-ocr) · Apache-2.0

**Contributors:** Salah AlHaismawi · Mohamed Saleh Tulib · Ahmed ElSayed Mohamed Ibrahim

## Highlights

- **KITAB-Bench: CER 0.117**, against Gemini-2.0-Flash 0.13, AIN-7B 0.20 and GPT-4o 0.31 (13 Arabic OCR datasets; 0.132 with the images as given).
- **Misraj-DocOCR: MARS 77.1** (76.3 with the images as given): just behind Misraj's own Baseer v2 (77.8), ahead of the original Baseer (76.9), Gemini-2.5-Pro (70.8) and GPT-5 (54.8).
- **Faithful tashkeel:** 0.08 invented diacritics per 100 letters on undiacritized text, and vocalized pages keep their marks.
- **Tables** as HTML in the order they are drawn (left-to-right or right-to-left), merged cells included; column order right on 95% / 96% of rendered mixed-direction test tables.
- **IDs and passports:** 79.2% of fields correct on real ID cards and 84.9% on real passports (held-out, no training overlap), with ICAO check-digit validation of the MRZ.
- **Stable:** essentially no repetition loops; the `nuqta-ocr` library adds a loop guard on top.
- **Open and on-premises:** your documents never leave your network. Runs on a single small GPU (about 3 GB in bf16): ~3 s per document page one at a time with vLLM (faster batched), ~0.2 s per text line.

<p align="center"><img src="results_chart.png" alt="KITAB-Bench and Misraj-DocOCR results" width="100%"></p>

## Examples

Real outputs of Nuqta-Arabic-OCR 0.8B, through the `nuqta-ocr` library. Sources: a Hindawi book page (CC BY 4.0), a
Misraj-DocOCR page (Apache-2.0), and a synthetic passport and diagram we generated (no real person's document).

![Faithful tashkeel](examples/example_book.png)
![Tables](examples/example_table.png)
![Passport fields](examples/example_id.png)
![Diagram](examples/example_diagram.png)

## Benchmarks

All Nuqta numbers are our runs, scored with **KITAB-Bench's own scoring code** (copied unchanged). Misraj published no scoring code, so for Misraj-DocOCR we follow the recipe in the Baseer paper (§7.1) on top of that same code; competitor numbers are the published
figures. For the full benchmarks, every subset and the other models' results, see
[KITAB-Bench](https://github.com/mbzuai-oryx/KITAB-Bench) and
[Misraj-DocOCR](https://huggingface.co/datasets/Misraj/Misraj-DocOCR) (leaderboard in the
Baseer paper, updated in [Misraj's September 2026 results table](https://misraj.ai/en/blogs/baseer-arabic-document-ocr-vlm-misraj)). *Recommended input size* = how the model is meant to be
used, and what the `nuqta-ocr` library, the demo and the code below do: a page-shaped image smaller than the model's
2.4-megapixel training size is enlarged to it, while line and word crops are read as they are. *Images as given* =
each test image sent to the model unchanged (apart from the same 2.4 MP cap). Evaluation code to reproduce every number: [nuqta-ocr/benchmarks](https://github.com/SalahAlHaismawi/nuqta-ocr/tree/main/benchmarks).

### KITAB-Bench: OCR track (13 datasets, 3,760 images), character error rate ↓

With the recommended input size only the Hindawi pages change (they are small 612x792 page renders); the other 12 datasets are crops or full-size pages, read as given.

| Model | Size | CER |
|---|---|---|
| **Nuqta-Arabic-OCR 0.8B**, recommended input size | 0.89B | **0.117** |
| Nuqta-Arabic-OCR 0.8B, images as given | 0.89B | 0.132 (95% CI 0.127-0.139) |
| Gemini-2.0-Flash | closed | 0.130 |
| AIN-7B | 7B | 0.200 |
| GPT-4o | closed | 0.310 |
| Qwen-2.5-VL | 7B | 0.492 |
| Tesseract | - | 0.540 |
| EasyOCR | - | 0.580 |

<details><summary><b>Every KITAB-Bench dataset (Nuqta-Arabic-OCR 0.8B, images as given)</b></summary>

| Dataset | CER |
|---|---|
| Adab (word crops) | 0.246 |
| ArabicOCR (lines) | 0.028 |
| EvArEST (scene text) | 0.155 |
| Hindawi (book pages) | 0.234 |
| Historical books | 0.179 |
| HistoryAr (manuscripts) | 0.187 |
| ISI-PPT (slides) | 0.035 |
| KHATT (handwritten lines) | 0.125 |
| KHATT paragraphs | 0.082 |
| Muharaf (manuscripts) | 0.270 |
| Online-KHATT | 0.126 |
| PATS (fonts) | 0.014 |
| SynthesizeAr (synthetic) | 0.040 |

Hindawi's small 612x792 page renders are read far better at the recommended input size (CER 0.033).
</details>

**Contamination disclosure.** 234 KITAB test images (all 200 KHATT-paragraph pages, the 10 HistoricalBooks pages,
13 Muharaf and 11 KHATT-line images) also appear in public datasets we trained on. Without them the macro CER is
**0.131** (11 datasets, images as given). PATS-OCR is scored on all 500 lines, including 114 whose text
also appears in our training data (scores are the same or better without them). Misraj-DocOCR has no such overlap.

### Misraj-DocOCR (400 real Arabic document pages)

| Model | Size | CER ↓ | WER ↓ | BLEU ↑ | chrF ↑ | TEDS ↑ | MARS ↑ |
|---|---|---|---|---|---|---|---|
| **Nuqta-Arabic-OCR 0.8B**, recommended input size | 0.89B | 0.13 | 0.241 | 63.6 | 87.4 | 66.8 | 77.1 |
| Nuqta-Arabic-OCR 0.8B, images as given | 0.89B | 0.141 | - | - | 85.7 | 66.9 (95% CI 59.2-74.7) | 76.3 |
| Baseer v2 (Misraj, September 2026) | not stated | **0.12** | **0.19** | 76.3 | 88.9 | **67** | **77.8** |
| Baseer (paper) | 3B | 0.53† | 0.25 | - | 87.8 | 66 | 76.9 |
| Gemini-2.5-Pro | closed | 0.31 | 0.37 | **77.9** | **89.6** | 52 | 70.8 |
| Azure Document Intelligence | closed | 0.27 | 0.44 | 62.0 | 82.5 | 42 | 62.2 |
| dots.ocr | 3B | 0.40 | 0.50 | 58.2 | 78.4 | 40 | 59.2 |
| GPT-5 | closed | 0.62 | 0.86 | 40.7 | 61.6 | 48 | 54.8 |
| Mistral OCR | closed | 0.42 | 0.49 | 52.4 | 71.8 | 17 | 44.4 |
| QARI | - | 0.64 | 0.76 | 38.6 | 64.5 | 21 | 42.8 |

Bold = best in each column. Every other model's numbers are Misraj's: the Baseer paper and their September 2026
results table, which added Baseer v2 (no public weights that we could find; its demo is baseerocr.com) and GPT-5. The 0.8B is third on MARS, behind the 4B and Baseer v2.

† As printed in the Baseer paper. It is higher than Baseer's own WER (0.25), unlike every other row of that
table, so it was probably computed with different text cleanup; Baseer's weights are not public, so we could not
re-score it, and we make no CER comparison with Baseer.

TEDS rests on 59 table pages and moves by several points between comparable models; MARS = (chrF + TEDS) / 2.
Tables written where the reference has one: 55 / 59.

**Scorer check.** Misraj's scoring code is not public, so we checked ours against a row they did publish. We ran
Qwen3-VL-8B-Instruct on all 400 pages with a plain Markdown prompt. Our scorer gives it chrF 54.7, TEDS 50.3 and MARS
52.5, against Misraj's 54.5, 49 and 51.8. Each part lands within about a point, so the numbers in this table are on
Misraj's scale. Our exact predictions for every Nuqta number, and for this check, are in
[benchmarks/predictions](https://github.com/SalahAlHaismawi/nuqta-ocr/tree/main/benchmarks/predictions/misraj_dococr)
for anyone to score with their own code.

### Beyond the benchmarks

| | Nuqta-Arabic-OCR 0.8B |
|---|---|
| Invented diacritics on undiacritized text | 0.08 per 100 letters |
| Table column order, rendered mixed-direction web tables (left-to-right / right-to-left) | 95% / 96% correct |
| Diagrams (KITAB diagrams, boxes read intact, in reading order) | 87.3% |
| Real ID cards, fields correct (held-out) | 79.2% |
| Real passports, fields correct / MRZ valid | 84.9% / 85.7% |
| Privacy check: training ID numbers reproduced on other cards | 0 of 633 numbers |

**Urdu and Jawi, never trained on.** Nuqta was trained for Arabic (and the English printed alongside it), not for
Urdu or Jawi. On a page rendered from a Malay news article written in Jawi the 0.8B gets 94.5% of characters right,
as well as the 4B; nearly every miss is a letter Arabic does not have (ڤ read as ق or ف, ڠ as غ, ڬ as ك). Urdu is
weaker: 78.5% on a page rendered from an Urdu Wikipedia article in Naskh type and 62% in Nastaliq, the usual Urdu book
and newspaper style (the 4B: 93% and 87%). These are single-page spot checks with the default prompt, not benchmarks.

## What makes Nuqta different

**Architecture: a deeper attention stack.** Nuqta builds on [Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B), a
vision-language model whose decoder mixes linear-attention layers (Gated DeltaNet) with a few full-attention layers
(6 of 24). Reading a dense Arabic page means relating every letter and diacritic to text
far away on the page, which is what full attention does best, so we **grew the decoder by two extra full-attention
layers** (after decoder layers 11 and 23): **26 layers, 8 with full attention**. The new layers start as an exact
identity (zero-initialised output projections), so the pretrained model is undisturbed at step 0, and they train at
twice the learning rate of the rest of the decoder.

| | |
|---|---|
| Parameters | 0.89B (0.10B vision encoder) |
| Decoder | 26 layers (8 full attention, of which 2 added; 18 linear attention), hidden size 1024 |
| Input | images up to 2.4 megapixels; PDFs page by page |
| Output | up to 8,192 tokens: text or Markdown with HTML tables |
| Modes | as written · without tashkeel · Markdown · ID fields |

**Data: exact labels, not guesses.** Training pages come with labels that are exact by construction or verified:
born-digital documents and PDF text layers, rendered books and web pages, official gazettes, real scans aligned to
their source text, real and synthetic tables with HTML labels, forms, receipts, ID cards and passports, diagrams with
block-ordered labels, and handwritten pages, across 172 sources. Labels from automatic readers were only kept where
independent readings agreed. All benchmark test sets were excluded from training (see the disclosure above for the
public-dataset overlap we found afterwards).

**Where the ID and passport data comes from.** Real cards and passports: 7,846 images from 64 public
[Roboflow Universe](https://universe.roboflow.com) projects, by licence 7,384 CC BY 4.0, 314 MIT, 128 public domain,
and 20 from two projects with no open licence stated. Their text labels were kept only where the MRZ check
digits or two independent readings agreed. Also used: [MIDV-LAIT](https://doi.org/10.1007/978-3-030-86331-9_17) (mock
documents with synthetic holders, CC BY-SA 2.5) and our own synthetic cards and passports for 18 countries. The
evaluation cards are held out (no image or holder overlap), and a privacy test checks that the model does not
reproduce training ID numbers on other cards (0 of 633 reproduced).

**Training.** 40,000 steps from Qwen3.5-0.8B (effective batch 16, AdamW 8-bit, peak LR 2e-5 for the decoder and 2e-6 for the vision encoder, warmup-stable-decay schedule); from step 30,000 a curated annealing mix (verified real pages, tables, IDs, layouts and diagrams) while the learning rate decays. Then reinforcement-learning rounds with weight averaging between them (GRPO-style, on-policy samples scored against exact labels): rewards for complete, faithful reading, table structure and numbers, valid ID check digits, and penalties for repetition loops, invented diacritics and foreign-script leaks; in the last round the 0.8B also learned tables from the 4B's readings of 543 real document pages. After it, none of the 3,760 KITAB-Bench images runs away (official runaway check). Compute: one NVIDIA RTX PRO 6000 GPU (96 GB) for the supervised stage (about 4.6 s per step), one GPU per reinforcement-learning round.

**Faithful tashkeel by design.** Every training page is labelled with exactly the diacritics printed on it, so the
model learns to copy tashkeel, not to add it.

## How to use

With 🤗 Transformers:

```python
import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

repo = "SalahALHaismawi/Nuqta-Arabic-OCR-0.8B"
processor = AutoProcessor.from_pretrained(repo)
model = AutoModelForImageTextToText.from_pretrained(repo, dtype=torch.bfloat16, device_map="auto")

def prepare(im):  # recommended input size: pages to the 2.4 MP training size, crops as they are, all capped at 2.4 MP
    w, h = im.size
    page = max(w, h) <= 2 * min(w, h) and min(w, h) >= 450
    if page or w * h > 2_400_000:
        k = (2_400_000 / (w * h)) ** 0.5
        im = im.resize((max(32, int(w * k)), max(32, int(h * k))), Image.LANCZOS)
    return im

prompt = "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image."
messages = [{"role": "user", "content": [{"type": "image", "image": prepare(Image.open("page.jpg").convert("RGB"))}, {"type": "text", "text": prompt}]}]
inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True,
                                       return_tensors="pt", enable_thinking=False).to(model.device)
out = model.generate(**inputs, max_new_tokens=8192, do_sample=False)
print(processor.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True))
```

With vLLM: `vllm serve SalahALHaismawi/Nuqta-Arabic-OCR-0.8B`, then send the `prepare`d image and prompt to the OpenAI-compatible chat endpoint with
`temperature 0` and `chat_template_kwargs: {"enable_thinking": false}`.

### With the nuqta-ocr library

The library adds page enlarging, PDF input, the loop guard and ID field parsing:

```bash
pip install "nuqta-ocr[vllm]"      # or "nuqta-ocr[fast]" for transformers with fast kernels
```

```python
from nuqta import OCR

if __name__ == "__main__":
    ocr = OCR("nuqta-0.8b")
    print(ocr.read("page.jpg").text)                       # as written: tashkeel only where printed
    print(ocr.read("scan.pdf", mode="markdown").text)      # headings, lists, HTML tables; every page
    print(ocr.read("passport.jpg", mode="id").fields)      # MRZ fields + check digits
```

Command line: `nuqta read scan.pdf --mode markdown --model nuqta-0.8b`.

### Prompts and settings

Use the prompts below with the model's chat template (thinking disabled, greedy decoding, stop tokens `<|im_end|>`
and `<|endoftext|>`). The snippet above already applies the recommended input size: page-shaped images
(aspect ratio ≤ 2, short side ≥ 450 px) resized to about 2.4 megapixels, crops kept at their size, every image capped
at 2.4 MP. (The `nuqta-ocr` library also re-reads a page at its native size if the first reading repeats itself.)

| Mode | Prompt |
|---|---|
| as-written | `Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image.` |
| bare | `Transcribe the Arabic text in this image without any diacritics.` |
| markdown | `Convert this document to Markdown: headings, paragraphs, lists and tables in reading order. Include only the diacritics visible in the image.` |

### On phones and laptops (GGUF, llama.cpp)

[Nuqta-Arabic-OCR-0.8B-GGUF](https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-0.8B-GGUF) runs fully offline with
llama.cpp on Android, iOS, Mac, Windows and Linux: 560 MB at 4-bit plus a 205 MB vision file, about 1.6 GB of RAM.
The 4-bit build matches this model's accuracy on KITAB-Bench pages (Hindawi book pages with tashkeel: CER 0.028 vs
0.031 in bf16). Settings and measured speeds are on its card.

## Limitations

- Handwriting is usable (KITAB KHATT lines CER 0.125) but less reliable than print, and historical manuscripts are
  weak (Muharaf 0.270); on unclear handwriting the model can substitute a familiar word for a rare one.
- Decorative calligraphy is not supported, and on Quranic or calligraphic script the model can add marks that are
  not printed (for example on hamzat al-wasl).
- ID and passport fields should be reviewed by a person; `id` mode reports failed check digits and inconsistent
  national numbers instead of correcting them.
- Dotted leader lines in tables of contents are not copied.
- Tables: the 0.8B may reorder or drop columns, especially in small mixed Arabic / English tables that start with an English column (every cell is still read correctly). Use the 4B for tables; a fix is in training.


## References

- *KITAB-Bench: A Comprehensive Multi-Domain Benchmark for Arabic OCR and Document Understanding* (MBZUAI, 2025) ·
  [code and leaderboard](https://github.com/mbzuai-oryx/KITAB-Bench)
- *Misraj-DocOCR* · [dataset](https://huggingface.co/datasets/Misraj/Misraj-DocOCR); evaluation recipe and leaderboard
  in the *Baseer* paper (Misraj AI, 2025)
- Base model: [Qwen3.5](https://huggingface.co/Qwen)

## Contributors

- **Salah AlHaismawi**
- **Mohamed Saleh Tulib**
- **Ahmed ElSayed Mohamed Ibrahim**

## License

Apache-2.0.

## Citation

```bibtex
@misc{nuqta_ocr_2026,
  title  = {Nuqta OCR: Accurate Arabic Document OCR with Faithful Tashkeel},
  author = {Salah AlHaismawi and Mohamed Saleh Tulib and Ahmed ElSayed Mohamed Ibrahim},
  year   = {2026},
  url    = {https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-0.8B}
}
```
