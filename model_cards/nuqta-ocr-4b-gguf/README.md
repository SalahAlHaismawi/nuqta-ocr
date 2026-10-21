---
license: apache-2.0
language:
- ar
base_model: SalahALHaismawi/Nuqta-OCR-4B
pipeline_tag: image-text-to-text
library_name: gguf
tags:
- ocr
- arabic
- arabic-ocr
- tashkeel
- diacritics
- gguf
- llama.cpp
- on-device
---

<p align="center"><img src="nuqta_logo.png" width="160" alt="Nuqta OCR"></p>

# Nuqta-OCR 4B GGUF: the most accurate Nuqta model, offline

This repo holds the GGUF build of [Nuqta-OCR-4B](https://huggingface.co/SalahALHaismawi/Nuqta-OCR-4B) for
[llama.cpp](https://github.com/ggml-org/llama.cpp). It reads Arabic documents, copies the tashkeel that is printed
and almost never adds any, and runs fully offline on Mac, Windows and Linux. It needs **about 6 GB of RAM** at 4-bit, so it suits
laptops and desktops; for phones use [Nuqta-OCR-0.8B-GGUF](https://huggingface.co/SalahALHaismawi/Nuqta-OCR-0.8B-GGUF).

| File | Size | Use |
|---|---|---|
| `nuqta-ocr-4b-Q4_K_M.gguf` | 2.9 GB | laptops and desktops (recommended) |
| `nuqta-ocr-4b-Q8_0.gguf` | 4.8 GB | closest to the original |
| `nuqta-ocr-4b-mmproj-f16.gguf` | 672 MB | vision encoder, **always needed** next to the model |

## Accuracy against the full model

We scored Q4_K_M (llama.cpp, CPU) against the bf16 model (vLLM) with the same prompts, image sizes and scoring:
greedy decoding, KITAB-Bench normalisation, character error rate (lower is better), on the same pages.

| KITAB-Bench set (first 20 images) | bf16 | Q4_K_M GGUF |
|---|---|---|
| Hindawi (book pages with tashkeel, at the recommended input size) | 0.026 | 0.022 |
| PATS-OCR (printed lines) | 0.011 | 0.014 |
| SynthesizeAR (synthetic lines) | 0.034 | 0.034 |
| Adab (poetry word crops) | 0.226 | 0.229 |

All differences are within page-to-page noise. On the full benchmarks the 4B model scores KITAB-Bench CER 0.106
and Misraj-DocOCR MARS 82.8, first on both: see the [main model card](https://huggingface.co/SalahALHaismawi/Nuqta-OCR-4B).

## Run it

```bash
llama-mtmd-cli -m nuqta-ocr-4b-Q4_K_M.gguf --mmproj nuqta-ocr-4b-mmproj-f16.gguf \
  --image page.png --temp 0 -c 8192 --image-max-tokens 4096 \
  -p "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image."
```

Or serve an OpenAI-compatible API (one image plus the prompt per request):

```bash
llama-server -m nuqta-ocr-4b-Q4_K_M.gguf --mmproj nuqta-ocr-4b-mmproj-f16.gguf \
  -c 8192 --image-max-tokens 4096 --temp 0 --port 8080
```

Any app built on a recent llama.cpp with multimodal support (`mtmd`, Qwen3.5 architecture) can load these two
files. Tested with llama.cpp commit `5aeac37` (October 2026).

### Three settings that matter

1. **Use the recommended input size.** Enlarge page-shaped images (long side ≤ 2× short side, short side ≥ 450
   px) to about 2.4 megapixels, the model's training size; leave line and word crops as they are; never go above
   2.4 MP.
2. **Pass `--image-max-tokens 4096`**, so llama.cpp doesn't shrink the page again.
3. **Set `-c 8192`.** It is enough for a full page and keeps memory at about 6 GB.

The model may begin its answer with an empty `<think></think>` block: drop it.

### Prompts

| Mode | Prompt |
|---|---|
| as written (default) | `Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image.` |
| no tashkeel | `Transcribe the Arabic text in this image without any diacritics.` |
| Markdown (tables, headings) | `Convert this document to Markdown: headings, paragraphs, lists and tables in reading order. Include only the diacritics visible in the image.` |

## Speed

On a laptop CPU alone (8 threads, no GPU), Q4_K_M reads a full 2.4 MP book page in about 2.5 minutes. With a GPU
(Metal on Apple silicon, CUDA or Vulkan) it is much faster; for high-volume serving use the original model with vLLM
(about 1.8 s per page, batched).

## Contributors

Salah AlHaismawi · Mohamed Saleh Tulib · Ahmed ElSayed Mohamed Ibrahim

## License

Apache 2.0, like the original model. Built on [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B).

## Citation

```bibtex
@misc{nuqta_ocr_2026,
  title  = {Nuqta OCR: Accurate Arabic Document OCR with Faithful Tashkeel},
  author = {Salah AlHaismawi and Mohamed Saleh Tulib and Ahmed ElSayed Mohamed Ibrahim},
  year   = {2026},
  url    = {https://huggingface.co/SalahALHaismawi/Nuqta-OCR-4B-GGUF}
}
```
