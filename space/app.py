"""Nuqta OCR demo Space (Hugging Face ZeroGPU): read an Arabic page, photo, ID or PDF; benchmarks and examples."""
import base64
import json
import os
from pathlib import Path

import gradio as gr
import spaces

from nuqta import OCR
from nuqta.preprocess import load_image

from app_examples import GALLERY, MODES

HERE = Path(__file__).parent
A = HERE / "assets"
MODELS = {"4B · most accurate": os.environ.get("NUQTA_4B", "SalahALHaismawi/Nuqta-Arabic-OCR-4B"),
          "0.8B · fast": os.environ.get("NUQTA_08B", "SalahALHaismawi/Nuqta-Arabic-OCR-0.8B")}
# the examples' readings, precomputed with the 4B (precompute_examples.py): a click shows them at once, no GPU time
CACHED = json.loads((A / "example_outputs.json").read_text())
MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "5"))

LOGO = base64.b64encode((A / "nuqta_logo.png").read_bytes()).decode()

# models load once at start-up; ZeroGPU attaches a GPU inside @spaces.GPU calls
_OCR = {name: OCR(path, backend="transformers", device_map="cuda") for name, path in MODELS.items()}


def _pages(path: str):
    if path.lower().endswith(".pdf"):
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(path)
        return [doc[i].render(scale=200 / 72).to_pil().convert("RGB") for i in range(min(len(doc), MAX_PDF_PAGES))]
    return [load_image(path)]


def _view(text):
    """Rendered view: drop the model's image placeholders (logos, photos, stamps)."""
    return text.replace("<img>image here</img>", "").strip()


def _fields_or_notes(text, mode, notes):
    if mode == "id":
        from nuqta import read_fields

        return json.dumps(read_fields(text), ensure_ascii=False, indent=1, default=str)
    return "\n".join(notes)


@spaces.GPU(duration=120)
def run(image, pdf, mode_label, model_name):
    """Stream the reading of one image token by token; a PDF is read page by page with the library."""
    src = pdf or image
    if not src:
        yield "", "", ""
        return
    mode = MODES[mode_label]
    ocr = _OCR[model_name]
    md = mode in ("markdown", "id")
    if pdf:
        res = ocr.read_many(_pages(pdf), mode=mode)
        text = "\n\n".join(r.text for r in res)
        notes = ["A page was re-read at its native size."] if any(p.fallback for r in res for p in r.pages) else []
        yield text, _view(text) if md else "", _fields_or_notes(text, mode, notes)
        return
    from threading import Thread

    from transformers import TextIteratorStreamer

    from nuqta.preprocess import prepare
    from nuqta.text import PROMPTS, clean, looped, trim_loops

    be = ocr.backend
    msgs = [{"role": "user", "content": [{"type": "image", "image": prepare(load_image(src))},
                                         {"type": "text", "text": PROMPTS["markdown" if mode == "id" else mode]}]}]
    inputs = be.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                              return_tensors="pt", enable_thinking=False).to(be.model.device)
    streamer = TextIteratorStreamer(be.processor.tokenizer, skip_prompt=True, skip_special_tokens=True)
    Thread(target=be.model.generate, kwargs=dict(**inputs, streamer=streamer, max_new_tokens=8192, do_sample=False,
                                                 eos_token_id=be.eos, pad_token_id=be.eos[0])).start()
    text = ""
    for piece in streamer:
        text += piece
        yield clean(text), "", ""
    text = clean(text)
    notes = []
    if looped(text):
        text, notes = trim_loops(text), ["Some repetition was trimmed from the output."]
    yield text, _view(text) if md else "", _fields_or_notes(text, mode, notes)


def tab_for(mode_label):
    m = MODES[mode_label]
    return gr.Tabs(selected="fields" if m == "id" else "rendered" if m == "markdown" else "text")


def pick(evt: gr.SelectData):
    f, _, mode = GALLERY[evt.index]
    c = CACHED[f]
    return str(A / f), None, mode, c["text"], _view(c["rendered"]), c["extra"], tab_for(mode)


HEADER = """
<div class="hero">
  <div class="brand"><img src="data:image/png;base64,{logo}" alt="Nuqta"><h1>Nuqta OCR <span class="ar">نقطة</span></h1></div>
  <p class="lead">Open-weights Arabic OCR that <b>copies the tashkeel printed on the page</b> and almost
  never adds any. Books, official documents, tables, forms, IDs and passports, as text or Markdown.</p>
  <div class="stats">
    <div><b>#1</b><span>KITAB-Bench<br>CER 0.106</span></div>
    <div><b>#1</b><span>Misraj-DocOCR<br>MARS 82.8</span></div>
    <div><b>0.08</b><span>invented marks per<br>100 letters (0.8B)</span></div>
    <div><b>560 MB</b><span>0.8B on a phone<br>(4-bit GGUF)</span></div>
  </div>
  <div class="models">
    <a href="https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B"><span class="tag">Most accurate</span><b>Nuqta-Arabic-OCR 4B</b><span>#1 on KITAB &amp; Misraj · 16 GB GPU</span></a>
    <a href="https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-0.8B"><span class="tag">Best for its size</span><b>Nuqta-Arabic-OCR 0.8B</b><span>Beats Gemini on KITAB · 3 GB</span></a>
    <a href="https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-0.8B-GGUF"><span class="tag">Phones</span><b>0.8B GGUF</b><span>560 MB · offline · llama.cpp</span></a>
    <a href="https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B-GGUF"><span class="tag">Laptops</span><b>4B GGUF</b><span>2.9 GB · offline · llama.cpp</span></a>
  </div>
</div>
"""

BENCH = """
<div class="bench">
  <div class="bgrid">
    <div class="bcard">
      <h3>KITAB-Bench <span>OCR track · 13 datasets</span></h3>
      <p class="metric">Character error rate · lower is better</p>
      <table>
        <tr><th>Model</th><th>Size</th><th class="n">CER</th></tr>
        <tr class="us"><td>Nuqta-Arabic-OCR 4B</td><td>4.75B</td><td class="n best">0.106</td></tr>
        <tr class="us"><td>Nuqta-Arabic-OCR 0.8B</td><td>0.89B</td><td class="n">0.117</td></tr>
        <tr><td>Gemini-2.0-Flash</td><td>closed</td><td class="n">0.130</td></tr>
        <tr><td>AIN-7B</td><td>7B</td><td class="n">0.200</td></tr>
        <tr><td>GPT-4o</td><td>closed</td><td class="n">0.310</td></tr>
        <tr><td>Qwen-2.5-VL</td><td>7B</td><td class="n">0.492</td></tr>
        <tr><td>Tesseract</td><td>–</td><td class="n">0.540</td></tr>
        <tr><td>EasyOCR</td><td>–</td><td class="n">0.580</td></tr>
      </table>
    </div>
    <div class="bcard">
      <h3>Misraj-DocOCR <span>400 real document pages</span></h3>
      <p class="metric">MARS = (chrF + TEDS) / 2 · higher is better</p>
      <table>
        <tr><th>Model</th><th>Size</th><th class="n">chrF</th><th class="n">TEDS</th><th class="n">MARS</th></tr>
        <tr class="us"><td>Nuqta-Arabic-OCR 4B</td><td>4.75B</td><td class="n">89.4</td><td class="n best">76.1</td><td class="n best">82.8</td></tr>
        <tr><td>Baseer v2 <span class="hint">Misraj, Sept 2026</span></td><td>–</td><td class="n">88.9</td><td class="n">67</td><td class="n">77.8</td></tr>
        <tr class="us"><td>Nuqta-Arabic-OCR 0.8B</td><td>0.89B</td><td class="n">87.4</td><td class="n">66.8</td><td class="n">77.1</td></tr>
        <tr><td>Baseer <span class="hint">paper</span></td><td>3B</td><td class="n">87.8</td><td class="n">66</td><td class="n">76.9</td></tr>
        <tr><td>Gemini-2.5-Pro</td><td>closed</td><td class="n best">89.6</td><td class="n">52</td><td class="n">70.8</td></tr>
        <tr><td>Azure Doc. Intelligence</td><td>closed</td><td class="n">82.5</td><td class="n">42</td><td class="n">62.2</td></tr>
        <tr><td>dots.ocr</td><td>3B</td><td class="n">78.4</td><td class="n">40</td><td class="n">59.2</td></tr>
        <tr><td>GPT-5</td><td>closed</td><td class="n">61.6</td><td class="n">48</td><td class="n">54.8</td></tr>
      </table>
    </div>
  </div>
  <div class="bcard wide">
    <h3>Beyond the benchmarks</h3>
    <table>
      <tr><th></th><th class="n">4B</th><th class="n">0.8B</th></tr>
      <tr><td>Invented diacritics on undiacritized text <span class="hint">per 100 letters · lower is better</span></td><td class="n">0.16</td><td class="n best">0.08</td></tr>
      <tr><td>Table column order right <span class="hint">left-to-right / right-to-left tables</span></td><td class="n best">98% / 98%</td><td class="n">95% / 96%</td></tr>
      <tr><td>Real ID cards: fields correct <span class="hint">held out, no training overlap</span></td><td class="n best">85.7%</td><td class="n">79.2%</td></tr>
      <tr><td>Real passports: fields correct</td><td class="n best">87.2%</td><td class="n">84.9%</td></tr>
    </table>
  </div>
  <p class="bnote">Nuqta numbers: our runs, scored with KITAB-Bench's own scoring code (for Misraj-DocOCR, which published no code, with the Baseer paper's recipe on top of it; checked against Misraj's own published score for Qwen3-VL-8B, 52.5 vs 51.8 MARS), at the recommended input size
  (what this demo and the <code>nuqta-ocr</code> library do). Competitor numbers: published figures (KITAB-Bench authors; Misraj's <a href="https://arxiv.org/abs/2509.18174">Baseer paper</a> and <a href="https://misraj.ai/en/blogs/baseer-arabic-document-ocr-vlm-misraj">September 2026 results table</a>). Full results,
  confidence intervals, the "images as given" setting and a contamination disclosure are on the
  <a href="https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B">model cards</a>.</p>
</div>
"""

USAGE = """
### Python library

```bash
pip install "nuqta-ocr[vllm]"
```

```python
from nuqta import OCR

if __name__ == "__main__":                               # needed with vLLM
    ocr = OCR("nuqta-4b")                               # or "nuqta-0.8b"
    print(ocr.read("page.jpg").text)                     # as written
    print(ocr.read("scan.pdf", mode="markdown").text)    # headings, lists, HTML tables
    print(ocr.read("passport.jpg", mode="id").fields)    # MRZ fields + check digits
```

### Offline, on a phone or laptop

[Nuqta-Arabic-OCR-0.8B-GGUF](https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-0.8B-GGUF) runs with llama.cpp on Android,
iOS, Mac, Windows and Linux: 560 MB at 4-bit, about 1.6 GB of RAM, matching the full model on our spot checks.
[Nuqta-Arabic-OCR-4B-GGUF](https://huggingface.co/SalahALHaismawi/Nuqta-Arabic-OCR-4B-GGUF) for laptops and desktops.

### Why it is different

- **Faithful tashkeel by design:** every training page is labelled with exactly the diacritics printed on it.
- **A deeper attention stack:** built on Qwen3.5, with two extra full-attention layers added to the decoder.
- **Exact labels, not guesses:** born-digital documents, PDF text layers, official gazettes, real scans aligned to
  their source text, tables with HTML labels, IDs and passports, from 172 sources.
- **Reinforcement learning (0.8B)** against repetition loops, invented diacritics, wrong table structure and bad MRZ check
  digits; the 0.8B also learned tables from the 4B's readings of real documents.
- **Right-to-left tables:** column order follows how the table is drawn (98% right on mixed-direction tables, 4B).
- **Private by design:** open weights you run on your own servers or devices; your documents never leave your network.
"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;600&display=swap');
.bench {max-width: 1100px; margin: 8px auto 0;}
.bgrid {display: grid; grid-template-columns: 1fr 1.25fr; gap: 16px;}
.bcard {border: 1px solid var(--border-color-primary); border-radius: 16px; padding: 18px 20px; background: var(--background-fill-secondary);}
.bcard.wide {margin-top: 16px;}
.bcard h3 {margin: 0; font-size: 1.15em;} .bcard h3 span {font-weight: 400; opacity: .65; font-size: .85em; margin-left: 6px;}
.bcard .metric {margin: 2px 0 10px; font-size: .85em; opacity: .7;}
.bench table {width: 100%; border-collapse: collapse; font-size: .95em; border: none !important; box-shadow: none !important; outline: none !important; margin: 0 !important;}
.bench .table-wrap, .bench div:has(> table) {border: none !important; box-shadow: none !important;}
.bench th, .bench td {border: none !important; border-bottom: 1px solid var(--border-color-primary) !important; padding: 9px 10px; text-align: left; background: transparent;}
.bench tr {border: none !important;}
.bench tr:last-child td {border-bottom: none !important;}
.bench th {font-size: .8em; text-transform: uppercase; letter-spacing: .05em; opacity: .65; font-weight: 600;}
.bench .n {text-align: right; font-variant-numeric: tabular-nums;}
.bench tr.us td {background: #19b98a1a; font-weight: 600;}
.bench tr.us td:first-child {color: #19b98a; border-radius: 8px 0 0 8px;} .bench tr.us td:last-child {border-radius: 0 8px 8px 0;}
.bench .best {font-weight: 800; color: #19b98a;}
.bench .hint {display: block; font-size: .8em; opacity: .6; font-weight: 400;}
.bnote {font-size: .85em; opacity: .75; margin: 14px 4px 0;} .bnote a {color: #19b98a;}
@media (max-width: 860px) {.bgrid {grid-template-columns: 1fr;}}
.brand {display: flex; align-items: center; justify-content: center; gap: 14px;}
.brand img {height: 72px; border-radius: 14px;}
.brand h1 {margin: 0;}
.pick {font-weight: 600; margin: 4px 0 0;}
.credits {font-size: .82em; opacity: .7; margin-top: -6px;}
@media (max-width: 640px) {.tab-container button {padding-left: 10px !important; padding-right: 10px !important;}}
#examples, #examples .gallery-container, #examples .grid-wrap {height: auto !important; max-height: none !important; overflow: visible !important;}
#examples .caption-label {max-width: 92%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
@media (max-width: 640px) {#examples .grid-container {grid-template-columns: repeat(3, minmax(0, 1fr)) !important;}
  #examples .gallery-item, #examples .thumbnail-item {height: auto !important; aspect-ratio: 1;}}
.hero {text-align: center; padding: 8px 0 4px;}
.hero h1 {font-size: 2.4em; margin-bottom: 4px;}
.hero .ar {color: #19b98a;}
.hero .lead {max-width: 760px; margin: 0 auto 14px; font-size: 1.08em;}
.stats {display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin: 6px 0 10px;}
.stats div {border: 1px solid #19b98a55; border-radius: 12px; padding: 10px 16px; min-width: 140px;}
.stats b {display: block; font-size: 1.6em; color: #19b98a;}
.stats span {font-size: 0.85em; opacity: 0.85;}
.models {display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; max-width: 980px; margin: 4px auto 6px;}
.models a {display: flex; flex-direction: column; gap: 2px; text-align: left; text-decoration: none; color: inherit;
           border: 1px solid #19b98a40; border-radius: 12px; padding: 10px 14px; transition: border-color .15s;}
.models a:hover {border-color: #19b98a;}
.models .tag {font-size: .7em; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #19b98a;}
.models b {font-size: 1.02em;} .models span:last-child {font-size: .84em; opacity: .8;}
@media (max-width: 760px) {.models {grid-template-columns: 1fr 1fr;}}
.rtl textarea, .rtl .prose {direction: rtl; text-align: right; font-family: 'Noto Naskh Arabic', serif; font-size: 1.15em; line-height: 1.9;}
footer {display: none !important;}
"""

with gr.Blocks(title="Nuqta OCR: Arabic OCR with faithful tashkeel", css=CSS, delete_cache=(1800, 3600),
               theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="slate",
                                    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"])) as demo:
    gr.HTML(HEADER.replace("{logo}", LOGO))
    with gr.Tabs():
        with gr.Tab("Try it"):
            gr.Markdown("Tap an example to see the 4B's reading, or upload your own page below.", elem_classes="pick")
            examples = gr.Gallery([(str(A / f), cap) for f, cap, _ in GALLERY], columns=6, height="auto",
                                  allow_preview=False, show_label=False, object_fit="cover", elem_id="examples")
            gr.Markdown("Book pages: Hindawi (CC BY 4.0). Table: Misraj-DocOCR (Apache-2.0). Passports, invoice, "
                        "receipt, form and diagram are made up: no real person's data.", elem_classes="credits")
            with gr.Row(equal_height=False):
                with gr.Column(scale=5):
                    image = gr.Image(label="Page, photo, ID or passport", type="filepath", height=520,
                                     sources=["upload", "clipboard", "webcam"])
                    with gr.Accordion("Have a PDF?", open=False):
                        pdf = gr.File(label=f"PDF (first {MAX_PDF_PAGES} pages)", file_types=[".pdf"], type="filepath")
                    with gr.Row():
                        mode = gr.Dropdown(list(MODES), value=list(MODES)[0], label="Output", scale=3)
                        model = gr.Dropdown(list(MODELS), value=list(MODELS)[0], label="Model", scale=2)
                    go = gr.Button("Read", variant="primary", size="lg")
                    gr.Markdown("Uploads are only used for the reading and are deleted from the server within an hour.")
                with gr.Column(scale=6):
                    with gr.Tabs() as out_tabs:
                        with gr.Tab("Text", id="text"):
                            out = gr.Textbox(show_label=False, lines=22, max_lines=40, elem_classes="rtl",
                                             show_copy_button=True, placeholder="ستظهر القراءة هنا")
                        with gr.Tab("Rendered", id="rendered"):
                            rendered = gr.Markdown(elem_classes="rtl")
                        with gr.Tab("ID fields", id="fields"):
                            extra = gr.Code(language="json", show_label=False)
            examples.select(pick, None, [image, pdf, mode, out, rendered, extra, out_tabs])
            go.click(lambda: gr.Tabs(selected="text"), None, out_tabs).then(run, [image, pdf, mode, model], [out, rendered, extra]).then(
                tab_for, mode, out_tabs)
        with gr.Tab("Benchmarks"):
            gr.Image(str(A / "results_chart.png"), show_label=False, interactive=False, show_download_button=False,
                     show_fullscreen_button=False, container=False)
            gr.HTML(BENCH)
        with gr.Tab("Examples"):
            gr.Markdown("Real outputs of Nuqta-Arabic-OCR 4B. Sources: a Hindawi book page (CC BY 4.0), a Misraj-DocOCR page "
                        "(Apache-2.0), and a synthetic passport and diagram we generated (no real person's document).")
            for k in ("book", "table", "id", "diagram"):
                gr.Image(str(A / f"example_{k}.png"), show_label=False, interactive=False, container=False,
                         show_download_button=False)
        with gr.Tab("Code"):
            gr.Markdown(USAGE)

if __name__ == "__main__":
    demo.queue(max_size=20).launch(allowed_paths=[str(A)])
