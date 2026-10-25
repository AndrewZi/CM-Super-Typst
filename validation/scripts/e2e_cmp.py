# -*- coding: utf-8 -*-
"""e2e_cmp.py — сравнение результатов e2e.py: python3 e2e_cmp.py [class ...] [-v]"""
import os, sys, json, collections, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import e2e
W = e2e.W
TOL = 0.0025


def one(cls, verbose=False):
    G = json.load(open(f"{W}/c{cls}_glyphs.json"))
    L = json.load(open(f"{W}/c{cls}_lines.json"))
    lat, typ = G["lat"], G["typ"]
    assert len(lat) == len(typ) == len(L), (len(lat), len(typ), len(L))
    stat = collections.Counter()
    bad = []
    unavailable = []
    maxstep = 0.0
    by_style = collections.defaultdict(lambda: collections.Counter())
    for ln, a, b in zip(L, lat, typ):
        key = ln["style"]
        if not a:
            stat["latex-unavailable"] += 1
            unavailable.append(ln)
            by_style[key]["unavail"] += 1
            continue
        if len(a) != len(b):
            stat["count"] += 1
            bad.append((ln, "count", len(a), len(b)))
            by_style[key]["bad"] += 1
            continue
        worst, wj = 0.0, -1
        sz_bad = 0
        face_bad = []
        for j in range(len(a)):
            fa, fb = a[j][4], b[j][4]
            if abs(fa - fb) > 1e-3 * max(fa, fb):
                sz_bad += 1
            la, tb = e2e.latex_face(a[j][2]), e2e.typst_face(b[j][2])
            if la != tb and not (tb in e2e.F.SUBST and e2e.F.SUBST[tb][0] == la) and not (tb in e2e.F.ALIAS and e2e.F.ALIAS[tb][0] == la):
                face_bad.append((la, tb))
            if j + 1 < len(a):
                da = a[j + 1][0] - a[j][0]
                db = b[j + 1][0] - b[j][0]
                d = abs(da - db) / max(fa, fb)
                if d > worst:
                    worst, wj = d, j
        maxstep = max(maxstep, worst)
        ok = True
        why = []
        if worst > TOL:
            ok = False
            why.append(("step", round(worst, 5), wj))
        if sz_bad:
            ok = False
            why.append(("size", sz_bad, round(a[0][4] / e2e.BP, 3), round(b[0][4] / e2e.BP, 3)))
        if face_bad:
            ok = False
            why.append(("face", collections.Counter(face_bad).most_common(3)))
        if ok:
            stat["ok"] += 1
            by_style[key]["ok"] += 1
        else:
            stat["bad"] += 1
            by_style[key]["bad"] += 1
            bad.append((ln, why))
    print(f"класс {cls}: {dict(stat)} maxstep={maxstep:.5f} em")
    if verbose or bad:
        for item in bad[:60]:
            ln = item[0]
            print("   BAD", ln["id"], ln["ctx"], repr(ln["style"]), ln["size"], ln["text"], item[1:])
        if len(bad) > 60:
            print("   ...", len(bad) - 60, "ещё")
    if verbose:
        for ln in unavailable[:80]:
            print("   N/A", ln["id"], ln["ctx"], repr(ln["style"]), ln["size"])
    return stat, maxstep, bad, unavailable


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    v = "-v" in sys.argv
    for c in [int(x) for x in args] or [12]:
        one(c, v)
