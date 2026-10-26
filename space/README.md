---
title: Nuqta Arabic OCR
emoji: 📜
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
pinned: true
license: apache-2.0
short_description: "Arabic OCR with faithful tashkeel: #1 on KITAB & Misraj"
models:
- SalahALHaismawi/Nuqta-Arabic-OCR-4B
- SalahALHaismawi/Nuqta-Arabic-OCR-0.8B
tags:
- ocr
- arabic
- arabic-ocr
- tashkeel
- document-ai
---

Demo of [Nuqta OCR](https://huggingface.co/collections/SalahALHaismawi/nuqta-ocr-6ad4af255195b706ac93d1d4): read
Arabic pages, photos, tables, IDs and PDFs with tashkeel exactly as printed. Hardware: ZeroGPU. Environment
variables: `NUQTA_4B`, `NUQTA_08B` (model ids), `MAX_PDF_PAGES` (default 5).
