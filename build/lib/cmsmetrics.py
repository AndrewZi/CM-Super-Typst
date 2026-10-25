"""cmsmetrics.py — метрики LaTeX для одного рисунка (дизайн-размера) CM-Super из TFM:
ширины глифов, кернинг, лигатуры, параметры шрифта. Единицы — доли em (кегля дизайна).
Кодировки перебираются по приоритету ENC_PRIORITY; пересечения проверяются (расхождения собираются в conflicts)."""
import os, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))
import tfmlib
from paths import *
import tfmcache

ENC_PRIORITY = ["t2a", "t1", "t2b", "t2c", "x2", "ts1"]       # русский контекст (T2A главнее): ширины, лигатуры, таблица кернинга kern (R)
ENC_PRIORITY_L = ["t1", "ts1", "t2a", "t2b", "t2c", "x2"]     # латинский (английский) контекст: таблица кернинга kern_L и ширины adv_L (T1, затем TS1, главнее T2A)
ENC_PRIORITY_X = ["x2", "t2a", "t1", "t2b", "t2c", "ts1"]     # церковнославянский контекст (язык CHU): таблица kern_X (X2 главнее)
KERN_TABLES = (("kern", "kern_src", ENC_PRIORITY), ("kern_L", "kern_src_L", ENC_PRIORITY_L), ("kern_X", "kern_src_X", ENC_PRIORITY_X))
CYR_ENCS = ("t2a", "t2b", "t2c", "x2")
_ENC = {e: tfmlib.read_enc(f"{ENCDIR}/cm-super-{e}.enc")[1] for e in ("t1", "t2a", "t2b", "t2c", "x2", "ts1")}
EPS = 2.0e-4   # em: допустимое расхождение ширины одного и того же глифа в разных кодировках


def derive_lig_kerns(m, kname="kern", sname="kern_src"):
    """Порядок TeX: кёрн перед лигатурой берётся по ПЕРВОМУ компоненту лигатуры (пара (A, B) разбирается до того, как B+C станет лигатурой X),
    а в OpenType GPOS работает уже после GSUB, то есть видит пару (A, X). Поэтому для каждой лигатуры X добавляем пару (A, X) = кёрн (A, первый компонент X).
    Явная пара (A, X) из TFM (X набран напрямую, а не собран лигатурой) сохраняется, если выведенной нет."""
    kern = m[kname]
    m.setdefault("kderived", 0)
    m.setdefault("kamb", [])
    lefts_by_src = []
    for src in ("lig", "lig_cyr"):
        left = collections.defaultdict(set)
        for (a, b), c in m[src].items():
            if c in (a, b) or c == ".notdef":
                continue
            left[c].add(a)
        lefts_by_src.append(left)
    firsts_memo = {}

    def first(left, g, depth=0):
        key = (id(left), g)
        if key in firsts_memo:
            return firsts_memo[key]
        if depth < 6 and g in left:
            res = set()
            for a in left[g]:
                res |= first(left, a, depth + 1)
        else:
            res = {g}
        firsts_memo[key] = res
        return res
    by_second = collections.defaultdict(dict)       # b -> {a: kern}
    for (a, b), v in kern.items():
        by_second[b][a] = v
    new = {}
    for left in lefts_by_src:
        for X in left:
            fs = first(left, X) - {X}
            if not fs:
                continue
            cands = collections.defaultdict(list)
            for f in fs:
                for a, v in by_second.get(f, {}).items():
                    cands[a].append((f, v))
            for a, lst in cands.items():
                if len(lst) != len(fs) or max(v for f, v in lst) - min(v for f, v in lst) > EPS:
                    m["kamb"].append((a, X, lst))
                    continue
                v = lst[0][1]
                old = kern.get((a, X))
                if old is not None and abs(old - v) > EPS:
                    m["kconflicts"].append(((a, X), "derived", v, "tfm", old))
                new[(a, X)] = v
    for key, v in new.items():
        kern[key] = v
        m[sname][key] = "derived"
        m["kderived"] += 1


def design_metrics(tfms):
    """tfms: {enc: имя TFM} -> словарь метрик"""
    cache = tfmcache.load()
    m = {"adv": {}, "adv_src": {}, "adv_L": {}, "wvar": {}, "kern": {}, "kern_src": {}, "kern_L": {}, "kern_src_L": {}, "kern_X": {}, "kern_src_X": {}, "lig": {}, "lig_cyr": {}, "conflicts": [],
         "kconflicts": [], "other_ops": collections.Counter()}
    ds = None
    per = {}
    for enc in ENC_PRIORITY:
        if enc not in tfms:
            continue
        t = cache[tfms[enc]]
        names = _ENC[enc]
        ds = ds or t["designsize"]
        if abs(t["designsize"] - ds) > 1e-6:
            m["conflicts"].append(("designsize", enc, t["designsize"], ds))
        if enc == "t2a" or ("fontdimen" not in m):
            m["fontdimen"] = t["fontdimen"]
        glyphs = set()
        for code, d in t["chars"].items():
            nm = names[code]
            if nm == ".notdef":
                continue
            glyphs.add(nm)
            w = d.get("wd", 0.0)
            if nm in m["adv"]:
                if abs(m["adv"][nm] - w) > EPS:
                    m["conflicts"].append((nm, enc, w, m["adv_src"][nm], m["adv"][nm]))
            else:
                m["adv"][nm] = w
                m["adv_src"][nm] = enc
        per[enc] = dict(t=t, names=names, glyphs=glyphs)
        for (a, b), v in t["pairs"].items():
            la, lb = names[a], names[b]
            if la == ".notdef" or lb == ".notdef" or v[0] == "KRN":
                continue
            if v[1] != "LIG":
                m["other_ops"][v[1]] += 1
                continue
            res = names[v[2]]
            if res == ".notdef":
                continue            # лигатура на несуществующий знак (TS1 «Funny»): в шрифт не переносим
            tgt = m["lig_cyr"] if enc in CYR_ENCS else m["lig"]
            tgt.setdefault((la, lb), res)
    # ширины в латинском контексте (метрики T1/TS1 главнее T2A); глифы, у которых они отличаются, получают в шрифте двойника «имя.lat»
    for enc in ENC_PRIORITY_L:
        if enc not in per:
            continue
        t, names = per[enc]["t"], per[enc]["names"]
        for code, d in t["chars"].items():
            nm = names[code]
            if nm != ".notdef" and nm not in m["adv_L"]:
                m["adv_L"][nm] = d.get("wd", 0.0)
    for nm, w in m["adv_L"].items():
        if abs(w - m["adv"][nm]) > EPS:
            m["wvar"][nm] = w
    # таблицы кернинга: для каждой пары глифов «главной» считается первая по приоритету кодировка, где есть ОБА глифа
    # (как в LaTeX: пара набирается шрифтом текущей кодировки; нет пары в её TFM — нет и кернинга)
    for kname, sname, order in KERN_TABLES:
        kern, src = m[kname], m[sname]
        seen = []
        for enc in order:
            if enc not in per:
                continue
            P = per[enc]
            t, names, G = P["t"], P["names"], P["glyphs"]
            bc = t.get("boundary")
            for (a, b), v in t["pairs"].items():
                if v[0] != "KRN":
                    continue
                la, lb = names[a], names[b]
                if la == ".notdef":
                    continue
                if bc is not None and b == bc and a != bc:
                    # правая граница слова (BOUNDARYCHAR): TeX применяет этот кёрн в конце слова — перед пробелом
                    key = (la, "space")
                    if not any(la in G2 for e2, G2 in seen):
                        if key in kern:
                            if abs(kern[key] - v[1]) > EPS:
                                m["kconflicts"].append((key, enc, v[1], src[key], kern[key]))
                        else:
                            kern[key] = v[1]
                            src[key] = enc + "/boundary"
                if lb == ".notdef":
                    continue
                key = (la, lb)
                if any(la in G2 and lb in G2 for e2, G2 in seen):
                    continue
                if key in kern:
                    if abs(kern[key] - v[1]) > EPS:
                        m["kconflicts"].append((key, enc, v[1], src[key], kern[key]))
                else:
                    kern[key] = v[1]
                    src[key] = enc
            seen.append((enc, G))
    m["designsize"] = ds
    for kname, sname, order in KERN_TABLES:
        derive_lig_kerns(m, kname, sname)
    m["kderived"] = sum(1 for v in m["kern_src"].values() if v == "derived")
    fd = m["fontdimen"]
    m["space"], m["stretch"], m["shrink"] = fd["SPACE"], fd["STRETCH"], fd["SHRINK"]
    m["quad"], m["xheight"] = fd["QUAD"], fd["XHEIGHT"]
    return m


if __name__ == "__main__":
    import json
    designs = json.load(open(FULL + "/designs.json"))
    k = sys.argv[1] if len(sys.argv) > 1 else "sfrm1200|1200"
    m = design_metrics(designs[k])
    print(k, "ds", m["designsize"], "space", m["space"], "quad", m["quad"], "adv", len(m["adv"]), "kern", len(m["kern"]), "kern_L", len(m["kern_L"]),
          "lig", len(m["lig"]), "lig_cyr", len(m["lig_cyr"]), "conflicts", len(m["conflicts"]), "kconf", len(m["kconflicts"]), dict(m["other_ops"]))
    for c in m["conflicts"][:10]: print("  adv conflict", c)
    for c in m["kconflicts"][:10]: print("  kern conflict", c)
