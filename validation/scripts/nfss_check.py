# -*- coding: utf-8 -*-
"""nfss_check.py — сверка правил выбора рисунка по размеру (cmsfams.design_ranges) с настоящим LaTeX (nfss2/probe.json)."""
import os, sys, json, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
from paths import *
import cmsfams as F

PF = os.environ.get("PROBE_FILE", "probe.json")
P = json.load(open(HERE + "/nfss2/" + PF))
raw = json.load(open(FULL + "/designs.json"))
rev = {}
for key, tf in raw.items():
    pfb, tok = key.split("|")
    for e, n in tf.items():
        rev[n] = (F.face_of(pfb), tok, key)
ad = F.all_designs()
ds_of = {d["key"]: d["ds"] for f in ad for d in ad[f]}


CAPS_BASE = {F.FACE[f][6]: f for f in F.FACE if F.FACE[f][6]}


def expected_ds(face, s, ctx="L"):
    """рисунок, который выбирает шрифт CM-Super для Typst на размере s (пт TeX); ctx: "L" — T1, "R" — T2A/T2B/T2C/X2/TS1"""
    if face in F.CAPS_ONLY:                      # капитель: рисунок с тем же токеном, что у выбранного рисунка базовой гарнитуры
        base = CAPS_BASE[face]
        d = expected_ds(base, s, ctx)
        return F.caps_design_for(base, d)
    grp, sty, wt, it, ob, wd, capsf = F.FACE[face]
    rule = F.GROUP[grp][3]
    designs = ad[face]
    if face in F.SUBST:                          # Bright Bold < 9 pt берётся из полужирного (sub* в t2acmbr.fd)
        sub_face, below = F.SUBST[face]
        t_lo = max(x for x in F.LISTED if x < below)
        if s <= (t_lo + below) / 2.0:
            return expected_ds(sub_face, s, ctx)
    for dsv, lo, hi in F.design_ranges(rule, designs, ctx):
        if lo < s <= hi:
            d = min(designs, key=lambda x: (abs(x["ds"] - dsv), x["ds"]))
            return d
    raise RuntimeError


def parse(r):
    if r is None or r.startswith("nullfont"):
        return None
    m = re.match(r"(\S+)(?: at ([\d.]+)pt)?$", r)
    return m.group(1), (float(m.group(2)) if m.group(2) else None)


def known_exception(key, face, sv, dkey, ekey):
    """расхождения, которые устроены намеренно (см. README, «Ограничения»)"""
    enc, fam, ser, shp = key.split("/")
    if fam == "lcmtt" and shp == "it" and face == "sfit":
        # lcmtt/m/it = ecit1000 at 13.82 … 41.28: рисунок 10 pt, масштабированный — это шрифт «CM-Super SliTeX Typewriter Italic» (одна форма)
        return "lcmtt/it: рисунок 10 pt масштабируется (отдельный шрифт SliTeX Typewriter Italic)"
    if fam == "ccr" and ser == "bx" and sv > 24.88 + 1.5:
        return "ccr/bx: Roman Bold до 24.88 pt (размеры списка Concrete; помощник привязывает кегль)"
    if fam == "cmsd":
        return "пакет cmsd (t1cmsd.fd): другие правила выбора рисунка; см. README"
    return None


known = collections.Counter()
bad = collections.defaultdict(list)
nchk = 0
unknown = collections.Counter()
listed_by_decl = {}
face_of_decl = {}
for key, res in P.items():
    enc, fam, ser, shp = key.split("/")
    listed = []
    faces = set()
    for s, r in res.items():
        pr = parse(r)
        if pr is None:
            continue
        name, at = pr
        if name not in rev:
            unknown[(key, name)] += 1
            continue
        face, tok, dkey = rev[name]
        faces.add(face)
        dsz = ds_of[dkey]
        at_eff = at if at is not None else dsz
        sv = float(s)
        if abs(at_eff - sv) < 1e-3:
            listed.append(sv)
        # проверка выбора рисунка (кроме точек, лежащих вплотную к границе диапазонов)
        ctx = "L" if enc == "T1" else "R"
        exp = expected_ds(face, sv, ctx)
        nchk += 1
        if exp["key"] != dkey:
            kind = known_exception(key, face, sv, dkey, exp["key"])
            if kind:
                known[kind] += 1
            else:
                bad[key].append((s, name, at, exp["key"]))
    listed_by_decl[key] = sorted(set(listed))
    face_of_decl[key] = sorted(faces)
print("проверено точек:", nchk)
print("известные особенности:", dict(known))
print("неизвестные TFM:", dict(list(unknown.items())[:10]), len(unknown))
for k, v in bad.items():
    print("РАСХОЖДЕНИЕ", k, len(v), v[:6])
json.dump(dict(listed=listed_by_decl, faces=face_of_decl), open(HERE + "/nfss2/listed_" + PF, "w"), indent=0)
print("деклараций:", len(P), "с расхождениями:", len(bad))
