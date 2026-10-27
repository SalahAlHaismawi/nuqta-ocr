"""Build the Nuqta OCR website into docs/ (served by GitHub Pages). Run: python site/build.py"""
import html
import json
import pathlib
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
BASE = "https://salahalhaismawi.github.io/nuqta-ocr/"
TODAY = date.today().isoformat()

HF = "https://huggingface.co/SalahALHaismawi/"
DEMO = "https://huggingface.co/spaces/SalahALHaismawi/Nuqta-Arabic-OCR"
GH = "https://github.com/SalahAlHaismawi/nuqta-ocr"
PYPI = "https://pypi.org/project/nuqta-ocr/"
KITAB = "https://github.com/mbzuai-oryx/KITAB-Bench"
MISRAJ = "https://huggingface.co/datasets/Misraj/Misraj-DocOCR"
MISRAJ_TABLE = "https://misraj.ai/en/blogs/baseer-arabic-document-ocr-vlm-misraj"
AUTHORS = ["Salah AlHaismawi", "Mohamed Saleh Tulib", "Ahmed ElSayed Mohamed Ibrahim"]

CSS = (ROOT / "site" / "style.css").read_text()

FONTS = ("https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500&family=IBM+Plex+Mono&"
         "family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Sans+Arabic:wght@400;600&family=Amiri:wght@400;700&display=swap")

NAV_EN = [("Benchmarks", "best-arabic-ocr/"), ("Guides", "guides/"), ("Demo", DEMO), ("GitHub", GH), ("العربية", "ar/")]
NAV_AR = [("المقارنة", "best-arabic-ocr/"), ("الأدلة", "guides/"), ("التجربة", DEMO), ("GitHub", GH), ("English", "")]

SOFTWARE = {
    "@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Nuqta OCR",
    "alternateName": ["Nuqta Arabic OCR", "نقطة", "Nuqta-Arabic-OCR"],
    "applicationCategory": "DeveloperApplication", "operatingSystem": "Linux, macOS, Windows, Android, iOS",
    "description": "Open-source Arabic OCR models (4B and 0.8B) and Python library. First on KITAB-Bench (CER 0.106) "
                   "and Misraj-DocOCR (MARS 82.8) among published results. Copies printed tashkeel, reads tables, IDs and passports.",
    "url": BASE, "downloadUrl": PYPI, "softwareVersion": "0.1.1", "license": "https://www.apache.org/licenses/LICENSE-2.0",
    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    "author": [{"@type": "Person", "name": a} for a in AUTHORS],
    "sameAs": [GH, PYPI, DEMO, HF + "Nuqta-Arabic-OCR-4B", HF + "Nuqta-Arabic-OCR-0.8B"],
}


def rel(depth: int, href: str) -> str:
    if href.startswith("http"):
        return href
    return "../" * depth + href


def page(path: str, title: str, desc: str, body: str, *, lang="en", ld=(), alt=None, kind="WebPage"):
    depth = path.count("/")
    rtl = lang == "ar"
    nav = NAV_AR if rtl else NAV_EN
    url = BASE + path
    links = "".join(f'<a href="{rel(depth, h)}"{" hreflang=" + chr(34) + ("en" if rtl else "ar") + chr(34) if h in ("", "ar/") else ""}>{t}</a>' for t, h in nav)
    alts = ""
    if alt:
        en, ar = (alt, path) if rtl else (path, alt)
        alts = (f'<link rel="alternate" hreflang="en" href="{BASE + en}">'
                f'<link rel="alternate" hreflang="ar" href="{BASE + ar}">'
                f'<link rel="alternate" hreflang="x-default" href="{BASE + en}">')
    lds = [{"@context": "https://schema.org", "@type": kind, "name": title, "description": desc, "url": url,
            "inLanguage": lang, "dateModified": TODAY,
            "author": [{"@type": "Person", "name": a} for a in AUTHORS]}] + list(ld)
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)
    foot = ("نقطة · نماذج مفتوحة المصدر للتعرف الضوئي على النص العربي · Apache-2.0" if rtl else
            "Nuqta OCR · open-source Arabic OCR · Apache-2.0")
    doc = f"""<!doctype html>
<html lang="{lang}"{' dir="rtl"' if rtl else ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">{alts}
<link rel="icon" href="{rel(depth, 'img/icon.png')}">
<meta property="og:type" content="website"><meta property="og:url" content="{url}">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="{BASE}img/og.png"><meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{rel(depth, 'style.css')}">
{ld_html}
</head>
<body{' dir="rtl"' if rtl else ''}>
<header class="top"><div class="wrap">
<a class="brand" href="{rel(depth, 'ar/' if rtl else '')}">{'نقطة' if rtl else 'Nuqta OCR<span class="ar">نقطة</span>'}</a>
<nav>{links}</nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">{foot} · <a href="{GH}">GitHub</a> · <a href="{HF}Nuqta-Arabic-OCR-4B">Hugging Face</a> · <a href="{PYPI}">PyPI</a><br>
{' · '.join(AUTHORS)} · {'آخر تحديث' if rtl else 'Updated'} {TODAY}</div></footer>
</body>
</html>
"""
    f = OUT / path / "index.html" if path else OUT / "index.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(doc)
    return path


def faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]}


def faq_html(qas):
    return "".join(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>" for q, a in qas)


def table(head, rows, us=()):
    th = "".join(f"<th>{h}</th>" for h in head)
    trs = ""
    for r in rows:
        cls = ' class="us"' if r[0] in us else ""
        trs += f"<tr{cls}>" + "".join(f'<td{" class=n" if i else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>"
    return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


KITAB_ROWS = [
    ("Nuqta-Arabic-OCR 4B", "4.75B, open", "0.106"),
    ("Nuqta-Arabic-OCR 0.8B", "0.89B, open", "0.117"),
    ("Gemini-2.0-Flash", "closed", "0.130"),
    ("AIN-7B", "7B, open", "0.200"),
    ("GPT-4o", "closed", "0.310"),
    ("Qwen-2.5-VL", "7B, open", "0.492"),
    ("Tesseract", "open", "0.540"),
    ("EasyOCR", "open", "0.580"),
]
MISRAJ_ROWS = [
    ("Nuqta-Arabic-OCR 4B", "4.75B, open", "82.8", "76.1", "0.121"),
    ("Baseer v2 (Misraj)", "no public weights", "77.8", "67", "0.12"),
    ("Nuqta-Arabic-OCR 0.8B", "0.89B, open", "77.1", "66.8", "0.130"),
    ("Baseer (paper)", "3B", "76.9", "66", "0.53"),
    ("Gemini-2.5-Pro", "closed", "70.8", "52", "0.31"),
    ("Azure Document Intelligence", "closed", "62.2", "42", "0.27"),
    ("dots.ocr", "3B, open", "59.2", "40", "0.40"),
    ("GPT-5", "closed", "54.8", "48", "0.62"),
    ("Mistral OCR", "closed", "44.4", "17", "0.42"),
    ("QARI", "2B, open", "42.8", "21", "0.64"),
]
US = ("Nuqta-Arabic-OCR 4B", "Nuqta-Arabic-OCR 0.8B")

INSTALL = """<pre><code>pip install "nuqta-ocr[vllm]"   # Linux + NVIDIA GPU, fastest
pip install "nuqta-ocr[fast]"   # transformers with fast kernels
pip install nuqta-ocr           # transformers only</code></pre>"""

QUICK = """<pre><code>from nuqta import OCR

if __name__ == "__main__":
    ocr = OCR("nuqta-4b")          # or "nuqta-0.8b" for small GPUs
    print(ocr.read("page.jpg").text)                     # tashkeel only where printed
    print(ocr.read("scan.pdf", mode="markdown").text)    # headings, lists, HTML tables
    print(ocr.read("passport.jpg", mode="id").fields)    # MRZ fields with check digits</code></pre>"""

# ---------------------------------------------------------------- home (en)
HOME_FAQ = [
    ("What is the best Arabic OCR model?",
     "On the two public Arabic OCR benchmarks, Nuqta-Arabic-OCR 4B has the best published results: character error rate 0.106 on "
     "KITAB-Bench (Gemini-2.0-Flash 0.13, GPT-4o 0.31) and MARS 82.8 on Misraj-DocOCR (Baseer v2 77.8, Gemini-2.5-Pro 70.8). "
     "It is open source under Apache-2.0. The smaller Nuqta-Arabic-OCR 0.8B is second on KITAB-Bench and runs on a phone."),
    ("What is the best open-source Arabic OCR?",
     "Nuqta OCR. Both models are open weights under Apache-2.0, and both score better on KITAB-Bench than every other published "
     "result, open or closed. Tesseract and EasyOCR score 0.54 and 0.58 character error rate on the same benchmark."),
    ("Does Nuqta OCR keep tashkeel (Arabic diacritics)?",
     "Yes. It copies the diacritics printed on the page and almost never adds any: 0.08 to 0.16 invented marks per 100 letters "
     "on undiacritized text. Fully vocalized text such as Quran or children's books keeps its marks."),
    ("Can it convert Arabic PDFs to text?",
     "Yes. The nuqta-ocr Python library renders every PDF page and returns plain text or Markdown with HTML tables, in reading order."),
    ("Does it read Arabic handwriting?",
     "It reads handwritten lines and paragraphs (KHATT character error rate 0.07 to 0.11), but it is built for printed documents, "
     "where it is most accurate."),
    ("Can it run without a GPU?",
     "Yes. The GGUF builds run on CPU with llama.cpp, LM Studio and similar apps, and the 0.8B runs offline on Android and iPhone. "
     "On a laptop CPU a dense book page takes about a minute; on a 24 GB GPU about 3 seconds."),
    ("Is Nuqta OCR free for commercial use?",
     "Yes. The models and the library are released under Apache-2.0."),
    ("Which languages does it read?",
     "Arabic, and English mixed into Arabic documents (for example bilingual tables and IDs)."),
]

_ex = json.loads((ROOT / "space" / "assets" / "example_outputs.json").read_text())["1_book.png"]["text"]
_ex = _ex[:_ex.index("قَرِيبَةٍ؛") + len("قَرِيبَةٍ؛")] + " …"
_ex = html.escape(_ex).replace("ثرثار", "<mark>ثرثار</mark>").replace("شادو", "<mark>شادو</mark>")


def proof(depth, tag, caption):
    return (f'<figure><div class="proof"><img src="{rel(depth, "img/sample_page.png")}" width="900" height="307" '
            f'alt="Arabic book page with tashkeel"><span class="tag">{tag}</span><div class="out">{_ex}</div></div>'
            f'<figcaption>{caption}</figcaption></figure>')


home_body = f"""
<div class="hero"><div>
<h1>Nuqta: open-source Arabic OCR</h1>
<p class="lead">Nuqta turns Arabic scans, photos and PDFs into text you can copy and search. It writes the tashkeel that is
printed on the page and adds none of its own. Its two models have the best published scores on KITAB-Bench and
Misraj-DocOCR, and the smaller one runs on a phone.</p>
<div class="go"><a class="main" href="{DEMO}">Try it in the browser</a><a href="best-arabic-ocr/">Benchmarks</a>
<a href="{GH}">GitHub</a></div>
</div>
{proof(0, "Nuqta 4B output, unedited", "A page from a Hindawi children's book (CC BY 4.0). The names ثرثار and شادو are printed without marks, and the output leaves them that way.")}
</div>
<div class="nums">
<div><b>0.106</b><span>character error rate on KITAB-Bench. Next best: Gemini-2.0-Flash, 0.13</span></div>
<div><b>82.8</b><span>MARS on Misraj-DocOCR. Next best: Baseer v2, 77.8</span></div>
<div><b>1.6 GB</b><span>of memory runs the 0.8B offline on a phone</span></div>
</div>

<h2>What it reads</h2>
<ul class="plain">
<li><b>Books and scanned documents</b><span>Printed pages and old books, in reading order.</span></li>
<li><b>PDFs</b><span>Every page, with headings, lists and tables kept as Markdown and HTML.</span></li>
<li><b>Tashkeel</b><span>Vocalized text keeps its marks. Unmarked text stays unmarked.</span></li>
<li><b>Tables</b><span>Arabic and English tables, with columns in the order they are drawn.</span></li>
<li><b>IDs and passports</b><span>MRZ fields with their ICAO check digits. A failed check is flagged, not guessed.</span></li>
<li><b>On your own hardware</b><span>A GPU server, a laptop, Android or iPhone. Documents stay with you.</span></li>
</ul>

<h2>Two models</h2>
{table(["Model", "Size", "KITAB-Bench CER ↓", "Misraj MARS ↑", "Runs on"],
       [(f'<a href="{HF}Nuqta-Arabic-OCR-4B">Nuqta-Arabic-OCR 4B</a>', "4.75B", "0.106", "82.8", "16 GB GPU, or laptop (GGUF)"),
        (f'<a href="{HF}Nuqta-Arabic-OCR-0.8B">Nuqta-Arabic-OCR 0.8B</a>', "0.89B", "0.117", "77.1", "any GPU, CPU, phone (GGUF)")])}
<p class="note">GGUF builds for llama.cpp, LM Studio and other local apps:
<a href="{HF}Nuqta-Arabic-OCR-4B-GGUF">4B GGUF</a> (2.9 GB) · <a href="{HF}Nuqta-Arabic-OCR-0.8B-GGUF">0.8B GGUF</a> (560 MB).
Full comparison with Gemini, GPT, Azure, Mistral, Baseer, Tesseract and others: <a href="best-arabic-ocr/">Arabic OCR benchmarks</a>.</p>

<h2>Use it in Python</h2>
{INSTALL}
{QUICK}
<p>Command line: <code>nuqta read scan.pdf --mode markdown</code>. More in the <a href="guides/">guides</a>.</p>

<h2>Questions</h2>
{faq_html(HOME_FAQ)}

<h2>Cite</h2>
<pre><code>@misc{{nuqta_ocr_2026,
  title  = {{Nuqta OCR: Accurate Arabic Document OCR with Faithful Tashkeel}},
  author = {{Salah AlHaismawi and Mohamed Saleh Tulib and Ahmed ElSayed Mohamed Ibrahim}},
  year   = {{2026}},
  url    = {{{GH}}}
}}</code></pre>
"""

# ---------------------------------------------------------------- comparison
CMP_FAQ = [
    ("Which Arabic OCR is the most accurate in 2026?",
     "Nuqta-Arabic-OCR 4B has the best published score on both public Arabic OCR benchmarks: KITAB-Bench character error rate 0.106 "
     "and Misraj-DocOCR MARS 82.8."),
    ("Is Tesseract good for Arabic?",
     "Tesseract works for clean printed Arabic but misses many characters on real documents: 0.54 character error rate on KITAB-Bench, "
     "against 0.106 for Nuqta-Arabic-OCR 4B. It also drops or mangles tashkeel."),
    ("Is Gemini or GPT better than open models for Arabic OCR?",
     "Not on these benchmarks. Gemini-2.0-Flash scores 0.13 and GPT-4o 0.31 on KITAB-Bench, and Gemini-2.5-Pro 70.8 and GPT-5 54.8 "
     "MARS on Misraj-DocOCR, all behind Nuqta's open models."),
    ("What is the best Arabic OCR for tables?",
     "On Misraj-DocOCR tables (TEDS), Nuqta-Arabic-OCR 4B scores 76.1, ahead of Baseer v2 (67), Gemini-2.5-Pro (52) and Azure (42)."),
]

cmp_body = f"""
<p class="kicker">Updated {TODAY}</p>
<h1>Best Arabic OCR models in 2026, compared</h1>
<p class="lead">Scores from the two public Arabic OCR benchmarks, KITAB-Bench and Misraj-DocOCR, for open models, cloud APIs and
classic OCR engines. Other systems' numbers are the ones published by the benchmark authors.</p>

<h2>Summary</h2>
<ul>
<li><b>Most accurate overall:</b> Nuqta-Arabic-OCR 4B (open, Apache-2.0). First on both benchmarks.</li>
<li><b>Best small model:</b> Nuqta-Arabic-OCR 0.8B. Second on KITAB-Bench, ahead of Gemini-2.0-Flash and GPT-4o, and runs on a phone.</li>
<li><b>Lowest character error on Misraj-DocOCR:</b> Baseer v2 (0.12) and Nuqta 4B (0.121) are effectively tied; Baseer v2 has no public weights.</li>
<li><b>Classic engines:</b> Tesseract (0.54) and EasyOCR (0.58) miss about half of the characters on KITAB-Bench.</li>
</ul>

<h2>KITAB-Bench: 13 Arabic OCR datasets</h2>
<p>3,760 images: book pages, scanned lines, handwriting, manuscripts, slides, scene text and fonts. Character error rate, lower is better.</p>
{table(["Model", "Weights", "CER ↓"], KITAB_ROWS, US)}
<p class="note">Nuqta at its recommended input size (small page renders are enlarged to the training size). With every image sent
unchanged: 4B 0.111, 0.8B 0.132. 234 test images also appear in public datasets used for training; without them the 4B scores 0.113.
Source: <a href="{KITAB}">KITAB-Bench</a> and the Nuqta model cards.</p>

<h2>Misraj-DocOCR: 400 real Arabic document pages</h2>
<p>Pages converted to Markdown. MARS combines text and table accuracy, TEDS scores tables; higher is better. CER, lower is better.</p>
{table(["Model", "Weights", "MARS ↑", "TEDS ↑", "CER ↓"], MISRAJ_ROWS, US)}
<p class="note">Other systems from the Baseer paper and <a href="{MISRAJ_TABLE}">Misraj's September 2026 results table</a>.
Our scorer reproduces Misraj's published Qwen3-VL-8B score within a point, and our predictions are public in
<a href="{GH}/tree/main/benchmarks">the benchmarks folder</a> for anyone to re-score. Dataset: <a href="{MISRAJ}">Misraj-DocOCR</a>.</p>

<h2>How to choose</h2>
<ul class="plain">
<li><b>Highest accuracy, own GPU</b><span><a href="{HF}Nuqta-Arabic-OCR-4B">Nuqta-Arabic-OCR 4B</a> on a 16–24 GB GPU.</span></li>
<li><b>Small GPU, CPU or phone</b><span><a href="{HF}Nuqta-Arabic-OCR-0.8B">Nuqta-Arabic-OCR 0.8B</a>, or its 560 MB GGUF build.</span></li>
<li><b>Coming from Tesseract</b><span>Same one-call use from Python. <a href="../guides/tesseract-arabic-alternative/">Switching guide</a>.</span></li>
</ul>

<h2>Questions</h2>
{faq_html(CMP_FAQ)}
"""

# ---------------------------------------------------------------- guides
GUIDES = []

def guide(slug, title, desc, body, faq=()):
    GUIDES.append((slug, title, desc))
    full = f'<p class="kicker"><a href="../">Guides</a></p><h1>{html.escape(title)}</h1><p class="lead">{html.escape(desc)}</p>{body}'
    if faq:
        full += "<h2>Questions</h2>" + faq_html(faq)
    page(f"guides/{slug}/", title + " | Nuqta OCR", desc, full, ld=[faq_ld(faq)] if faq else [], kind="TechArticle")


guide("arabic-pdf-to-text", "Convert Arabic PDFs to text in Python",
      "Extract Arabic text from scanned or image-only PDFs, with tashkeel and tables, using the open-source Nuqta OCR library.",
      f"""
<h2>1. Install</h2>
{INSTALL}
<p>vLLM is the fastest backend (about 3 seconds per page for the 0.8B on a 24 GB GPU). Without a GPU, see
<a href="../run-arabic-ocr-offline/">running offline on CPU</a>.</p>
<h2>2. Read the PDF</h2>
<pre><code>from nuqta import OCR

if __name__ == "__main__":
    ocr = OCR("nuqta-4b")                                 # or "nuqta-0.8b"
    result = ocr.read("contract.pdf", mode="markdown")    # every page, rendered at 200 dpi
    for i, page in enumerate(result.pages, 1):
        print(f"--- page {{i}} ---")
        print(page.text)
    open("contract.md", "w", encoding="utf-8").write(result.text)</code></pre>
<p><code>mode="markdown"</code> keeps headings, lists and tables (as HTML). Use the default <code>as-written</code> mode for plain
text, or <code>bare</code> to remove all tashkeel.</p>
<h2>3. Many files at once</h2>
<pre><code>results = ocr.read_many(["a.pdf", "b.pdf", "scan.jpg"], mode="markdown")   # batched on the GPU</code></pre>
<h2>Command line</h2>
<pre><code>nuqta read contract.pdf --mode markdown > contract.md</code></pre>
<h2>Why not pdftotext?</h2>
<p>Text extraction tools such as pdftotext or PyMuPDF only work when the PDF already contains a text layer. Scanned PDFs are images,
and many Arabic PDFs have a broken text layer with letters in the wrong order or in presentation forms. OCR reads what is printed.</p>
""", [("How do I extract Arabic text from a scanned PDF?",
       "Use an OCR model, because a scanned PDF contains images, not text. With the open-source nuqta-ocr library: "
       "pip install nuqta-ocr, then OCR('nuqta-4b').read('file.pdf').text."),
      ("Why is Arabic text from my PDF reversed or broken?",
       "The PDF's text layer stores Arabic in visual order or as presentation-form glyphs. OCR the rendered page instead of copying the text layer.")])

guide("tesseract-arabic-alternative", "A more accurate alternative to Tesseract for Arabic",
      "Tesseract misses about half of the characters on the KITAB-Bench Arabic benchmark. Nuqta OCR cuts the error rate five-fold and keeps tashkeel.",
      f"""
<h2>The numbers</h2>
{table(["Engine", "KITAB-Bench CER ↓"], [("Nuqta-Arabic-OCR 4B", "0.106"), ("Nuqta-Arabic-OCR 0.8B", "0.117"), ("Tesseract", "0.540"), ("EasyOCR", "0.580")], US)}
<p>Tesseract was built for line-by-line printed text. Arabic's joined letters, dots and diacritics, mixed-direction tables
and low-resolution scans are where it fails. Nuqta is a vision-language model trained on Arabic documents.</p>
<h2>Switching</h2>
<pre><code># before
import pytesseract
from PIL import Image
text = pytesseract.image_to_string(Image.open("page.png"), lang="ara")

# after
from nuqta import OCR

if __name__ == "__main__":       # needed with the vLLM backend
    ocr = OCR("nuqta-0.8b")
    text = ocr.read("page.png").text</code></pre>
<p>Nuqta needs more compute than Tesseract. The 0.8B runs on any small GPU, and on CPU through its GGUF build
(<a href="../run-arabic-ocr-offline/">offline guide</a>).</p>
""", [("Is Tesseract good for Arabic OCR?",
       "For clean printed lines it works, but on the KITAB-Bench Arabic benchmark it has a 0.54 character error rate, against 0.106 for Nuqta-Arabic-OCR 4B."),
      ("What is the best free Arabic OCR?",
       "Nuqta OCR is free and open source (Apache-2.0) and has the best published scores on KITAB-Bench and Misraj-DocOCR.")])

guide("arabic-ocr-with-tashkeel", "Arabic OCR that keeps tashkeel (diacritics)",
      "Most OCR drops Arabic diacritics or invents them. Nuqta copies the tashkeel printed on the page and almost never adds any.",
      f"""
<p class="ar-text" dir="rtl">عِلْم · عَلَم · عُلِمَ</p>
<p>The same letters can be different words depending on their marks. A model that guesses marks from context changes the text;
a model that drops them loses meaning in vocalized books, poetry, religious texts and children's books.</p>
<h2>How Nuqta handles marks</h2>
<ul>
<li>Vocalized pages keep their marks: mark F1 0.997 on fully vocalized text.</li>
<li>Unvocalized pages stay unvocalized: 0.08 (0.8B) to 0.16 (4B) invented marks per 100 letters.</li>
<li>Partially marked names and words keep exactly the marks that are printed.</li>
</ul>
<h2>Choose the output</h2>
<pre><code>ocr.read("page.jpg").text                # as written: marks only where printed
ocr.read("page.jpg", mode="bare").text   # no marks at all, for search and indexing</code></pre>
""", [("Which Arabic OCR supports diacritics?",
       "Nuqta OCR reads tashkeel exactly as printed, with 0.997 mark F1 on vocalized text and almost no invented marks on plain text.")])

guide("arabic-passport-id-ocr", "Read Arabic ID cards and passports with OCR",
      "Extract MRZ fields with ICAO check digits from passports, visas and ID cards, and read Arabic ID text, on your own servers.",
      f"""
<pre><code>from nuqta import OCR

if __name__ == "__main__":
    ocr = OCR("nuqta-4b")
    r = ocr.read("passport.jpg", mode="id")
    print(r.fields["mrz"])   # format, issuer, surname, given_names, number, birth, expiry, check results</code></pre>
<p>Each MRZ field is checked against its ICAO check digit. A failed check is reported, never silently corrected, so the field can go
to a person for review. Egyptian national ID numbers are decoded and cross-checked against the printed birth date and sex.</p>
<h2>Accuracy on real documents</h2>
<p>On held-out real documents, the 4B reads 85.7% of ID-card fields and 87.2% of passport fields correctly. Documents never leave
your hardware, which matters for KYC and privacy rules.</p>
""", [("Can I do passport OCR on-premises?",
       "Yes. Nuqta OCR runs on your own GPU or CPU, so passport and ID images never leave your network.")])

guide("run-arabic-ocr-offline", "Run Arabic OCR offline on CPU, laptop or phone",
      "Use the GGUF builds of Nuqta OCR with llama.cpp, LM Studio and similar apps, or the Android and iPhone apps.",
      f"""
<h2>Files</h2>
{table(["Build", "Size", "RAM", "For"],
       [(f'<a href="{HF}Nuqta-Arabic-OCR-0.8B-GGUF">0.8B Q4_K_M</a>', "560 MB", "about 1.6 GB", "phones, any laptop"),
        (f'<a href="{HF}Nuqta-Arabic-OCR-4B-GGUF">4B Q4_K_M</a>', "2.9 GB", "about 6 GB", "laptops and desktops")])}
<p>4-bit builds score the same as full precision on our tests.</p>
<h2>llama.cpp</h2>
<pre><code>llama-mtmd-cli -m nuqta-ocr-0.8b-Q4_K_M.gguf --mmproj nuqta-ocr-0.8b-mmproj-f16.gguf \\
  --image page.png -c 8192 --image-max-tokens 4096 --temp 0 -t 8 \\
  -p "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) that are visible in the image."</code></pre>
<h2>Speed</h2>
<p>On a laptop CPU (Intel Core Ultra 9, 8 threads) a dense book page takes about a minute with the 0.8B; short pages, receipts and IDs
are faster. On a 24 GB GPU the same page takes about 3 seconds. Use about 8 fast cores: more threads do not help.</p>
<h2>Phones</h2>
<p>The <a href="{GH}/tree/main/apps">Android and iPhone apps</a> run the 0.8B on the device and show the first words in about 2 seconds.</p>
""")

guides_body = '<h1>Arabic OCR guides</h1><p class="lead">How to use Nuqta OCR for common Arabic OCR jobs.</p><ul class="plain">' + "".join(
    f'<li><b><a href="{s}/">{html.escape(t)}</a></b><span>{html.escape(d)}</span></li>' for s, t, d in GUIDES) + "</ul>"

# ---------------------------------------------------------------- arabic home
AR_FAQ = [
    ("ما أفضل نموذج لاستخراج النص العربي من الصور؟",
     "بحسب النتائج المنشورة في الاختبارين العامّين لقراءة النص العربي، يتصدر نموذج Nuqta-Arabic-OCR 4B: نسبة الخطأ في الحروف 0.106 في "
     "اختبار KITAB-Bench، و82.8 في اختبار Misraj-DocOCR، متقدمًا على Gemini وGPT وBaseer. والنموذج مفتوح المصدر برخصة Apache-2.0."),
    ("هل يحتفظ بالتشكيل؟",
     "نعم، يكتب الحركات المطبوعة في الصفحة كما هي، ونادرًا ما يضيف حركة غير موجودة فيها."),
    ("كيف أستخرج النص من ملف PDF عربي؟",
     "ثبّت المكتبة بالأمر pip install nuqta-ocr، ثم استدعِ OCR('nuqta-4b').read('file.pdf').text. ويمكنك أيضًا تجربته في المتصفح دون تثبيت أي شيء."),
    ("هل يعمل دون إنترنت؟",
     "نعم، يعمل على خوادمك أو حاسوبك أو هاتفك دون اتصال، فتبقى مستنداتك عندك."),
    ("هل هو مجاني؟", "نعم، النماذج والمكتبة مجانية ومفتوحة المصدر، ويمكن استخدامها في المشاريع التجارية."),
]

ar_body = f"""
<div class="hero"><div>
<h1>نقطة: قراءة النص العربي من الصور وملفات PDF</h1>
<p class="lead">نقطة نموذج مفتوح المصدر يستخرج النص العربي من صور الصفحات والمستندات الممسوحة وملفات PDF، فتحصل على نص
يمكنك نسخه والبحث فيه. ويكتب التشكيل كما ورد في الصفحة، ولا يضيف حركات من عنده. وقد حقق نموذجاه أعلى النتائج المنشورة
في اختباري <bdi>KITAB-Bench</bdi> و<bdi>Misraj-DocOCR</bdi>، ويعمل الصغير منهما على الهاتف دون إنترنت.</p>
<div class="go"><a class="main" href="{DEMO}">جرّبه في المتصفح</a><a href="../best-arabic-ocr/">المقارنة</a><a href="{GH}">GitHub</a></div>
</div>
{proof(1, "ناتج نموذج نقطة 4B كما هو، دون تعديل", "صفحة من كتاب أطفال نشرته مؤسسة هنداوي (برخصة CC BY 4.0). الاسمان «ثرثار» و«شادو» غير مشكولين في الكتاب، وبقيا كذلك في الناتج.")}
</div>
<div class="nums">
<div><b dir="ltr">0.106</b><span>نسبة الخطأ في الحروف في اختبار <bdi>KITAB-Bench</bdi>، وأقرب منافس 0.13</span></div>
<div><b dir="ltr">82.8</b><span>النتيجة في اختبار <bdi>Misraj-DocOCR</bdi>، وأقرب منافس 77.8</span></div>
<div><b dir="ltr">1.6 GB</b><span>من الذاكرة تكفي لتشغيل النموذج الصغير على الهاتف</span></div>
</div>
<h2>ما يقرؤه نقطة</h2>
<ul class="plain">
<li><b>الكتب والمستندات الممسوحة</b><span>يقرأ الصفحة بترتيبها الصحيح، من الكتب المطبوعة إلى الوثائق القديمة.</span></li>
<li><b>ملفات PDF</b><span>يقرأ صفحات الملف كلها، ويحتفظ بالعناوين والقوائم والجداول.</span></li>
<li><b>التشكيل</b><span>النص المشكول يبقى مشكولًا، وغير المشكول يبقى بلا حركات.</span></li>
<li><b>الجداول</b><span>العربية والإنجليزية، بترتيب أعمدتها كما في الأصل.</span></li>
<li><b>الهويات وجوازات السفر</b><span>يقرأ منطقة MRZ ويتحقق من أرقام التدقيق فيها.</span></li>
<li><b>على جهازك</b><span>يعمل على خوادمك أو حاسوبك أو هاتفك، فلا تغادر مستنداتك أجهزتك.</span></li>
</ul>
<h2>طريقة الاستخدام</h2>
{INSTALL}
{QUICK}
<h2>أسئلة شائعة</h2>
{faq_html(AR_FAQ)}
"""

# ---------------------------------------------------------------- write
OUT.mkdir(exist_ok=True)
(OUT / "style.css").write_text(CSS.strip() + "\n")
paths = [
    page("", "Nuqta OCR: open-source Arabic OCR, first on KITAB-Bench and Misraj",
         "Open-source Arabic OCR models and Python library. Converts Arabic scans, photos and PDFs to text or Markdown, keeps printed "
         "tashkeel, reads tables, IDs and passports. Best published scores on KITAB-Bench and Misraj-DocOCR.",
         home_body, ld=[SOFTWARE, faq_ld(HOME_FAQ)], alt="ar/"),
    page("ar/", "نقطة: OCR عربي مفتوح المصدر لتحويل الصور وملفات PDF إلى نص",
         "نماذج ومكتبة مفتوحة المصدر للتعرف الضوئي على النص العربي: تحويل الصور والمستندات الممسوحة وملفات PDF إلى نص، مع التشكيل والجداول "
         "والبطاقات وجوازات السفر. الأول على معياري KITAB-Bench وMisraj-DocOCR.",
         ar_body, lang="ar", ld=[SOFTWARE, faq_ld(AR_FAQ)], alt=""),
    page("best-arabic-ocr/", "Best Arabic OCR models in 2026: benchmark comparison",
         "KITAB-Bench and Misraj-DocOCR results for Arabic OCR: Nuqta, Gemini, GPT-4o, GPT-5, Azure, Mistral OCR, Baseer, QARI, "
         "dots.ocr, Tesseract and EasyOCR.", cmp_body, ld=[faq_ld(CMP_FAQ)], kind="Article"),
    page("guides/", "Arabic OCR guides | Nuqta OCR", "Guides for Arabic OCR: PDFs to text, tashkeel, IDs and passports, Tesseract alternative, offline use.",
         guides_body),
] + [f"guides/{s}/" for s, _, _ in GUIDES]

(OUT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{BASE + p}</loc><lastmod>{TODAY}</lastmod></url>\n" for p in paths) + "</urlset>\n")
(OUT / "robots.txt").write_text(
    "User-agent: *\nAllow: /\n\n"
    + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in
              ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot",
               "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot", "Bingbot"])
    + f"Sitemap: {BASE}sitemap.xml\n")
(OUT / "llms.txt").write_text((ROOT / "llms.txt").read_text().rstrip() + f"\n- Website: {BASE} · Benchmarks: {BASE}best-arabic-ocr/ · Guides: {BASE}guides/\n")
(OUT / ".nojekyll").write_text("")
print("built", len(paths), "pages into", OUT)
