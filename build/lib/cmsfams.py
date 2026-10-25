"""cmsfams.py — таблица гарнитур CM-Super → семейства Typst, правила выбора рисунка по размеру (как в NFSS LaTeX).

Терминология:
  face   — «гарнитура Type 1» CM-Super (префикс .pfb без цифр: sfrm, sfti, sfbmr …);
  design — один рисунок (файл .pfb + набор TFM) для одного дизайн-размера; ключ из designs.json вида "sfrm1200|1200";
  group  — семейство Typst («CM-Super», «CM-Super Sans» …), в которое входит несколько face (Regular, Italic, Bold …).
"""
import os, re, json, sys
sys.path.insert(0, os.path.dirname(__file__))
from paths import *
import tfmcache

TEXPT_TO_BP = 72.0 / 72.27          # 1 pt TeX = 0.996264 pt Typst/PDF
LISTED = [5, 6, 7, 8, 9, 10, 10.95, 12, 14.4, 17.28, 20.74, 24.88, 29.86, 35.83]   # размеры из .fd LaTeX

# face -> (group, style label, weight, italic, oblique, width class, caps face)
#   width class: 5 = normal, 3 = condensed
FACE = {
    # --- основное семейство «CM-Super» (Computer Modern Roman)
    "sfrm": ("R", "Regular", 400, 0, 0, 5, "sfcc"),
    "sfti": ("R", "Italic", 400, 1, 0, 5, None),
    "sfsl": ("R", "Slanted", 400, 0, 1, 5, "sfsc"),
    "sfbx": ("R", "Bold", 700, 0, 0, 5, "sfxc"),
    "sfbi": ("R", "Bold Italic", 700, 1, 0, 5, None),
    "sfbl": ("R", "Bold Slanted", 700, 0, 1, 5, "sfoc"),
    "sfrb": ("R", "Semibold", 600, 0, 0, 5, None),
    # --- отдельные семейства на основе Roman
    "sfui": ("UP", "Regular", 400, 0, 0, 5, None),
    "sfci": ("CL", "Italic", 400, 1, 0, 5, None),
    "sfdh": ("DH", "Regular", 400, 0, 0, 5, None),
    "sfbm": ("VAR", "Bold", 700, 0, 0, 5, None),
    # --- Sans
    "sfss": ("SS", "Regular", 400, 0, 0, 5, None),
    "sfsi": ("SS", "Slanted", 400, 0, 1, 5, None),
    "sfsx": ("SS", "Bold", 700, 0, 0, 5, None),
    "sfso": ("SS", "Bold Slanted", 700, 0, 1, 5, None),
    "sfssdc": ("SS", "Semibold Condensed", 600, 0, 0, 3, None),
    # --- Typewriter
    "sftt": ("TT", "Regular", 400, 0, 0, 5, "sftc"),
    "sfit": ("TT", "Italic", 400, 1, 0, 5, None),
    "sfst": ("TT", "Slanted", 400, 0, 1, 5, None),
    "sfvt": ("VT", "Regular", 400, 0, 0, 5, None),
    "sfvi": ("VT", "Italic", 400, 1, 0, 5, None),
    # --- Fibonacci, Funny
    "sffb": ("FB", "Regular", 400, 0, 0, 5, None),
    "sffs": ("FB", "Slanted", 400, 0, 1, 5, None),
    "sfff": ("FF", "Regular", 400, 0, 0, 5, None),
    "sffi": ("FF", "Italic", 400, 1, 0, 5, None),
    # --- Concrete
    "sform": ("CC", "Regular", 400, 0, 0, 5, "sfocc"),
    "sfosl": ("CC", "Slanted", 400, 0, 1, 5, None),
    "sfoti": ("CC", "Italic", 400, 1, 0, 5, None),
    # --- Bright
    "sfbmr": ("BR", "Regular", 400, 0, 0, 5, None),
    "sfbmo": ("BR", "Slanted", 400, 0, 1, 5, None),
    "sfbsr": ("BR", "Semibold", 600, 0, 0, 5, None),
    "sfbso": ("BR", "Semibold Slanted", 600, 0, 1, 5, None),
    "sfbbx": ("BR", "Bold", 700, 0, 0, 5, None),
    "sfbtl": ("BT", "Light", 300, 0, 0, 5, None),
    "sfbto": ("BT", "Light Slanted", 300, 0, 1, 5, None),
    # --- Sans Quotation, SliTeX
    "sfsq": ("SQ", "Regular", 400, 0, 0, 5, None),
    "sfqi": ("SQ", "Slanted", 400, 0, 1, 5, None),
    "sflq": ("SL", "Regular", 400, 0, 0, 5, None),
    "sfli": ("SL", "Slanted", 400, 0, 1, 5, None),
    "sflb": ("SL", "Bold", 700, 0, 0, 5, None),
    "sflo": ("SL", "Bold Slanted", 700, 0, 1, 5, None),
    "sfltt": ("SLT", "Regular", 400, 0, 0, 5, None),
    "sflti": ("SLT", "Italic", 400, 1, 0, 5, None),          # псевдоним: рисунок sfit1000 (lcmtt/m/it в t1lcmtt.fd: ecit1000 at 13.82pt …)
    "isflq": ("ISL", "Regular", 400, 0, 0, 5, None),
    "isfli": ("ISL", "Slanted", 400, 0, 1, 5, None),
    "isflb": ("ISL", "Bold", 700, 0, 0, 5, None),
    "isflo": ("ISL", "Bold Slanted", 700, 0, 1, 5, None),
    "isfltt": ("ISLT", "Regular", 400, 0, 0, 5, None),
}
# подмена рисунка по размеру (sub* в .fd): в t2acmbr.fd жирный Bright на размерах < 9 pt берётся из полужирного (cmbr/sb/n)
#   face -> (face-замена, размеры строго меньше этого значения берутся из замены)
SUBST = {"sfbbx": ("sfbsr", 9)}
# псевдонимы: «виртуальная» гарнитура берёт один рисунок (токен) настоящей гарнитуры
#   t1lcmtt.fd: lcmtt/m/it = ecit1000 (рисунок 10 pt), масштабированный до размеров SliTeX 13.82 … 41.28 pt
ALIAS = {"sflti": ("sfit", "1000")}
# faces, которые используются только как «капитель» (глифы .cc) других faces
CAPS_ONLY = {"sfcc", "sfsc", "sfxc", "sfoc", "sftc", "sfocc"}

# group -> (имя семейства, PS-префикс, вид, правило размеров, моноширинный)
GROUP = {
    "R": ("CM-Super", "CMSuper", "serif", "std", 0),
    "UP": ("CM-Super Upright", "CMSuperUpright", "serif", "std", 0),
    "CL": ("CM-Super Classical", "CMSuperClassical", "serif", "std", 0),
    "DH": ("CM-Super Dunhill", "CMSuperDunhill", "serif", "std", 0),
    "VAR": ("CM-Super Variant", "CMSuperVariant", "serif", "std", 0),
    "SS": ("CM-Super Sans", "CMSuperSans", "sans", "ss", 0),
    "TT": ("CM-Super Typewriter", "CMSuperTypewriter", "mono", "tt", 1),
    "VT": ("CM-Super Typewriter Proportional", "CMSuperTypewriterProportional", "sans", "tt", 0),
    "FB": ("CM-Super Fibonacci", "CMSuperFibonacci", "serif", "std", 0),
    "FF": ("CM-Super Funny", "CMSuperFunny", "serif", "std", 0),
    "CC": ("CM-Super Concrete", "CMSuperConcrete", "serif", "concrete", 0),
    "BR": ("CM-Super Bright", "CMSuperBright", "sans", "bright", 0),
    "BT": ("CM-Super Bright Typewriter", "CMSuperBrightTypewriter", "mono", "bright", 1),
    "SQ": ("CM-Super Sans Quotation", "CMSuperSansQuotation", "sans", "single", 0),
    "SL": ("CM-Super SliTeX", "CMSuperSliTeX", "sans", "single", 0),
    "SLT": ("CM-Super SliTeX Typewriter", "CMSuperSliTeXTypewriter", "mono", "single", 1),
    "ISL": ("CM-Super SliTeX Invisible", "CMSuperSliTeXInvisible", "sans", "single", 0),
    "ISLT": ("CM-Super SliTeX Typewriter Invisible", "CMSuperSliTeXTypewriterInvisible", "mono", "single", 1),
}


def face_of(pfb):
    return re.sub(r"\d+$", "", pfb)


def size_label(ds):
    s = f"{ds:.2f}".rstrip("0").rstrip(".")
    return s


_designs = None


def all_designs():
    """{face: [dict(key, pfb, tok, tfms, ds)] отсортировано по ds}"""
    global _designs
    if _designs is None:
        raw = json.load(open(FULL + "/designs.json"))
        cache = tfmcache.load()
        out = {}
        for key, tf in raw.items():
            pfb, tok = key.split("|")
            ds = None
            for e in ("t1", "t2a", "t2b", "t2c", "x2", "ts1"):
                if e in tf:
                    ds = cache[tf[e]]["designsize"]
                    break
            out.setdefault(face_of(pfb), []).append(dict(key=key, pfb=pfb, tok=tok, tfms=tf, ds=ds))
        for f in out:
            out[f].sort(key=lambda d: (d["ds"], d["key"]))
        for a, (base, tok) in ALIAS.items():
            out[a] = [dict(d) for d in out[base] if d["tok"] == tok]
            assert len(out[a]) == 1, (a, base, tok)
        _designs = out
    return _designs


def listed_to_design(group_rule, listed, designs, ctx="L"):
    """Какой design (по ds) берёт NFSS для 'listed' размера.
    ctx: "L" — латинская кодировка T1 (английский текст), "R" — кириллические кодировки T2A/T2B/T2C/X2 и TS1.
    Различаются только sans-serif (cmss): в T1 для 5–8 pt берётся масштабированный рисунок 8 pt (ecss0800), а в T2A/T2B/T2C/X2/TS1 —
    собственные рисунки 5, 6, 7 pt (lass0500 …); см. t1cmss.fd и t2acmss.fd."""
    avail = sorted({d["ds"] for d in designs})
    if group_rule == "single":
        return avail[0]
    if group_rule == "ss":
        group_rule = "tt" if ctx == "L" else "std"
    if group_rule == "tt" and listed <= 8:
        want = 8
    elif group_rule == "bright":
        want = 8 if listed <= 8 else 9 if listed == 9 else 10 if listed <= 14.4 else 17.28
    elif group_rule == "concrete":
        want = min(listed, 10)
    else:
        want = listed
    return min(avail, key=lambda a: (abs(a - want), a))


def design_ranges(group_rule, designs, ctx="L"):
    """Диапазоны размера (pt TeX) -> ds рисунка. Возвращает [(ds, lo, hi)], lo/hi включительно сверху (lo<x<=hi),
    крайние -inf/+inf. Правило NFSS: ближайший из LISTED размеров (при равенстве — меньший). ctx — см. listed_to_design."""
    mids = [(LISTED[i] + LISTED[i + 1]) / 2 for i in range(len(LISTED) - 1)]
    per = [listed_to_design(group_rule, s, designs, ctx) for s in LISTED]
    out = []
    lo = float("-inf")
    for i, s in enumerate(LISTED):
        hi = mids[i] if i < len(mids) else float("inf")
        if out and out[-1][0] == per[i]:
            out[-1] = (per[i], out[-1][1], hi)
        else:
            out.append((per[i], lo, hi))
        lo = hi
    return out


def context_split(group_rule, designs):
    """(ranges_primary, remap): ranges_primary — диапазоны для кириллического контекста (самый детальный набор рисунков),
    remap — {ds кириллического рисунка: ds рисунка для латинского контекста} там, где они различаются."""
    if group_rule != "ss":
        return design_ranges(group_rule, designs), {}
    R = design_ranges(group_rule, designs, "R")
    Lr = design_ranges(group_rule, designs, "L")
    remap = {}
    for dsR, lo, hi in R:
        pts = [x for x in (lo, hi) if abs(x) != float("inf")]
        probe = (sum(pts) / len(pts)) if len(pts) == 2 else (hi - 0.01 if lo == float("-inf") else lo + 0.01)
        dsL = [d for d, l2, h2 in Lr if l2 < probe <= h2][0]
        # диапазон R должен целиком лежать в одном диапазоне L
        assert any(l2 <= lo and hi <= h2 for d, l2, h2 in Lr), (dsR, lo, hi)
        if dsL != dsR:
            remap[dsR] = dsL
    return R, remap


def caps_design_for(face, d):
    """design капители для рисунка d (по токену, иначе ближайший по ds)"""
    cf = FACE[face][6]
    if not cf:
        return None
    cds = all_designs()[cf]
    same = [c for c in cds if c["tok"] == d["tok"]]
    if same:
        return same[0]
    return min(cds, key=lambda c: (abs(c["ds"] - d["ds"]), c["ds"]))


if __name__ == "__main__":
    ad = all_designs()
    for f in sorted(ad):
        info = FACE.get(f)
        print(f, info[:2] if info else ("CAPS" if f in CAPS_ONLY else "??"), [(d["tok"], d["ds"]) for d in ad[f]])
    missing = [f for f in ad if f not in FACE and f not in CAPS_ONLY]
    print("не описаны:", missing)
    for g, (fam, ps, kind, rule, mono) in GROUP.items():
        faces = [f for f in FACE if FACE[f][0] == g]
        ds = [d for f in faces[:1] for d in ad[f]]
        print(g, fam, rule, [(round(a, 2), None if lo == float("-inf") else lo, None if hi == float("inf") else hi) for a, lo, hi in design_ranges(rule, ds)])
