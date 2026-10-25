# -*- coding: utf-8 -*-
"""nfss_detail.py — подробности расхождений nfss_check: диапазоны размеров, где выбор рисунка LaTeX ≠ cmsfams.design_ranges"""
import os, sys, json, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
from paths import *
import cmsfams as F
P = json.load(open(HERE + "/nfss2/probe.json"))
raw = json.load(open(FULL + "/designs.json"))
rev = {}
for key, tf in raw.items():
    pfb, tok = key.split("|")
    for e, n in tf.items():
        rev[n] = (F.face_of(pfb), tok, key)
ad = F.all_designs()
ds_of = {d["key"]: d["ds"] for f in ad for d in ad[f]}
def parse(r):
    if r is None or r.startswith("nullfont"): return None
    m = re.match(r"(\S+)(?: at ([\d.]+)pt)?$", r)
    return m.group(1), (float(m.group(2)) if m.group(2) else None)
def expected(face, s):
    grp = F.FACE[face][0]; rule = F.GROUP[grp][3]
    for dsv, lo, hi in F.design_ranges(rule, ad[face]):
        if lo < s <= hi:
            return min(ad[face], key=lambda x: (abs(x["ds"] - dsv), x["ds"]))
want = sys.argv[1:]
for key, res in P.items():
    if want and not any(w in key for w in want): continue
    rows = []
    for s, r in sorted(res.items(), key=lambda kv: float(kv[0])):
        pr = parse(r)
        if pr is None: rows.append((float(s), "—", None, None)); continue
        name, at = pr
        if name not in rev: rows.append((float(s), name + "?", at, None)); continue
        face, tok, dkey = rev[name]
        e = expected(face, float(s))
        rows.append((float(s), name, at, "ok" if e["key"] == dkey else "MISMATCH→" + e["key"]))
    # свернуть подряд идущие одинаковые
    out = []
    for row in rows:
        k = (row[1], row[2], row[3])
        if out and out[-1][0] == k: out[-1][2] = row[0]
        else: out.append([k, row[0], row[0]])
    print("==", key)
    for k, a, b in out:
        print(f"   {a:g}–{b:g}: {k[0]} at {k[1]} {k[2]}")
