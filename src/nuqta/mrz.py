"""Passport / ID machine-readable zone (ICAO 9303) from an OCR reading (2026-10-13).

parse_mrz(text) finds the MRZ lines in a model reading (TD3 passports 2 x 44, TD2 2 x 36, TD1 ID cards 3 x 30),
(visas MRV-A 2 x 44 / MRV-B 2 x 36: document code V, no composite check digit)
splits them into fields, checks every check digit and, given the whole reading, whether the number and dates also
appear in the printed (visual) zone. Nothing is corrected silently: a failed check digit is reported as failed.
The model may drop trailing '<' filler, so lines are padded to the format length; a field that falls in the
missing part is reported as unread.
"""
import re
from datetime import date

_LINE = re.compile(r"^[A-Z0-9<]{20,50}$")
_WEIGHTS = (7, 3, 1)
_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_TAG = re.compile(r"</?(?:td|th|tr|p|br|div|span|b|strong|em|i|code)\b[^<>]*>", re.IGNORECASE)


def check_digit(s: str) -> str:
    """ICAO 9303 check digit: weights 7, 3, 1; '<' = 0, A-Z = 10-35."""
    total = 0
    for i, c in enumerate(s):
        v = int(c) if c.isdigit() else (ord(c) - 55 if "A" <= c <= "Z" else 0)
        total += v * _WEIGHTS[i % 3]
    return str(total % 10)


def _candidates(text: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        s = _TAG.sub("", raw)  # markup the reading may wrap around the line (<td>, <p>); MRZ '<' is not a tag
        s = re.sub(r"\s+", "", s).upper().replace("«", "<").replace("‹", "<")
        # a line with no '<' (TD3 line 2 with a full optional field) counts only when long and number-heavy
        ok = _LINE.match(s) and ("<" in s or (len(s) >= 28 and sum(c.isdigit() for c in s) >= 6))
        out.append(s if ok else "")
    return out


def _groups(lines: list[str]) -> list[list[str]]:
    groups, cur = [], []
    for s in lines + [""]:
        if s:
            cur.append(s)
        elif cur:
            if any("<" in x for x in cur):
                groups.append(cur)
            cur = []
    return groups


def _fmt(lines: list[str]) -> tuple[str, int] | None:
    if len(lines) >= 3:
        return "TD1", 30
    if len(lines) == 2:
        n = max(len(x) for x in lines)
        return ("TD2", 36) if abs(n - 36) < abs(n - 44) and not lines[0].startswith("P") else ("TD3", 44)
    return None


def _names(s: str) -> tuple[str, str]:
    s = s.rstrip("<")
    sur, _, given = s.partition("<<")
    return sur.replace("<", " ").strip(), given.replace("<", " ").strip()


def _date(yymmdd: str, future: bool) -> str | None:
    if not re.fullmatch(r"\d{6}", yymmdd):
        return None
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:])
    now = date.today().year % 100
    year = 2000 + yy if (future or yy <= now) else 1900 + yy
    try:
        return date(year, mm, dd).strftime("%d-%m-%Y")
    except ValueError:
        return None


def _check(value: str, digit: str) -> bool | None:
    if not value or not digit or "<" * len(value) == value and digit == "<":
        return None  # unread (missing filler part) or an empty optional field
    return check_digit(value) == digit


def parse_mrz(text: str) -> dict | None:
    """The first MRZ block in `text` as fields + check-digit results, or None."""
    for g in _groups(_candidates(text)):
        f = _fmt(g)
        if not f:
            continue
        kind, n = f
        ls = [x[:n].ljust(n, "<") for x in g[: 3 if kind == "TD1" else 2]]
        cut = [len(x) for x in g]  # how much of each line was actually read
        if kind == "TD1":
            a, b, c = ls
            num, nd, dob, dd, sex, exp, ed = a[5:14], a[14], b[0:6], b[6], b[7], b[8:14], b[14]
            out = {"format": "TD1 (ID card)", "doc_type": a[0:2].strip("<"), "issuer": a[2:5], "nationality": b[15:18]}
            sur, given = _names(c)
            comp = (a[5:30] + b[0:7] + b[8:15] + b[18:29], b[29]) if cut[1] >= 30 else None
        else:
            a, b = ls
            num, nd, dob, dd, sex, exp, ed = b[0:9], b[9], b[13:19], b[19], b[20], b[21:27], b[27]
            visa = a[0] == "V"  # MRV: the optional data runs to the end of line 2, there is no composite digit
            out = {"format": ("MRV-A (visa)" if n == 44 else "MRV-B (visa)") if visa else "TD3 (passport)" if kind == "TD3" else "TD2",
                   "doc_type": a[0:2].strip("<"), "issuer": a[2:5], "nationality": b[10:13]}
            sur, given = _names(a[5:])
            last = n - 1
            comp = (b[0:10] + b[13:20] + b[21:last], b[last]) if cut[1] >= n and not visa else None
        out.update({"surname": sur, "given_names": given, "number": num.rstrip("<"), "sex": sex.replace("<", "X"),
                    "birth": _date(dob, False), "expiry": _date(exp, True)})
        checks = {"number": _check(num, nd), "birth": _check(dob, dd), "expiry": _check(exp, ed)}
        if comp:
            checks["composite"] = _check(*comp)
        out["checks"] = checks
        out["valid"] = all(v is not False for v in checks.values()) and any(v for v in checks.values())
        out["lines"] = g
        # cross-check with the printed (visual) zone of the same reading (the MRZ lines themselves left out)
        vis = "\n".join(x for x in text.splitlines() if re.sub(r"\s+", "", _TAG.sub("", x)).upper() not in g)
        flat = re.sub(r"\s+", "", vis)
        seen = {}
        if out["number"]:
            seen["number"] = out["number"] in flat
        for k in ("birth", "expiry"):
            if out[k]:
                d, m, y = out[k].split("-")
                mon = _MONTHS[int(m) - 1]
                seen[k] = any(v in flat.upper() for v in (f"{d}-{m}-{y}", f"{d}/{m}/{y}", f"{d}.{m}.{y}", f"{y}-{m}-{d}",
                                                          f"{y}/{m}/{d}", f"{d}{mon}{y}", f"{d}{mon}{y[2:]}"))
        out["printed_match"] = seen
        return out
    return None
