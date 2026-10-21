"""Precompute the demo's example readings with Nuqta-OCR 4B (served by vLLM, OpenAI API), so clicking an example in
the Space shows its result instantly without spending ZeroGPU time.

    python space/precompute_examples.py --url http://127.0.0.1:8100/v1 --model <served name>
"""
import argparse
import base64
import io
import json
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from app_examples import GALLERY, MODES  # noqa: E402
from nuqta import read_fields  # noqa: E402
from nuqta.preprocess import load_image, prepare  # noqa: E402
from nuqta.text import PROMPTS, clean, looped, trim_loops  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    a = ap.parse_args()
    out = {}
    for f, _, mode_label in GALLERY:
        mode = MODES[mode_label]
        im = prepare(load_image(HERE / "assets" / f))
        b = io.BytesIO()
        im.save(b, "PNG")
        body = {"model": a.model, "temperature": 0.0, "max_tokens": 8192, "chat_template_kwargs": {"enable_thinking": False},
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()}},
                    {"type": "text", "text": PROMPTS["markdown" if mode == "id" else mode]}]}]}
        text = clean(httpx.post(f"{a.url}/chat/completions", json=body, timeout=600).json()["choices"][0]["message"]["content"])
        if looped(text):
            text = trim_loops(text)
        fields = json.dumps(read_fields(text), ensure_ascii=False, indent=1, default=str) if mode == "id" else ""
        out[f] = {"text": text, "rendered": text if mode in ("markdown", "id") else "", "extra": fields}
        print(f, mode, len(text), flush=True)
    (HERE / "assets" / "example_outputs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
