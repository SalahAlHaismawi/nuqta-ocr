"""Produce benchmark predictions ({"id", "ref", "hyp"} per line, one .jsonl per set) for KITAB-Bench and Misraj-DocOCR.

    # 1) serve the model with vLLM (the published numbers were made this way)
    vllm serve SalahALHaismawi/Nuqta-OCR-0.8B --served-model-name nuqta --max-model-len 16384
    # 2) predictions: images as given (default) or with the library's page enlarging
    python benchmarks/run.py --sets kitab misraj --model nuqta --out results/nuqta-0.8b
    python benchmarks/run.py --sets kitab_hindawi misraj --model nuqta --out results/nuqta-0.8b-enlarged --page-enlarging
    # or without a server, through the nuqta library's own generation backend (vLLM offline or transformers)
    python benchmarks/run.py --sets kitab misraj --backend nuqta --model SalahALHaismawi/Nuqta-OCR-0.8B --out ...
    # 3) score
    python benchmarks/score.py results/nuqta-0.8b

Datasets are downloaded from the Hugging Face Hub at pinned revisions (the ones every published number was measured
on). Settings (fixed, as published): greedy decoding (temperature 0), repetition penalty 1.0, thinking disabled,
8192 new tokens at most, every image capped at 2.4 MP (the training size). Prompt: the "as-written" mode prompt for
the KITAB-Bench OCR sets, the "markdown" mode prompt for Misraj-DocOCR. Output is cleaned the way the library does
(code fences and <think> blocks removed) and is otherwise raw: no loop trimming, no fallback re-read.

Runs are resumable: ids already in an output file are skipped, failed requests are not written and are retried on
the next run.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------- datasets
# name -> (Hub dataset, pinned revision, reference column)
DATASETS = {
    "kitab_adab": ("ahmedheakl/arocrbench_adab", "a3e21b255b386517a57d5ed7c19f3eeda0246876", "text"),
    "kitab_arabicocr": ("ahmedheakl/arocrbench_arabicocr", "23f27f0905157fe1f4eeb6e2f68e2d8e440ca65c", "text"),
    "kitab_evarest": ("ahmedheakl/arocrbench_evarest", "f9eac11881d008f21d3a766556526660752caaf9", "text"),
    "kitab_hindawi": ("ahmedheakl/arocrbench_hindawi", "5693b901e43bb5c72b4b77e4a3efeadfd01739a8", "text"),
    "kitab_historicalbooks": ("ahmedheakl/arocrbench_historicalbooks", "cbe0684cfc878f281be6d6b11c22f41d32842c00", "answer"),
    "kitab_historyar": ("ahmedheakl/arocrbench_historyar", "4e8d71775498cb10b873453910a2819714b46463", "text"),
    "kitab_isippt": ("ahmedheakl/arocrbench_isippt", "6f4a6c330923cab4fabb3bccbc28a31a8f4e5c7a", "text"),
    "kitab_khatt": ("ahmedheakl/arocrbench_khatt", "0535f85e967ee715f1ac01f2af802130d26567ac", "text"),
    "kitab_khattparagraph": ("ahmedheakl/arocrbench_khattparagraph", "d0e44472833d6de53ff23ca0cb1d36c77a213581", "answer"),
    "kitab_muharaf": ("ahmedheakl/arocrbench_muharaf", "36579daf4929d82da45c90e24398041da3019a0d", "text"),
    "kitab_onlinekhatt": ("ahmedheakl/arocrbench_onlinekhatt", "8c90441e48754066b1440d53c12098ece35684cd", "text"),
    "kitab_patsocr": ("ahmedheakl/arocrbench_patsocr", "b43dcde0a749fef3ab49690fe07f855b420acff1", "answer"),
    "kitab_synthesizear": ("ahmedheakl/arocrbench_synthesizear", "01a9a05f08c4b75dc54e66a3805b2d945ef954ae", "text"),
    "misraj_dococr": ("Misraj/Misraj-DocOCR", "7177bf70f77ce259890d6af0bef53f18faf26ec9", "markdown"),
    "kitab_pdf2md_reviewed": ("Misraj/KITAB_pdf_to_markdown_reviewed", "8890d721c660cd027839bc8bc48634552fe7aec6", "markdown"),
}
KITAB_OCR = [n for n in DATASETS if n.startswith("kitab_") and n != "kitab_pdf2md_reviewed"]  # the 13 OCR subsets
GROUPS = {"kitab": KITAB_OCR, "misraj": ["misraj_dococr"]}
MARKDOWN_SETS = {"misraj_dococr", "kitab_pdf2md_reviewed"}

# ids left out of every published run (see excluded_ids.json for the reason)
EXCLUDED = {k: set(v) for k, v in json.loads((HERE / "excluded_ids.json").read_text()).items() if not k.startswith("_")}


@dataclass
class Sample:
    id: str
    image: bytes
    reference: str


def load_set(name: str, revision: str | None = None, local_dir: Path | None = None, limit: int | None = None,
             all_images: bool = True):
    """Yield the samples of one set. Ids are "<parquet file stem>:<row index over the whole set>", the ids of the
    published prediction files."""
    import pyarrow.parquet as pq

    repo, pinned, col = DATASETS[name]
    if local_dir is None:
        from huggingface_hub import snapshot_download

        local_dir = Path(snapshot_download(repo, repo_type="dataset", revision=revision or pinned,
                                           allow_patterns=["*.parquet"]))
    files = sorted(Path(local_dir).rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no parquet files for {name} under {local_dir}")
    skip = set() if all_images else EXCLUDED.get(name, set())
    n = kept = 0
    for f in files:
        pf = pq.ParquetFile(f)
        for batch in pf.iter_batches(batch_size=32, columns=["image", col]):
            for img, ref in zip(batch.column("image").to_pylist(), batch.column(col).to_pylist()):
                data = img.get("bytes") if isinstance(img, dict) else img
                if data is None or ref is None:
                    continue
                sid = f"{f.stem}:{n}"
                n += 1
                if sid in skip:
                    continue
                yield Sample(sid, data, ref)
                kept += 1
                if limit and kept >= limit:
                    return


# --------------------------------------------------------------------------- image policy
TRAIN_PIXELS = 2_400_000  # the training size, and the cap for every image


def is_page(w: int, h: int) -> bool:
    """nuqta.preprocess.is_page: aspect <= 2 and short side >= 450 px."""
    return max(w, h) / max(min(w, h), 1) <= 2.0 and min(w, h) >= 450


def prepare(data: bytes, enlarge: str):
    """enlarge="none": images as given (only capped at 2.4 MP). "pages": the nuqta library's page rule
    (nuqta.preprocess.prepare): a page-shaped image under 2.4 MP is enlarged to 2.4 MP, crops keep their size."""
    from PIL import Image

    im = Image.open(io.BytesIO(data))
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")  # composite onto white: a bare RGB conversion turns transparent pixels black
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im).convert("RGB")
    elif im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    area = im.width * im.height
    if area < TRAIN_PIXELS and enlarge == "pages" and is_page(im.width, im.height):
        k = (TRAIN_PIXELS / area) ** 0.5
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    if im.width * im.height > TRAIN_PIXELS:
        k = (TRAIN_PIXELS / (im.width * im.height)) ** 0.5
        im = im.resize((max(32, int(im.width * k)), max(32, int(im.height * k))), Image.LANCZOS)
    return im


def png_bytes(im) -> bytes:
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


# --------------------------------------------------------------------------- prompts / output clean-up
try:  # the library's prompts when it is installed (they are the training prompts)
    from nuqta.text import PROMPTS
except ImportError:
    PROMPTS = {
        "as-written": "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) "
                      "that are visible in the image.",
        "markdown": "Convert this document to Markdown: headings, paragraphs, lists and tables in reading order. Include "
                    "only the diacritics visible in the image.",
    }

_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"^```\w*\n?|\n?```$")


def clean(text: str) -> str:
    text = _THINK.sub("", text or "")
    return _FENCE.sub("", text.strip()).strip()


MAX_TOKENS = 8192


# --------------------------------------------------------------------------- generation
async def _predict(client, url: str, model: str, prompt: str, png: bytes, max_tokens: int, api_key: str | None) -> str:
    import httpx

    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}},
            {"type": "text", "text": prompt},
        ]}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "repetition_penalty": 1.0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    for attempt in range(4):
        try:
            r = await client.post(f"{url}/chat/completions", json=body, headers=headers, timeout=600)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, KeyError) as e:
            if attempt == 3:
                return f"<<ERROR {type(e).__name__}: {e}>>"
            await asyncio.sleep(2 ** attempt)
    return ""


async def run_endpoint(args, samples: list[Sample], prompt: str, out) -> int:
    import httpx

    sem = asyncio.Semaphore(args.concurrency)
    failed = 0

    async with httpx.AsyncClient() as client:
        async def one(s: Sample):
            nonlocal failed
            async with sem:
                png = png_bytes(prepare(s.image, args.enlarge))
                hyp = await _predict(client, args.url, args.model, prompt, png, args.max_tokens, args.api_key)
            if hyp.startswith("<<ERROR"):
                failed += 1
                return
            out.write(json.dumps({"id": s.id, "ref": s.reference, "hyp": clean(hyp)}, ensure_ascii=False) + "\n")
            out.flush()

        await asyncio.gather(*(one(s) for s in samples))
    return failed


def run_library(backend, args, samples: list[Sample], prompt: str, out) -> int:
    for i in range(0, len(samples), args.batch):
        chunk = samples[i:i + args.batch]
        items = [(prepare(s.image, args.enlarge).convert("RGB"), prompt) for s in chunk]
        for s, hyp in zip(chunk, backend.generate(items, args.max_tokens)):
            out.write(json.dumps({"id": s.id, "ref": s.reference, "hyp": clean(hyp)}, ensure_ascii=False) + "\n")
        out.flush()
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", required=True,
                    help=f"groups {list(GROUPS)} or set names {list(DATASETS)}")
    ap.add_argument("--out", type=Path, required=True, help="output directory (one <set>.jsonl per set)")
    ap.add_argument("--model", required=True, help="served model name (endpoint) or Hub id / local path (--backend nuqta)")
    ap.add_argument("--backend", choices=["endpoint", "nuqta"], default="endpoint",
                    help="endpoint: an OpenAI-compatible server such as `vllm serve` (default); nuqta: the library's "
                         "generation backend in-process")
    ap.add_argument("--nuqta-backend", default="auto", help="with --backend nuqta: auto, vllm or transformers")
    ap.add_argument("--url", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--api-key", default=None, help="bearer token for the endpoint, if it needs one")
    ap.add_argument("--page-enlarging", dest="enlarge", action="store_const", const="pages", default="none",
                    help="the nuqta library's page rule: page-shaped images under 2.4 MP are enlarged to 2.4 MP")
    ap.add_argument("--mode", choices=["auto", "as-written", "markdown"], default="auto",
                    help="prompt (auto: markdown for Misraj / pdf2md, as-written for the KITAB OCR sets)")
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--concurrency", type=int, default=16, help="parallel requests (endpoint)")
    ap.add_argument("--batch", type=int, default=16, help="images per generate() call (--backend nuqta)")
    ap.add_argument("--limit", type=int, help="first N images per set (smoke tests)")
    ap.add_argument("--exclude-overlap", dest="all_images", action="store_false",
                    help="leave out the 114 PATS-OCR lines whose text is in our training data (excluded_ids.json); "
                         "the published numbers use the full official set")
    ap.add_argument("--revision", help="dataset revision instead of the pinned one (numbers may then differ)")
    ap.add_argument("--data-dir", type=Path, help="read <data-dir>/<set>/**/*.parquet instead of downloading")
    args = ap.parse_args()

    names = [n for s in args.sets for n in GROUPS.get(s, [s])]
    unknown = [n for n in names if n not in DATASETS]
    if unknown:
        sys.exit(f"unknown sets {unknown}; choose from {list(GROUPS)} or {list(DATASETS)}")
    args.out.mkdir(parents=True, exist_ok=True)
    cfg = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k != "api_key"}
    cfg_path = args.out / "run_config.json"
    if cfg_path.exists():  # resuming: refuse to mix settings in one folder
        old = json.loads(cfg_path.read_text())
        clash = [k for k in ("model", "enlarge", "mode", "max_tokens", "revision") if old.get(k) != cfg[k]]
        if clash:
            sys.exit(f"{args.out} holds a run with other settings ({', '.join(f'{k}={old.get(k)!r}' for k in clash)}); "
                     "use another --out")
    cfg_path.write_text(json.dumps(cfg, indent=2))

    backend = None
    if args.backend == "nuqta":
        from nuqta.backends import make_backend
        backend = make_backend(args.model, args.nuqta_backend)

    failures = 0
    for name in names:
        mode = args.mode if args.mode != "auto" else ("markdown" if name in MARKDOWN_SETS else "as-written")
        prompt = PROMPTS[mode]
        path = args.out / f"{name}.jsonl"
        done = set()
        if path.exists():
            done = {json.loads(line)["id"] for line in path.open(encoding="utf-8") if line.strip()}
        local = args.data_dir / name if args.data_dir else None
        todo = [s for s in load_set(name, args.revision, local, args.limit, args.all_images) if s.id not in done]
        print(f"[{name}] {len(done)} done, {len(todo)} to run (mode {mode}, enlarge {args.enlarge})", flush=True)
        t0 = time.time()
        with path.open("a", encoding="utf-8") as out:
            if backend is None:
                failed = asyncio.run(run_endpoint(args, todo, prompt, out))
            else:
                failed = run_library(backend, args, todo, prompt, out)
        if todo:
            print(f"[{name}] {len(todo) - failed} written in {time.time() - t0:.0f}s"
                  + (f", {failed} requests FAILED (rerun to resume)" if failed else ""), flush=True)
        failures += failed
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
