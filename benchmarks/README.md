# Nuqta OCR benchmarks

Code to reproduce the KITAB-Bench and Misraj-DocOCR numbers in the Nuqta OCR model cards.

| File | What it does |
|---|---|
| `run.py` | Runs a model on the benchmark images and writes predictions, one `<set>.jsonl` per set, one `{"id", "ref", "hyp"}` object per line. The datasets are downloaded from the Hugging Face Hub at pinned revisions. |
| `score.py` | The scorer. It applies the published KITAB-Bench recipe, and the Misraj-DocOCR recipe from Baseer §7.1, to the prediction files. It does not depend on the `nuqta` package. |
| `kitab_official.py` | The KITAB-Bench scoring functions (text normalisation, `aug_html`, TEDS), copied unchanged from [KITAB-Bench](https://github.com/mbzuai-oryx/KITAB-Bench) (MIT licence, attribution in the file). |
| `excluded_ids.json` | The 114 KITAB PATS-OCR images whose text overlaps our training data (scored; `--exclude-overlap` drops them) (see [Test images left out](#test-images-left-out)). |

## Setup

```bash
git clone https://github.com/SalahAlHaismawi/nuqta-ocr && cd nuqta-ocr
pip install -e ".[bench,vllm]"     # use ".[bench]" alone if you only want to score existing predictions
```

The published numbers were produced with vLLM 0.19.1 (`vllm serve`), sacrebleu 2.6.0, Levenshtein 0.27.5, apted 1.0.3,
lxml 6.1.3 and beautifulsoup4 4.15.0.

## Reproducing the model-card numbers

The cards give two settings:

- **Images as given**: each test image goes to the model unchanged. Like every image, it is capped at the 2.4 MP
  training size.
- **With page enlarging**: the `nuqta` library's input rule (`nuqta.preprocess.prepare`). A page-shaped image
  (aspect ratio ≤ 2 and short side ≥ 450 px) smaller than 2.4 MP is enlarged to 2.4 MP. Line and word crops keep their
  size.

All runs use the same decoding settings, which are fixed in `run.py`:

- greedy decoding (temperature 0), repetition penalty 1.0, thinking disabled, at most 8192 new tokens
- the library's `as-written` prompt for the 13 KITAB OCR sets, and its `markdown` prompt for Misraj-DocOCR
- the output is kept raw (code fences stripped only): no loop trimming and no fallback re-read

### Nuqta-OCR 0.8B

```bash
vllm serve SalahALHaismawi/Nuqta-OCR-0.8B --served-model-name nuqta --max-model-len 16384 &

# images as given: the 13 KITAB-Bench OCR sets and Misraj-DocOCR
python benchmarks/run.py --sets kitab misraj --model nuqta --out results/0.8b/as-given
# with page enlarging: Hindawi (the KITAB set of full pages) and Misraj-DocOCR
python benchmarks/run.py --sets kitab_hindawi misraj --model nuqta --out results/0.8b/page-enlarging --page-enlarging

# KITAB-Bench, images as given
python benchmarks/score.py results/0.8b/as-given/kitab_*.jsonl
# KITAB-Bench, with page enlarging: the 12 other sets as given, Hindawi enlarged
python benchmarks/score.py $(ls results/0.8b/as-given/kitab_*.jsonl | grep -v hindawi) \
                           results/0.8b/page-enlarging/kitab_hindawi.jsonl
# Misraj-DocOCR, both settings
python benchmarks/score.py results/0.8b/as-given/misraj_dococr.jsonl --teds-jobs 4
python benchmarks/score.py results/0.8b/page-enlarging/misraj_dococr.jsonl --teds-jobs 4
```

### Nuqta-OCR 4B

These are the same commands with the 4B model served:

```bash
vllm serve SalahALHaismawi/Nuqta-OCR-4B --served-model-name nuqta --max-model-len 16384 &
python benchmarks/run.py --sets kitab misraj --model nuqta --out results/4b/as-given
python benchmarks/run.py --sets kitab_hindawi misraj --model nuqta --out results/4b/page-enlarging --page-enlarging
python benchmarks/score.py results/4b/as-given/kitab_*.jsonl
python benchmarks/score.py $(ls results/4b/as-given/kitab_*.jsonl | grep -v hindawi) results/4b/page-enlarging/kitab_hindawi.jsonl
python benchmarks/score.py results/4b/as-given/misraj_dococr.jsonl --teds-jobs 4
python benchmarks/score.py results/4b/page-enlarging/misraj_dococr.jsonl --teds-jobs 4
```

### Expected results

"With page enlarging" is what the model cards call the *recommended input size*.

| | KITAB macro CER | KITAB Hindawi CER | Misraj CER | WER | BLEU | chrF | TEDS | MARS |
|---|---|---|---|---|---|---|---|---|
| 0.8B, images as given | 0.132 (official 2 dp: 0.13) | 0.234 | 0.141 | 0.260 | 61.31 | 85.69 | 66.9 | 76.28 |
| 0.8B, with page enlarging | 0.117 | 0.033 | 0.130 | 0.241 | 63.56 | 87.42 | 66.8 | 77.09 |
| 4B, images as given | 0.111 (official 2 dp: 0.11) | 0.090 | 0.161 | 0.352 | 67.59 | 87.58 | 74.4 | 81.00 |
| 4B, with page enlarging | 0.106 | 0.029 | 0.121 | 0.246 | 68.42 | 89.43 | 76.1 | 82.78 |

`score.py` prints the per-set CER, the KITAB macro average rounded to 2 dp as KITAB-Bench's `ocr-eval/metrics.py`
does, and the unrounded macro mean that the cards quote.

The scorer is deterministic. We re-scored our saved prediction files with this `score.py`, and every metric matched
our internal scorer to full floating-point precision. A fresh run can still be a little off in the last digit. GPU
kernels and vLLM batching are not bit-reproducible, and one greedy token that flips early on a page changes the rest of
that page. The `--backend nuqta` path (in-process generation through the library, vLLM or transformers) uses the same
inputs and decoding, but transformers kernels differ from vLLM's, so expect small differences there too.

**Confidence intervals.** Add `--bootstrap 2000` and pass the 13 KITAB files and the Misraj file in **one** call (one
random stream, seed 0, runs over the KITAB subsets and then Misraj). This prints 95% intervals from resampled pages.
KITAB pages are resampled within each subset and Misraj pages over the whole set, with TEDS resampled over its table
pages.

```bash
python benchmarks/score.py results/0.8b/as-given/kitab_*.jsonl results/0.8b/as-given/misraj_dococr.jsonl --teds-jobs 4 --bootstrap 2000
```

### Why KITAB "with page enlarging" re-reads only Hindawi

Hindawi is the only KITAB OCR set made of full pages. Its 200 images are all 612x792 page renders with about 10 px
text, all page-shaped and all under 2.4 MP. The published "with page enlarging" KITAB figure re-reads Hindawi with
`--page-enlarging` and keeps the other 12 sets as given.

The page rule also matches 31 images in other sets: HistoricalBooks 10, KHATT 8, KHATT-paragraph 6, EvArEST 4 and
HistoryAr 3. To score the library's behaviour on every image, run `--sets kitab --page-enlarging`. That is a
different, unpublished variant, so its result can differ slightly from the table above.

For Misraj-DocOCR, the published "with page enlarging" run is exactly `--page-enlarging`: 253 of the 400 pages are
enlarged.

## Metrics

| Metric | Meaning |
|---|---|
| **CER** | Character error rate: total Levenshtein edits ÷ total reference characters over the whole set (a corpus rate, as torchmetrics `CharErrorRate` computes it; `--check-torchmetrics` re-checks it with torchmetrics). Lower is better. |
| **WER** | The same over whitespace-separated words. |
| **BLEU** | sacrebleu `corpus_bleu`, defaults. |
| **chrF** | sacrebleu `corpus_chrf`, defaults (chrF2, the version KITAB-Bench's code runs; the KITAB paper writes chrF3, so `score.py` prints that too). |
| **TEDS** | Tree-edit-distance similarity of HTML tables (KITAB-Bench `pdfs-eval`). On each page, every reference table is matched with its best predicted table (0 if none); the score is averaged over the 59 Misraj pages that have reference tables, ×100. Extra predicted tables cost nothing. |
| **MARS** | (chrF + TEDS) / 2, KITAB-Bench's "All Average" (α = 0.5), the headline Misraj-DocOCR metric in the Baseer paper. |
| **KITAB macro CER** | The unweighted mean of the 13 subsets' corpus CERs (KITAB-Bench's headline OCR number). |

Text normalisation is KITAB-Bench's `preprocess_arabic_text`. Newlines and tabs become spaces, and tashkeel
(U+064B-U+065F, U+0670) is removed. The alef forms [إأٱآ] become ا, ة becomes ه, ى becomes ي, tatweel is removed and
whitespace is collapsed. The benchmarks therefore do **not** score diacritics. Punctuation, digits and markdown syntax
are left as they are in the text metrics.

**Misraj-DocOCR recipe.** Misraj published no scoring code. The Baseer paper (arXiv:2509.18174 §7.1) lists six
output-standardisation steps and reuses KITAB-Bench's metrics, so `score.py` does the following:

- converts markdown pipe tables to HTML
- cuts out `<table>` blocks and scores them with TEDS only (as in KITAB-Bench `pdfs-eval`), so table cells do not count
  in CER, WER, BLEU or chrF
- drops `<img>` placeholders
- unwraps `<page_number>` and `<watermark>` (their text stays) and every other HTML tag outside tables
- turns horizontal rules into "—" and normalises "#  Heading" to "# Heading"

Nothing is clipped or trimmed, so a runaway (looping) prediction counts in full. `--trim-loops` (the library's
loop trimming) and `--clip-runaways` exist for diagnosis, but they are not the published setting.

## Test images left out

All 500 PATS-OCR images are scored, as in the official benchmark (13 KITAB sets, 3,760 images). 114 of them have
text (at least half of their 50-character shingles) that also appears in our synthetic training renders or Wikisource
training pages; their ids are in `excluded_ids.json`, and `run.py --exclude-overlap` leaves them out. Leaving them out
does not flatter the models: PATS CER is 0.011 (4B) and 0.014 (0.8B) on all 500, and 0.011 / 0.014 on the other 386.

The model cards also disclose 234 KITAB images that appear in public datasets we trained on: all 200 KHATT-paragraph
pages, the 10 HistoricalBooks pages, 13 Muharaf images and 11 KHATT-line images. These are **kept** in the published
numbers. Misraj-DocOCR has no such overlap.

## Competitor numbers

The other models' numbers in the cards come from their papers and leaderboards: Gemini-2.0-Flash, AIN-7B, GPT-4o,
Qwen-2.5-VL, Tesseract and EasyOCR from [KITAB-Bench](https://github.com/mbzuai-oryx/KITAB-Bench)
([arXiv:2502.14949](https://arxiv.org/abs/2502.14949)); Baseer, Gemini-2.5-Pro, Azure Document Intelligence, dots.ocr
and QARI on Misraj-DocOCR from the [Baseer paper](https://arxiv.org/abs/2509.18174). We did not re-run those models
with this code.

## Options

```
run.py   --sets kitab | misraj | <set names>    groups or single sets (kitab_pdf2md_reviewed is also available)
         --backend endpoint|nuqta                an OpenAI-compatible server (default) or the library in-process
         --page-enlarging                        the library's page rule (default: images as given)
         --url, --api-key, --concurrency         endpoint options;  --nuqta-backend auto|vllm|transformers, --batch
         --limit N                               first N images per set (smoke test)
         --data-dir DIR                          read DIR/<set>/**/*.parquet instead of downloading
         --revision REV                          another dataset revision (numbers may then differ)
score.py FILES|DIRS  --teds-jobs N  --bootstrap N  --json out.json  --recipe kitab|misraj
         --trim-loops  --clip-runaways  --check-torchmetrics  (diagnostics, not the published setting)
```

Runs can be resumed: ids already present in an output file are skipped, and failed requests are not written. If an
output folder was made with other settings, `run.py` refuses to write to it.
