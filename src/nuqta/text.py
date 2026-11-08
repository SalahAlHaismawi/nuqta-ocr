"""Output clean-up and loop detection."""
from __future__ import annotations

import re

PROMPTS = {
    "as-written": "Transcribe the Arabic text in this image exactly as written. Include only the diacritics (tashkeel) "
                  "that are visible in the image.",
    "bare": "Transcribe the Arabic text in this image without any diacritics.",
    "markdown": "Convert this document to Markdown: headings, paragraphs, lists and tables in reading order. Include "
                "only the diacritics visible in the image.",
}
MODES = tuple(PROMPTS)

_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"^```\w*\n?|\n?```$")
_CHAR_RUN = re.compile(r"([^\s<])\1{199,}")  # 200+ of one character: dotted / underlined form lines are shorter
_CYCLE = re.compile(r"(.{8,200}?)(?:\s*\1){2,}", re.S)
LOOP_CHARS = 200  # a reading that loses more than this to trim_loops counts as looped
END_REPEATS = 5  # a span repeated this often up to the very end of the output (cut off by the token limit) is a loop
RUNAWAY_REPEATS = 20  # a span repeated this often is a loop even mid-text; fewer repeats only count at the very end
LINE_REPEATS = 10  # a long line re-appearing this often is a loop (refrains and repeated table rows stay)


def clean(text: str) -> str:
    text = _THINK.sub("", text or "")
    return _FENCE.sub("", text.strip()).strip()


def trim_loops(text: str) -> str:
    """Remove runaway repetition only. Genuine repeats stay: identical table rows, dotted form lines, refrains and MRZ
    filler («<<<<»). A runaway is a span repeated back to back that either runs on to the end of the output (where
    generation was cut off) END_REPEATS+ times or repeats RUNAWAY_REPEATS+ times anywhere; it keeps one copy. A run of 200+ identical characters
    keeps one, and a long line (>= 40 chars) that appears LINE_REPEATS+ times is kept only at its first occurrence."""
    text = _CHAR_RUN.sub(r"\1", text)

    def cut(m):
        unit = m.group(1)
        if not unit.replace("<", "").strip():  # MRZ filler
            return m.group(0)
        reps = len(m.group(0)) / max(len(unit), 1)
        at_end = m.end() >= len(m.string.rstrip()) - 1
        return unit if ((at_end and reps >= END_REPEATS) or reps >= RUNAWAY_REPEATS) else m.group(0)

    prev = None
    while prev != text:
        prev = text
        text = _CYCLE.sub(cut, text)
    lines = text.split("\n")
    keys = [re.sub(r"\s+", " ", line).strip() for line in lines]
    count = {}
    for k in keys:
        count[k] = count.get(k, 0) + 1
    seen, out = set(), []
    for line, k in zip(lines, keys):
        if len(k) >= 40 and count[k] >= LINE_REPEATS and k in seen:
            continue
        seen.add(k)
        out.append(line)
    return "\n".join(out)


def looped(text: str) -> bool:
    return len(text) - len(trim_loops(text)) > LOOP_CHARS


# --- output validation -----------------------------------------------------------------
# The loop detector above removes repetition, but some degenerate readings are not repeats:
# a model that falls into a counting loop emits "1 2 3 4 ..." (or Arabic-Indic digits),
# which has no repeated substring and survives trim_loops.  Counting tables can also contain
# long ascending runs, so this only fires on a long run of *consecutive numeric tokens* with
# no words between them.
COUNTING_RUN = 10
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_TRIM = ".,;:،؛!?()[]{}<>«»\"'"


def _numeric_tokens(text: str) -> list[int]:
    out: list[int] = []
    for token in text.translate(_DIGITS).split():
        token = token.strip(_TRIM)
        if token.isdigit():
            out.append(int(token))
    return out


def counting_sequence(text: str, min_run: int = COUNTING_RUN) -> bool:
    """True for a long run of consecutive numbers (a common generation loop)."""
    numbers = _numeric_tokens(text)
    run = 1
    for previous, current in zip(numbers, numbers[1:]):
        run = run + 1 if current == previous + 1 else 1
        if run >= min_run:
            return True
    return False


def validate_text(text: str) -> list[str]:
    """Return human-readable reasons a reading looks degenerate (empty when clean).

    This is a warning, not a correction: the caller decides whether to retry,
    reject the page or pass it to a human.  The OCRmyPDF plugin treats any
    non-empty result as a hard failure.
    """
    issues: list[str] = []
    if looped(text):
        issues.append("repeated output")
    if counting_sequence(text):
        issues.append("counting sequence")
    letters = "".join(ch for ch in text if ch.isalpha())
    if len(letters) >= 40:
        most = max(set(letters), key=letters.count)
        if letters.count(most) / len(letters) > 0.5:
            issues.append("one character dominates")
    return issues
