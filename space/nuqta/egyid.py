"""Egyptian national ID card (بطاقة تحقيق الشخصية) reading -> fields (2026-10-14).

The card prints no field labels: the front is header, first name, the rest of the name, address lines, (birth date),
the 14-digit national number and the card serial; the back is the national number, the issue month, profession lines,
sex, religion, marital status and «البطاقة سارية حتى <expiry>». Fields are taken by line position and shape.

The national number is self-describing: digit 1 the century (2 = 19xx, 3 = 20xx), 2-7 the birth date YYMMDD, 8-9 the
governorate of birth, 13 odd for a man, even for a woman. `nid_info` decodes it; the decoded birth date / sex /
governorate cross-check the printed values (a misread digit rarely keeps them consistent; the address is where the
holder lives now, so a different governorate is no error).
"""
import re
from datetime import date

_AI = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_TO_AI = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
GOV = {"01": "القاهرة", "02": "الإسكندرية", "03": "بورسعيد", "04": "السويس", "11": "دمياط", "12": "الدقهلية",
       "13": "الشرقية", "14": "القليوبية", "15": "كفر الشيخ", "16": "الغربية", "17": "المنوفية", "18": "البحيرة",
       "19": "الإسماعيلية", "21": "الجيزة", "22": "بني سويف", "23": "الفيوم", "24": "المنيا", "25": "أسيوط",
       "26": "سوهاج", "27": "قنا", "28": "أسوان", "29": "الأقصر", "31": "البحر الأحمر", "32": "الوادي الجديد",
       "33": "مطروح", "34": "شمال سيناء", "35": "جنوب سيناء", "88": "خارج الجمهورية"}
# spellings on cards / in addresses that differ from GOV («اسكندرية», «الاسماعيلية», «بنى سويف», ...)
_GOV_KEYS = {g: {re.sub("[أإآ]", "ا", g).replace("ى", "ي"), re.sub("^ال", "", re.sub("[أإآ]", "ا", g)).replace("ى", "ي")}
             for g in GOV.values()}
_HEAD = re.compile(r"جمهورية\s+مصر\s+العربية|بطاقة\s+تحقيق\s+الشخصية")
_NID = re.compile(r"(?<![\d٠-٩])[23٢٣](?:\s?[\d٠-٩]){13}(?![\d٠-٩])")
_DATE = re.compile(r"[\d٠-٩]{4}\s*/\s*[\d٠-٩]{1,2}(?:\s*/\s*[\d٠-٩]{1,2})?")
_SEX = {"ذكر", "أنثى", "انثى", "انثي"}
_RELIGION = re.compile(r"^(?:مسلم|مسلمة|مسلمه|مسيحي|مسيحى|مسيحية|مسيحيه|يهودي|يهودى)$")
_MARITAL = re.compile(r"^(?:أعزب|اعزب|عزباء|آنسة|انسة|آنسه|انسه|متزوج|متزوجة|متزوجه|مطلق|مطلقة|مطلقه|أرمل|ارمل|أرملة|ارملة|ارمله)$")
_SERIAL = re.compile(r"^[A-Z]{1,3}\s?[\d٠-٩]{6,8}$|^[\d٠-٩]{8}[\d٠-٩A-Z]?$")


def looks_egyptian(text: str) -> bool:
    return bool(_HEAD.search(text) or ("سارية حتى" in text and _NID.search(text)))


def nid_info(nid: str) -> dict | None:
    """Decode a 14-digit national number; None when it cannot be one (bad century / date / governorate)."""
    d = re.sub(r"\D", "", nid.translate(_AI))
    if len(d) != 14 or d[0] not in "23":
        return None
    try:
        dob = date((1900 if d[0] == "2" else 2000) + int(d[1:3]), int(d[3:5]), int(d[5:7]))
    except ValueError:
        return None
    if d[7:9] not in GOV:
        return None
    return {"dob": dob, "gov": GOV[d[7:9]], "sex": "ذكر" if int(d[12]) % 2 else "أنثى"}


def _date(v: str):
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", re.sub(r"\s", "", v.translate(_AI)))
    try:
        return date(int(m[1]), int(m[2]), int(m[3])) if m else None
    except ValueError:
        return None


def gov_in(gov: str, text: str) -> bool:
    t = re.sub("[أإآ]", "ا", text).replace("ى", "ي")
    return any(k in t for k in _GOV_KEYS.get(gov, ()))


def parse(text: str) -> dict:
    """Fields of an Egyptian ID front or back reading; {} when it is not one."""
    if not looks_egyptian(text):
        return {}
    lines = [re.sub(r"\*\*|</?t[dhr]>|^#+\s*", "", x).strip() for x in text.split("\n")]
    lines = [x for x in lines if x and not re.fullmatch(r"<img>.*?</img>|image here", x) and not _HEAD.fullmatch(x)]
    f: dict[str, str] = {}
    words, addr = [], []
    back = any("سارية حتى" in x for x in lines) or any(x in _SEX or _RELIGION.match(x) for x in lines)
    for x in lines:
        if _HEAD.search(x):
            continue
        m = _NID.search(x)
        if m and "nid" not in f:
            f["nid"] = m.group(0)
            continue
        if "سارية حتى" in x:
            d = _DATE.search(x)
            if d:
                f["doe"] = d.group(0)
            else:
                f["_doe_next"] = "1"
            continue
        d = _DATE.fullmatch(x)
        if d:
            if f.pop("_doe_next", None):
                f["doe"] = x
            elif back and x.count("/") + x.count("／") == 1:
                f.setdefault("doi", x)  # the back prints the issue month «٢٠١٥/١١»
            elif not back:
                # newer fronts print the expiry too («٢٠٣٠/٠٢»): a date after the card could have been issued
                y = int(re.sub(r"\D", "", x.translate(_AI))[:4])
                f.setdefault("doe" if y > 2010 or x.count("/") == 1 else "dob", x)
            else:
                f.setdefault("doe" if "doi" in f else "doi", x)
            continue
        if _SERIAL.match(x) and "nid" in f and not back:
            f.setdefault("no", x)
            continue
        if x in _SEX:
            f["sex"] = x
            continue
        if _RELIGION.match(x):
            f["religion"] = x
            continue
        if _MARITAL.match(x):
            f["marital"] = x
            continue
        if re.fullmatch(r"[\d٠-٩]{1,2}", x):  # husband's name line / card copy number «١»
            continue
        if re.search("[ء-ي]", x):
            (words if back else (words if len(words) < 2 and "nid" not in f and not addr else addr)).append(x)
    f.pop("_doe_next", None)
    if back:
        if words:
            f["prof"] = " ".join(words)
    else:
        if words:
            f["name"] = " ".join(words)
        if addr:
            f["address"] = " ".join(addr)
        f.setdefault("nat", "مصري")
    return f


def check(f: dict, conf: dict) -> None:
    """Cross-check / fill from the national number: birth date, sex, governorate of birth (front address)."""
    info = nid_info(f.get("nid", ""))
    if not f.get("nid"):
        return
    if not info:
        conf["nid"] = "check"  # cannot be a national number: a digit is misread
        return
    ok = True
    if f.get("dob"):
        ok &= _date(f["dob"]) == info["dob"]
    else:
        f["dob"] = info["dob"].strftime("%Y/%m/%d").translate(_TO_AI)
        conf["dob"] = "nid"
    if not f.get("pob"):
        f["pob"], conf["pob"] = info["gov"], "nid"  # governorate of birth
    if f.get("sex"):
        ok &= (f["sex"] == "ذكر") == (info["sex"] == "ذكر")
    else:
        f["sex"], conf["sex"] = info["sex"], "nid"
    # the governorate of birth is often the address one too, but people move: agreement is evidence, not a rule
    conf["nid"] = ("verified" if conf.get("dob") != "nid" or gov_in(info["gov"], f.get("address", "")) else "agreed") if ok else "check"
