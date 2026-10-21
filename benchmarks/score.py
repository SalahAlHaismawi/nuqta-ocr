"""Score prediction files ({"id", "ref", "hyp"} per line) with the published KITAB-Bench and Misraj-DocOCR recipes.

    python benchmarks/score.py results/nuqta-0.8b/kitab_*.jsonl            # KITAB-Bench OCR: per set + macro average
    python benchmarks/score.py results/nuqta-0.8b/misraj_dococr.jsonl --teds-jobs 4
    python benchmarks/score.py results/nuqta-0.8b                          # a directory = every *.jsonl in it

The recipe is picked from the file name (kitab_* -> kitab, misraj_* / *pdf2md* -> misraj) or forced with --recipe.
Standalone: the KITAB-Bench functions are vendored in kitab_official.py (MIT, attribution there); nothing here
imports the nuqta package.

kitab   KITAB-Bench image-to-text (ocr-eval/metrics.py): preprocess_arabic_text on reference and prediction (newlines
        -> space, tashkeel U+064B-U+065F/U+0670 removed, [إأٱآ] -> ا, ة -> ه, ى -> ي, tatweel removed, whitespace
        collapsed), then corpus CER / WER (sum of Levenshtein edits / sum of reference length: what torchmetrics
        CharErrorRate / WordErrorRate compute), sacrebleu corpus BLEU and chrF. The headline number is the unweighted
        mean over the 13 subsets of each subset's CER, rounded to 2 dp first as ocr-eval/metrics.py does; the
        unrounded mean (3 dp) is printed next to it.

misraj  Misraj-DocOCR / Baseer (arXiv:2509.18174 §7.1). Misraj published no code; the paper gives six output
        standardization steps and reuses KITAB-Bench's pdfs-eval metrics (CER, WER, BLEU, chrF, TEDS, MARS):
          1. markdown pipe tables -> HTML (Baseer step 2)
          2. <table>...</table> blocks are cut out (regex from pdfs-eval/eval.py) and scored by TEDS only; the
             remaining text gets the text metrics (as in pdfs-eval)
          3. <img>...</img> placeholders dropped; <page_number>/<watermark> unwrapped (step 6, content kept); every
             other HTML tag outside tables unwrapped (step 1); horizontal rules -> "—" (step 3); "#  Heading" ->
             "# Heading" (step 4); step 5 (<b> in tables) is moot, aug_html unwraps those tags before TEDS
          4. KITAB pdfs-eval preprocess_arabic_text on the text (markdown syntax and punctuation are NOT stripped)
          5. corpus CER / WER, sacrebleu corpus BLEU and chrF (chrF2, sacrebleu default, what KITAB's code runs);
             TEDS per page = mean over the reference tables of the best-matching predicted table, averaged over the
             pages that have reference tables, x100; MARS = (chrF + TEDS) / 2.
Nothing is clipped or trimmed by default: a runaway prediction counts in full.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from Levenshtein import distance as lev  # noqa: E402  (KITAB-Bench uses python-Levenshtein)
from sacrebleu import corpus_bleu, corpus_chrf, sentence_chrf  # noqa: E402

from kitab_official import TEDS, aug_html, preprocess_arabic_text, preprocess_arabic_text_ocr  # noqa: E402

# ------------------------------------------------------------------ markdown pipe tables -> HTML (Baseer step 2)
_PIPE_ROW = re.compile(r"^\s*\|(.*)\|\s*$")
_PIPE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def pipe_tables_to_html(text: str) -> str:
    """Rewrite markdown pipe tables as <table><thead>/<tbody> HTML; other lines untouched.
    A table is a run of |...| rows; the row before a |---| separator is the header."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        if not _PIPE_ROW.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        block = []
        while i < len(lines) and (_PIPE_ROW.match(lines[i]) or _PIPE_SEP.match(lines[i])):
            block.append(lines[i])
            i += 1

        def cells(ln: str) -> list[str]:
            return [c.strip() for c in _PIPE_ROW.match(ln).group(1).split("|")]

        head, body = None, []
        for k, ln in enumerate(block):
            if _PIPE_SEP.match(ln):
                continue
            if head is None and k + 1 < len(block) and _PIPE_SEP.match(block[k + 1]):
                head = cells(ln)
            else:
                body.append(cells(ln))
        html = ["<table>"]
        if head:
            html += ["  <thead>", "    <tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr>", "  </thead>"]
        html += ["  <tbody>"] + ["    <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body] + ["  </tbody>", "</table>"]
        out.extend(html)
    return "\n".join(out)


# ------------------------------------------------------------------ loop trimming (optional, NOT official)
_CYCLE = re.compile(r"(.{8,200}?)(?:\s*\1){2,}", re.S)
_CHAR_RUN = re.compile(r"([^\s<])\1{9,}")


def trim_loops(text: str) -> str:
    """The nuqta library's loop trimming (nuqta.text.trim_loops): a span repeated 3+ times back to back keeps one
    copy, a long line (>= 40 chars) that re-appears later is dropped. Only with --trim-loops."""
    text = _CHAR_RUN.sub(r"\1", text)
    prev = None
    while prev != text:
        prev = text
        text = _CYCLE.sub(lambda m: m.group(0) if not m.group(1).replace("<", "").strip() else m.group(1), text)
    seen, out = set(), []
    for line in text.split("\n"):
        key = re.sub(r"\s+", " ", line).strip()
        if len(key) >= 40 and key in seen:
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out)


# ------------------------------------------------------------------ Baseer §7.1 output standardization
_TABLE = re.compile(r"<table[\s\S]*?</table>", re.I)  # pdfs-eval/eval.py extract_html_tables_from_file
_IMG = re.compile(r"<img\b[^>]*>.*?</img>|<image\b[^>]*>.*?</image>|<img\b[^>]*/?>|<image>", re.I | re.S)
_MODEL_TAGS = re.compile(r"<(page_number|watermark)\b[^>]*>(.*?)</\1>", re.I | re.S)
_ANY_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9_]*\b[^>]*/?>")
_HR = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,}|—+)[ \t]*$", re.M)
_HEAD = re.compile(r"^[ \t]*(#{1,6})[ \t]*(?=\S)", re.M)
_CODE_FENCE = re.compile(r"^```[a-zA-Z]*\s*$", re.M)


def baseer_standardize(text: str) -> tuple[str, list[str]]:
    """The six post-processing steps of arXiv:2509.18174 §7.1; returns (text without tables, [html tables])."""
    text = _CODE_FENCE.sub("", text or "")
    text = pipe_tables_to_html(text)  # step 2
    tables = _TABLE.findall(text)
    text = _TABLE.sub(" ", text)
    text = _IMG.sub(" ", text)  # image placeholders carry no page text
    text = _MODEL_TAGS.sub(r" \2 ", text)  # step 6: model-specific tags go, their text (page numbers) stays
    text = _ANY_TAG.sub(" ", text)  # step 1: no HTML outside tables
    text = _HR.sub("—", text)  # step 3
    text = _HEAD.sub(r"\1 ", text)  # step 4
    return text, tables


# ------------------------------------------------------------------ metrics
def is_runaway(ref: str, hyp: str) -> bool:
    return len(hyp) > 2 * len(ref) + 20


def text_metrics(refs: list[str], hyps: list[str], check_torchmetrics: bool = False) -> dict:
    """Corpus CER / WER / BLEU / chrF (the published numbers) plus per-page means for reference."""
    page_cer, page_wer, page_chrf, eds, weds = [], [], [], [], []
    for r, h in zip(refs, hyps):
        d, wd = lev(r, h), lev(r.split(), h.split())
        eds.append(d)
        weds.append(wd)
        if r:
            page_cer.append(d / len(r))
            page_wer.append(wd / len(r.split()))
        page_chrf.append(sentence_chrf(h, [r]).score)
    ref_chars = sum(len(r) for r in refs)
    ref_words = sum(len(r.split()) for r in refs)
    out = {"cer": sum(eds) / max(ref_chars, 1), "wer": sum(weds) / max(ref_words, 1)}
    if check_torchmetrics:  # the exact classes KITAB-Bench calls (needs torch; slow on runaway pages)
        from torchmetrics.text import CharErrorRate, WordErrorRate
        out["cer_torchmetrics"] = CharErrorRate()(hyps, refs).item()
        out["wer_torchmetrics"] = WordErrorRate()(hyps, refs).item()
    nan = float("nan")
    out |= {
        "bleu": corpus_bleu(hyps, [refs]).score,
        "chrf": corpus_chrf(hyps, [refs]).score,  # sacrebleu default = chrF2 (what KITAB's code runs)
        "chrf3": corpus_chrf(hyps, [refs], beta=3).score,  # what the KITAB paper's MARS formula writes
        "edit_distance_mean": statistics.fmean(eds) if eds else 0.0,
        "cer_page_mean": statistics.fmean(page_cer) if page_cer else nan,
        "cer_page_median": statistics.median(page_cer) if page_cer else nan,
        "wer_page_mean": statistics.fmean(page_wer) if page_wer else nan,
        "chrf_page_mean": statistics.fmean(page_chrf) if page_chrf else nan,
        "ref_chars": ref_chars,
        "hyp_chars": sum(len(h) for h in hyps),
        "ref_words": ref_words,
        "_eds": eds, "_ref_lens": [len(r) for r in refs],  # per page, for --bootstrap (not saved)
    }
    return out


_TEDS = TEDS()


def page_teds(args: tuple[list[str], list[str]]) -> float | None:
    """pdfs-eval/metrics.py: each reference table takes its best-matching predicted table (0 if none); pages without
    reference tables are not scored (extra predicted tables cost nothing)."""
    gt_tables, pred_tables = args
    if not gt_tables:
        return None
    best = []
    for g in gt_tables:
        gh = aug_html(preprocess_arabic_text(g))
        best.append(max((_TEDS.evaluate(aug_html(preprocess_arabic_text(p)), gh) for p in pred_tables), default=0.0))
    return statistics.fmean(best)


def read_rows(path: Path) -> tuple[list[dict], int]:
    rows, errors = [], 0
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if str(r.get("hyp") or "").startswith("<<ERROR"):  # a failed request, not a prediction
            errors += 1
            continue
        rows.append(r)
    return rows, errors


def _prep_hyp(ref: str, hyp: str, clip: bool, loops: bool) -> str:
    if loops:
        hyp = trim_loops(hyp)
    if clip:
        hyp = hyp[: 2 * len(ref) + 20]
    return hyp


def score_misraj(rows: list[dict], *, teds_jobs: int = 1, with_teds: bool = True, clip: bool = False,
                 loops: bool = False, check_torchmetrics: bool = False) -> dict:
    refs, hyps, pairs, n_gt, n_pred, runaways = [], [], [], 0, 0, 0
    for r in rows:
        ref, hyp = r["ref"], r["hyp"] or ""
        runaways += is_runaway(ref, hyp)
        hyp = _prep_hyp(ref, hyp, clip, loops)
        rt, rtab = baseer_standardize(ref)
        ht, htab = baseer_standardize(hyp)
        n_gt += len(rtab)
        n_pred += len(htab)
        refs.append(preprocess_arabic_text(rt).strip())
        hyps.append(preprocess_arabic_text(ht).strip())
        pairs.append((rtab, htab))
    out = text_metrics(refs, hyps, check_torchmetrics)
    out |= {"samples": len(rows), "runaways": runaways, "gt_tables": n_gt, "pred_tables": n_pred,
            "_ids": [r.get("id", i) for i, r in enumerate(rows)]}
    if with_teds:
        if teds_jobs > 1:
            with ProcessPoolExecutor(max_workers=teds_jobs) as pool:
                scores = list(pool.map(page_teds, pairs, chunksize=1))
        else:
            scores = [page_teds(p) for p in pairs]
        out["_teds"] = scores
        scores = [s for s in scores if s is not None]
        out["teds"] = 100 * statistics.fmean(scores) if scores else float("nan")
        out["teds_pages"] = len(scores)
        out["mars"] = (out["chrf"] + out["teds"]) / 2 if scores else float("nan")
        out["mars_chrf3"] = (out["chrf3"] + out["teds"]) / 2 if scores else float("nan")
    return out


def score_kitab(rows: list[dict], *, clip: bool = False, loops: bool = False, check_torchmetrics: bool = False) -> dict:
    refs, hyps, runaways = [], [], 0
    for r in rows:
        hyp = r["hyp"] or ""
        runaways += is_runaway(r["ref"], hyp)
        hyp = _prep_hyp(r["ref"], hyp, clip, loops)
        refs.append(preprocess_arabic_text_ocr(r["ref"]).strip())
        hyps.append(preprocess_arabic_text_ocr(hyp).strip())
    out = text_metrics(refs, hyps, check_torchmetrics)
    out |= {"samples": len(rows), "runaways": runaways, "_ids": [r.get("id", i) for i, r in enumerate(rows)]}
    return out


# ------------------------------------------------------------------ bootstrap confidence intervals
def _ci(xs: list[float]) -> tuple[float, float]:
    xs = sorted(xs)
    return xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]


def bootstrap(kitab: list[tuple[str, dict]], misraj: list[tuple[str, dict]], n: int, seed: int = 0) -> dict:
    """95% CIs by resampling pages (the model cards' intervals): KITAB pages are resampled within each subset and the
    statistic is the (unrounded) macro mean of the subsets' corpus CERs; Misraj resamples all pages for the corpus CER
    and, separately, the table pages for TEDS. One random stream (seed 0) runs over the KITAB subsets in name order and
    then over the Misraj files, so the cards' intervals come out exactly when both are scored in one call."""
    import random

    rng, res = random.Random(seed), {}
    if kitab:
        subs = []
        for _, s in sorted(kitab, key=lambda x: x[0]):
            pages = dict(zip(s["_ids"], zip(s["_eds"], s["_ref_lens"])))
            subs.append((pages, sorted(pages, key=str)))
        point = statistics.fmean(sum(p[k][0] for k in ks) / sum(p[k][1] for k in ks) for p, ks in subs)
        boots = []
        for _ in range(n):
            samp = [[rng.choice(ks) for _ in ks] for _, ks in subs]
            boots.append(statistics.fmean(sum(p[k][0] for k in sm) / max(1, sum(p[k][1] for k in sm))
                                          for (p, _), sm in zip(subs, samp)))
        lo, hi = _ci(boots)
        print(f"\n== bootstrap ({n}x): KITAB macro CER {point:.3f}  95% CI {lo:.3f}-{hi:.3f}")
        res["kitab_macro_cer"] = {"point": point, "ci95": [lo, hi]}
    for name, s in misraj:
        pages = dict(zip(s["_ids"], zip(s["_eds"], s["_ref_lens"], s.get("_teds") or [None] * len(s["_ids"]))))
        mk = sorted(pages, key=str)
        tk = [k for k in mk if pages[k][2] is not None]

        def stat(ks, tks):
            cer = sum(pages[k][0] for k in ks) / max(1, sum(pages[k][1] for k in ks))
            return cer, (100 * statistics.fmean(pages[k][2] for k in tks) if tks else float("nan"))

        bc, bt = [], []
        for _ in range(n):
            ks = [rng.choice(mk) for _ in mk]
            tks = [rng.choice(tk) for _ in tk]
            c, t = stat(ks, tks)
            bc.append(c)
            bt.append(t)
        pc, pt = stat(mk, tk)
        (cl, ch), (tl, th) = _ci(bc), _ci(bt)
        print(f"== bootstrap ({n}x): {name} CER {pc:.3f}  95% CI {cl:.3f}-{ch:.3f}   "
              f"TEDS {pt:.1f}  95% CI {tl:.1f}-{th:.1f} ({len(tk)} table pages)")
        res[name] = {"cer": {"point": pc, "ci95": [cl, ch]}, "teds": {"point": pt, "ci95": [tl, th]}}
    return res


def guess_recipe(path: Path) -> str:
    n = path.stem.lower()
    if n.startswith("misraj") or "pdf2md" in n or "pdf_to_markdown" in n:
        return "misraj"
    return "kitab" if n.startswith("kitab") else "misraj"


def fmt(s: dict, recipe: str) -> str:
    line = (f"CER {s['cer']:.3f} (page-mean {s['cer_page_mean']:.3f}, median {s['cer_page_median']:.3f})  "
            f"WER {s['wer']:.3f} (page-mean {s['wer_page_mean']:.3f})  "
            f"BLEU {s['bleu']:.2f}  chrF {s['chrf']:.2f} (chrF3 {s['chrf3']:.2f}, page-mean {s['chrf_page_mean']:.2f})")
    if recipe == "misraj" and "teds" in s:
        line += (f"  TEDS {s['teds']:.1f} ({s['teds_pages']} pages w/ GT tables)  MARS {s['mars']:.2f} "
                 f"(chrF3-MARS {s['mars_chrf3']:.2f})")
    line += f"  | n={s['samples']} runaways={s['runaways']} ref_chars={s['ref_chars']} hyp_chars={s['hyp_chars']}"
    if "cer_torchmetrics" in s:
        same = abs(s["cer_torchmetrics"] - s["cer"]) < 1e-6 and abs(s["wer_torchmetrics"] - s["wer"]) < 1e-6
        line += (f"\n             torchmetrics check: CER {s['cer_torchmetrics']:.6f} WER {s['wer_torchmetrics']:.6f}"
                 f" -> {'identical' if same else 'DIFFERENT'}")
    return line


def expand(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        out += sorted(p.glob("*.jsonl")) if p.is_dir() else [p]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path, help="prediction .jsonl files, or directories of them")
    ap.add_argument("--recipe", choices=["auto", "misraj", "kitab"], default="auto")
    ap.add_argument("--teds-jobs", type=int, default=1, help="processes for TEDS (does not change the score)")
    ap.add_argument("--no-teds", action="store_true")
    ap.add_argument("--clip-runaways", action="store_true", help="clip predictions to 2x reference + 20 chars (NOT official)")
    ap.add_argument("--trim-loops", action="store_true", help="apply the library's loop trimming first (NOT official)")
    ap.add_argument("--check-torchmetrics", action="store_true", help="re-check CER/WER with torchmetrics (needs torch)")
    ap.add_argument("--bootstrap", type=int, metavar="N", help="also print 95%% CIs from N page resamples (cards: 2000)")
    ap.add_argument("--json", type=Path, help="write every score to this JSON file")
    args = ap.parse_args()

    results, kitab, misraj = {}, [], []
    for path in expand(args.files):
        rows, errors = read_rows(path)
        recipe = guess_recipe(path) if args.recipe == "auto" else args.recipe
        print(f"\n== {path}  [{recipe} recipe, {len(rows)} pages" + (f", {errors} <<ERROR rows skipped" if errors else "") + "]")
        kw = {"clip": args.clip_runaways, "loops": args.trim_loops, "check_torchmetrics": args.check_torchmetrics}
        if recipe == "kitab":
            s = score_kitab(rows, **kw)
            kitab.append((path.stem, s))
        else:
            s = score_misraj(rows, teds_jobs=args.teds_jobs, with_teds=not args.no_teds, **kw)
            misraj.append((str(path), s))
        print("official     " + fmt(s, recipe), flush=True)
        results[str(path)] = {"recipe": recipe, **{k: v for k, v in s.items() if not k.startswith("_")}}

    if len(kitab) > 1:  # ocr-eval/metrics.py: mean over subsets of each subset's rounded corpus rate
        cer = statistics.fmean(round(s["cer"], 2) for _, s in kitab)
        wer = statistics.fmean(round(s["wer"], 2) for _, s in kitab)
        chrf = statistics.fmean(round(s["chrf"], 2) for _, s in kitab)
        cer3 = statistics.fmean(s["cer"] for _, s in kitab)
        print(f"\n== KITAB macro average over {len(kitab)} subsets: CER {cer:.2f} | WER {wer:.2f} | chrF {chrf:.2f}"
              f"   (unrounded mean CER {cer3:.3f})")
        results["kitab_macro"] = {"subsets": len(kitab), "cer": cer, "wer": wer, "chrf": chrf, "cer_unrounded": cer3}
    if args.bootstrap:
        results["bootstrap"] = bootstrap(kitab, misraj, args.bootstrap)
    if args.json:
        args.json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"saved {args.json}")


if __name__ == "__main__":
    main()
