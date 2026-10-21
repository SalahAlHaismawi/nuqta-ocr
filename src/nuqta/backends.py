"""Generation backends: Hugging Face transformers (default) and vLLM (fast batched serving, optional).

Both decode greedily (temperature 0, no repetition penalty), with thinking disabled: the settings the published
benchmark numbers were measured with.
"""
from __future__ import annotations

import base64
import io

from PIL import Image

MAX_NEW_TOKENS = 8192


def _data_url(im: Image.Image) -> str:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class TransformersBackend:
    def __init__(self, model: str, device_map: str = "auto", dtype: str = "bfloat16"):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(model)
        self.model = AutoModelForImageTextToText.from_pretrained(model, dtype=getattr(torch, dtype),
                                                                 device_map=device_map)
        self.model.eval()
        # stop at the end of the answer turn: the checkpoints' generation_config names only <|endoftext|>, so without
        # this generate() runs on into new chat turns up to max_new_tokens (vLLM stops via the chat template)
        tok = self.processor.tokenizer
        self.eos = [i for i in {tok.convert_tokens_to_ids("<|im_end|>"), tok.eos_token_id,
                                tok.convert_tokens_to_ids("<|endoftext|>")} if isinstance(i, int) and i >= 0]

    def generate(self, items: list[tuple[Image.Image, str]], max_new_tokens: int = MAX_NEW_TOKENS) -> list[str]:
        out = []
        for im, prompt in items:  # one at a time: pages differ a lot in size, padding a batch wastes memory
            msgs = [{"role": "user", "content": [{"type": "image", "image": im}, {"type": "text", "text": prompt}]}]
            inputs = self.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True,
                                                        return_dict=True, return_tensors="pt",
                                                        enable_thinking=False).to(self.model.device)
            with self.torch.inference_mode():
                ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, eos_token_id=self.eos,
                                         pad_token_id=self.eos[0])
            out.append(self.processor.decode(ids[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True))
        return out


class VLLMBackend:
    def __init__(self, model: str, gpu_memory_utilization: float = 0.85, max_model_len: int = 16384, **kw):
        from vllm import LLM, SamplingParams

        self.llm = LLM(model=model, gpu_memory_utilization=gpu_memory_utilization, max_model_len=max_model_len,
                       limit_mm_per_prompt={"image": 1}, **kw)
        self.SamplingParams = SamplingParams

    def generate(self, items: list[tuple[Image.Image, str]], max_new_tokens: int = MAX_NEW_TOKENS) -> list[str]:
        convs = [[{"role": "user", "content": [{"type": "image_url", "image_url": {"url": _data_url(im)}},
                                                {"type": "text", "text": prompt}]}] for im, prompt in items]
        sp = self.SamplingParams(temperature=0.0, max_tokens=max_new_tokens, repetition_penalty=1.0)
        res = self.llm.chat(convs, sp, chat_template_kwargs={"enable_thinking": False}, use_tqdm=False)
        return [r.outputs[0].text for r in res]


def make_backend(model: str, backend: str = "auto", **kw):
    if backend == "auto":
        try:
            import vllm  # noqa: F401
            backend = "vllm"
        except ImportError:
            backend = "transformers"
    if backend == "vllm":
        return VLLMBackend(model, **kw)
    if backend == "transformers":
        return TransformersBackend(model, **kw)
    raise ValueError(f"unknown backend {backend!r} (auto, transformers, vllm)")
