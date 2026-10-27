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

CSS = """
:root{--paper:#F3EFE6;--card:#FAF8F3;--ink:#141414;--muted:#6E695F;--rule:#D8D2C5;--green:#0F7A5C;--soft:#E3EFE9;--code:#EBE6DA}
@media (prefers-color-scheme:dark){:root{--paper:#121412;--card:#1A1D1A;--ink:#ECE8DF;--muted:#A39E93;--rule:#33362F;--green:#4FC79C;--soft:#17271F;--code:#202320}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.6 'IBM Plex Sans',system-ui,sans-serif}
[lang=ar] body,body[dir=rtl]{font-family:'IBM Plex Sans Arabic','IBM Plex Sans',system-ui,sans-serif}
a{color:var(--green)}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--rule)}
header.top .wrap{display:flex;align-items:center;gap:20px;min-height:60px;flex-wrap:wrap}
header.top .brand{display:flex;align-items:center;gap:10px;font-weight:600;text-decoration:none;color:var(--ink)}
header.top .brand img{width:34px;height:34px;border-radius:8px}
header.top nav{display:flex;gap:16px;flex-wrap:wrap;margin-inline-start:auto;font-size:15px}
header.top nav a{color:var(--muted);text-decoration:none}
header.top nav a:hover{color:var(--ink)}
main{padding:40px 0 64px}
h1{font-family:'EB Garamond',Georgia,serif;font-weight:500;font-size:clamp(34px,6vw,54px);line-height:1.1;margin:0 0 16px}
h2{font-family:'EB Garamond',Georgia,serif;font-weight:500;font-size:clamp(26px,4vw,34px);line-height:1.2;margin:48px 0 12px}
h3{font-size:19px;margin:28px 0 8px}
[dir=rtl] .stat b{text-align:right}
bdi{white-space:nowrap}
.btn.primary{color:#fff}
@media (prefers-color-scheme:dark){.btn.primary{color:#0b1a14}}
[dir=rtl] h1,[dir=rtl] h2{font-family:'Amiri','IBM Plex Sans Arabic',serif;font-weight:700}
.lead{font-size:20px;color:var(--muted);max-width:760px}
.eyebrow{font-size:13px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--green);margin:0 0 10px}
.cta{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}
.btn{display:inline-block;padding:11px 18px;border-radius:10px;border:1px solid var(--rule);background:var(--card);color:var(--ink);text-decoration:none;font-weight:600}
.btn.primary{background:var(--green);border-color:var(--green);color:#fff}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:32px 0}
.stat{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:18px 20px}
.stat b{display:block;font-family:'EB Garamond',Georgia,serif;font-size:40px;font-weight:500;color:var(--green);line-height:1.1}
.stat span{color:var(--muted);font-size:15px}
.tbl{overflow-x:auto;margin:16px 0;border:1px solid var(--rule);border-radius:12px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{padding:9px 12px;text-align:start;border-bottom:1px solid var(--rule);white-space:nowrap}
th{font-weight:600;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.05em}
tr:last-child td{border-bottom:0}
tr.us td{background:var(--soft);font-weight:600}
td.n{font-variant-numeric:tabular-nums}
pre{background:var(--code);border-radius:10px;padding:14px 16px;overflow-x:auto;font-size:14px;line-height:1.5;direction:ltr;text-align:left}
code{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:.92em}
p code,li code{background:var(--code);padding:1px 5px;border-radius:5px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:18px 20px}
.card h3{margin:0 0 6px}
.card p{margin:0;color:var(--muted);font-size:15px}
.card a.more{display:inline-block;margin-top:10px;font-weight:600;text-decoration:none}
details{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 16px;margin:10px 0}
summary{font-weight:600;cursor:pointer}
details p{margin:8px 0 0;color:var(--muted)}
.note{color:var(--muted);font-size:14px}
.ar-text{font-family:'Amiri',serif;font-size:1.25em}
footer{border-top:1px solid var(--rule);padding:28px 0;color:var(--muted);font-size:14px}
footer a{color:var(--muted)}
@media (max-width:600px){body{font-size:16px}th,td{white-space:normal;padding:8px}td:first-child{min-width:120px}header.top nav{margin-inline-start:0}}
"""

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
<a class="brand" href="{rel(depth, 'ar/' if rtl else '')}"><img src="{rel(depth, 'img/icon.png')}" alt="" width="34" height="34">{'نقطة' if rtl else 'Nuqta OCR'}</a>
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

home_body = f"""
<p class="eyebrow">Open-source Arabic OCR</p>
<h1>Nuqta OCR: the most accurate open Arabic OCR</h1>
<p class="lead">Nuqta reads Arabic scans, photos and PDFs into text or Markdown. It is first on both public Arabic OCR
benchmarks, copies the tashkeel printed on the page without adding any, and runs on your own hardware, down to a phone.</p>
<div class="cta"><a class="btn primary" href="{DEMO}">Try it in your browser</a><a class="btn" href="{GH}">GitHub</a>
<a class="btn" href="{HF}Nuqta-Arabic-OCR-4B">Hugging Face</a><a class="btn" href="best-arabic-ocr/">Benchmarks</a></div>
<div class="stats">
<div class="stat"><b>0.106</b><span>KITAB-Bench character error rate. Gemini-2.0-Flash: 0.13</span></div>
<div class="stat"><b>82.8</b><span>Misraj-DocOCR MARS. Baseer v2: 77.8</span></div>
<div class="stat"><b>0.08</b><span>invented diacritics per 100 letters (0.8B)</span></div>
<div class="stat"><b>1.6 GB</b><span>RAM for the 0.8B on a phone, offline</span></div>
</div>

<h2>What it reads</h2>
<div class="cards">
<div class="card"><h3>Books and scans</h3><p>Printed pages, old books and scanned documents, in reading order.</p></div>
<div class="card"><h3>PDFs to Markdown</h3><p>Headings, lists and tables as HTML. Every page of a PDF.</p></div>
<div class="card"><h3>Tashkeel as printed</h3><p>Vocalized text keeps its marks. Plain text stays plain.</p></div>
<div class="card"><h3>Tables</h3><p>Right-to-left and left-to-right tables, in the column order they are drawn.</p></div>
<div class="card"><h3>IDs and passports</h3><p>MRZ fields with ICAO check digits; failed checks are flagged, never guessed.</p></div>
<div class="card"><h3>Offline</h3><p>On-premises GPU, laptop CPU, Android and iPhone. Documents stay on your hardware.</p></div>
</div>

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
<p class="eyebrow">Benchmarks · updated {TODAY}</p>
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
<div class="cards">
<div class="card"><h3>Highest accuracy, own GPU</h3><p>Nuqta-Arabic-OCR 4B on a 16–24 GB GPU.</p><a class="more" href="{HF}Nuqta-Arabic-OCR-4B">Model →</a></div>
<div class="card"><h3>Small GPU, CPU or phone</h3><p>Nuqta-Arabic-OCR 0.8B, or its 560 MB GGUF build.</p><a class="more" href="{HF}Nuqta-Arabic-OCR-0.8B">Model →</a></div>
<div class="card"><h3>Coming from Tesseract</h3><p>A drop-in Python library with the same one-call use.</p><a class="more" href="../guides/tesseract-arabic-alternative/">Guide →</a></div>
</div>

<h2>Questions</h2>
{faq_html(CMP_FAQ)}
"""

# ---------------------------------------------------------------- guides
GUIDES = []

def guide(slug, title, desc, body, faq=()):
    GUIDES.append((slug, title, desc))
    full = f'<p class="eyebrow"><a href="../">Guides</a></p><h1>{html.escape(title)}</h1><p class="lead">{html.escape(desc)}</p>{body}'
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

guides_body = '<p class="eyebrow">Guides</p><h1>Arabic OCR guides</h1><p class="lead">How to use Nuqta OCR for common Arabic OCR jobs.</p><div class="cards">' + "".join(
    f'<div class="card"><h3>{html.escape(t)}</h3><p>{html.escape(d)}</p><a class="more" href="{s}/">Read →</a></div>' for s, t, d in GUIDES) + "</div>"

# ---------------------------------------------------------------- arabic home
AR_FAQ = [
    ("ما أفضل برنامج OCR عربي؟",
     "على المعيارين العامين للتعرف الضوئي على النص العربي، حقق نموذج Nuqta-Arabic-OCR 4B أفضل النتائج المنشورة: معدل خطأ في الحروف 0.106 على "
     "KITAB-Bench، ونتيجة 82.8 على Misraj-DocOCR، متقدمًا على Gemini وGPT وBaseer. وهو مفتوح المصدر برخصة Apache-2.0."),
    ("هل يحافظ على التشكيل؟",
     "نعم. ينقل التشكيل المطبوع في الصفحة كما هو، ونادرًا ما يضيف حركات غير موجودة فيها."),
    ("كيف أحوّل ملف PDF عربي إلى نص؟",
     "ثبّت المكتبة بالأمر pip install nuqta-ocr، ثم استخدم OCR('nuqta-4b').read('file.pdf').text، أو جرّب الصفحة التجريبية في المتصفح دون تثبيت."),
    ("هل يعمل دون إنترنت؟",
     "نعم. يعمل على خوادمك أو حاسوبك أو هاتفك دون اتصال، فلا تخرج مستنداتك من أجهزتك."),
    ("هل هو مجاني؟", "نعم، النماذج والمكتبة مجانية ومفتوحة المصدر، ويجوز استخدامها تجاريًا."),
]

ar_body = f"""
<p class="eyebrow">OCR عربي مفتوح المصدر</p>
<h1>نقطة: أدق نظام مفتوح المصدر للتعرف الضوئي على النص العربي</h1>
<p class="lead">يحوّل «نقطة» صور الصفحات والمستندات الممسوحة ضوئيًا وملفات PDF العربية إلى نص أو Markdown. وهو الأول على
معياري التعرف الضوئي العربي العامّين، وينقل التشكيل المطبوع كما هو، ويعمل على أجهزتك حتى الهاتف.</p>
<div class="cta"><a class="btn primary" href="{DEMO}">جرّبه في المتصفح</a><a class="btn" href="{GH}">GitHub</a>
<a class="btn" href="{HF}Nuqta-Arabic-OCR-4B">Hugging Face</a><a class="btn" href="../best-arabic-ocr/">المقارنة</a></div>
<div class="stats">
<div class="stat"><b dir="ltr">0.106</b><span>معدل خطأ الحروف على <bdi>KITAB-Bench</bdi>، مقابل 0.13 لنموذج <bdi>Gemini-2.0-Flash</bdi></span></div>
<div class="stat"><b dir="ltr">82.8</b><span>نتيجة <bdi>MARS</bdi> على <bdi>Misraj-DocOCR</bdi>، مقابل 77.8 لنموذج <bdi>Baseer v2</bdi></span></div>
<div class="stat"><b dir="ltr">0.08</b><span>حركة مضافة خطأً لكل 100 حرف (النموذج <bdi>0.8B</bdi>)</span></div>
<div class="stat"><b dir="ltr">1.6 GB</b><span>ذاكرة يحتاجها النموذج الصغير على الهاتف دون إنترنت</span></div>
</div>
<h2>ماذا يقرأ</h2>
<div class="cards">
<div class="card"><h3>الكتب والمستندات الممسوحة</h3><p>الصفحات المطبوعة والكتب القديمة، بترتيب القراءة الصحيح.</p></div>
<div class="card"><h3>تحويل PDF إلى نص</h3><p>العناوين والقوائم والجداول بصيغة HTML، لكل صفحات الملف.</p></div>
<div class="card"><h3>التشكيل كما هو مطبوع</h3><p>النص المشكول يحتفظ بحركاته، وغير المشكول يبقى دونها.</p></div>
<div class="card"><h3>الجداول</h3><p>جداول من اليمين إلى اليسار ومن اليسار إلى اليمين، بترتيب أعمدتها.</p></div>
<div class="card"><h3>البطاقات وجوازات السفر</h3><p>قراءة منطقة MRZ مع التحقق من أرقام الفحص.</p></div>
<div class="card"><h3>دون إنترنت</h3><p>على خوادمك أو حاسوبك أو هاتف أندرويد وآيفون.</p></div>
</div>
<h2>الاستخدام في بايثون</h2>
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
