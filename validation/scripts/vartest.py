# -*- coding: utf-8 -*-
"""vartest.py — «авто-размерные» (переменные) шрифты против статических: на каждом размере из диапазона рисунка формы и позиции глифов должны совпадать.
Режимы: --hb (uharfbuzz, быстрый, по всем парам кернинга), --typst (настоящий Typst: opsz = кегль, FeatureVariations, HVAR)."""
import os, sys, re, json, collections, argparse, subprocess, warnings, shutil
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "scripts"))
from paths import *
import cmsfams as F
import build as B
import assemble as A
from fontTools.ttLib import TTFont
import tfmtest as T

BP = 72.0 / 72.27


def var_path(face):
    d = F.all_designs()[face][0]
    nm = B.names_for(face, "var", d)
    return f"{T.OUTROOT}/auto/{nm['ps']}.otf", nm


def sample_sizes(L, layers):
    """внутренние точки диапазона слоя L (в пунктах Typst)"""
    lo, hi = L.rng
    pts = []
    lo_b = max(A.AXIS_MIN, lo * BP) if lo != float("-inf") else A.AXIS_MIN
    hi_b = min(A.AXIS_MAX, hi * BP) if hi != float("inf") else A.AXIS_MAX
    if lo == float("-inf"):
        pts = [A.AXIS_MIN, min(hi_b - 0.02, A.AXIS_MIN + 0.3)]
    elif hi == float("inf"):
        pts = [lo_b + 0.02, (lo_b + A.AXIS_MAX) / 2, A.AXIS_MAX]
    else:
        pts = [lo_b + 0.02, (lo_b + hi_b) / 2, hi_b - 0.02]
    return [round(p, 3) for p in pts if A.AXIS_MIN <= p <= A.AXIS_MAX]


STRIP = re.compile(r"\.d\d+")


def hb_shape(path, text, feats, lang, script, var=None):
    import uharfbuzz as hb
    if not text.strip():
        return []
    face = hb.Face(hb.Blob.from_file_path(path))
    order = TTFont(path).getGlyphOrder()
    ft = hb.Font(face)
    if var:
        ft.set_variations(var)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.language = lang
    buf.script = script
    buf.direction = "ltr"
    hb.shape(ft, buf, feats)
    return [(order[i.codepoint], p.x_advance, p.x_offset, i.cluster) for i, p in zip(buf.glyph_infos, buf.glyph_positions)]


def run_hb(faces):
    bad = 0
    _E = B.cmsmetrics._ENC
    ts1_only = (set(_E["ts1"]) - set(_E["t1"])) - {".notdef"}
    for face in faces:
        pl = B.plan(face, "var")
        if not pl["var"]:
            continue
        vpath, nm = var_path(face)
        if not os.path.exists(vpath):
            print("нет файла", vpath); bad += 1; continue
        cm = TTFont(vpath).getBestCmap()
        chars = sorted(u for u in cm if u >= 0x20 and not (0x2000 <= u <= 0x200F) and u not in (0xA0, 0xAD, 0x202F, 0x205F, 0x2028, 0x2029))
        tot = collections.Counter()
        for L in pl["layers"]:
            spath, snm = T.font_file(F.face_of(L.d["pfb"]), L.d)
            if not os.path.exists(spath):
                print("нет статического", spath); bad += 1; continue
            # тексты: все символы через пробел + пары из таблиц кернинга
            inv = {}
            for u, n in TTFont(spath).getBestCmap().items():
                inv.setdefault(n, u)
            texts = {"chars": " ".join(chr(u) for u in chars)}
            pairs = []
            for tab in ("kern", "kern_L"):
                for (a, b), v in L.m[tab].items():
                    ua, ub = inv.get(a), (0x20 if b == "space" else inv.get(b))
                    if ua and ub and ua >= 0x20 and (ub >= 0x20):
                        pairs.append(chr(ua) + chr(ub) + (" " if b == "space" else "") + "|")
            texts["pairs"] = " ".join(sorted(set(pairs)))
            texts["words"] = "Hamburgefonstiv Съешь ещё этих мягких французских булок fi fl ff ffi ffl AVAWAT To Ty “quotes” „низкие“ «ёлочки» — – ?! !‘ ?‘ № 0123456789"
            for s in sample_sizes(L, pl["layers"]):
                for lang, script in (("en", "Latn"), ("ru", "Cyrl")):
                    # рисунок, который должен выбираться в этом контексте (sans 5–7 pt: в латинском — масштабированный 8 pt)
                    spath_ctx, drop = spath, set()
                    if script == "Latn" and L.suffix in pl["lmap"]:
                        TL = [X for X in pl["layers"] if X.suffix == pl["lmap"][L.suffix]][0]
                        spath_ctx = T.font_file(F.face_of(TL.d["pfb"]), TL.d)[0]
                        drop = {chr(u) for u, n in cm.items() if n in ts1_only}
                    for fname, feats in (("default", {}), ("smcp", {"smcp": True, "c2sc": True}), ("onum", {"onum": True})):
                        if fname == "smcp" and not pl["caps"]:
                            continue
                        if fname == "onum" and drop:
                            continue                # oldstyle-цифры — глифы TS1: в латинском контексте остаются в «своём» рисунке
                        for tname, text in texts.items():
                            if drop:
                                text = "".join(ch for ch in text if ch not in drop)
                            a = hb_shape(vpath, text, feats, lang, script, {"opsz": s})
                            b = hb_shape(spath_ctx, text, feats, lang, script)
                            na = [(STRIP.sub("", g), adv, off) for g, adv, off, cl in a]
                            nb = [(g, adv, off) for g, adv, off, cl in b]
                            tot["cases"] += 1
                            if na != nb:
                                bad += 1; tot["bad"] += 1
                                diffs = [(i, x, y) for i, (x, y) in enumerate(zip(na, nb)) if x != y][:3]
                                print(f"  РАЗЛИЧИЕ {face} opsz={s} слой={L.suffix or 'основной'} ({L.d['ds']}pt) {lang}/{script} {fname}/{tname}: len {len(na)} vs {len(nb)}; {diffs}")
        print(f"[hb] {face:7s} {nm['typo_family']} / {nm['sty']}: слоёв {len(pl['layers'])}, проверок {tot['cases']}, плохих {tot['bad']}", flush=True)
    return bad


def run_typst(faces, work):
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    sample = "Hamburgefonstiv Съешь ещё этих мягких французских булок fi fl ffi AVAWAT To “quotes” „низкие“ «ёлочки» — № 123"
    lines, meta = [], []
    for face in faces:
        pl = B.plan(face, "var")
        if not pl["var"]:
            continue
        grp, sty, wt, it, ob, wd, capsf = F.FACE[face]
        vpath, vnm = var_path(face)
        style = "italic" if it else ("oblique" if ob else "normal")
        stretch = 100 if wd == 5 else 75
        for L in pl["layers"]:
            dface = F.face_of(L.d["pfb"])
            spath, snm = T.font_file(dface, L.d)
            gS, stS, wtS, itS, obS, wdS, _c = F.FACE[dface]
            styleS = "italic" if itS else ("oblique" if obS else "normal")
            stretchS = 100 if wdS == 5 else 75
            for s in sample_sizes(L, pl["layers"]):
                for feat in ("", ', features: (smcp: 1)') if pl["caps"] else ("",):
                    for fam, key, w_, st_, sr_ in ((vnm["typo_family"], "var", wt, style, stretch), (snm["typo_family"], "static", wtS, styleS, stretchS)):
                        lines.append(f'#text(font: "{fam}", size: {s}pt, weight: {w_}, style: "{st_}", stretch: {sr_}%, lang: "ru", fallback: false{feat})[{sample}]')
                        meta.append((face, s, L.d["tok"], key, feat))
    typ = '#set page(width: 8000pt, height: auto, margin: 5pt)\n#set par(leading: 1pt, spacing: 1pt)\n#set text(hyphenate: false)\n' + "\n\n".join(lines)
    open(work + "/t.typ", "w").write(typ)
    cmd = [T.TYPST, "compile", "--ignore-system-fonts", "--font-path", f"{T.OUTROOT}/auto"]
    dirs = {os.path.dirname(T.font_file(f, dd)[0]) for f in faces for dd in F.all_designs()[f]}
    for f in faces:
        if f in F.SUBST:
            sf = F.SUBST[f][0]
            dirs |= {os.path.dirname(T.font_file(sf, dd)[0]) for dd in F.all_designs()[sf]}
    for d in sorted(dirs):
        cmd += ["--font-path", d]
    cmd += [work + "/t.typ", work + "/t.pdf"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        print(r.stderr.decode("utf-8", "replace")[-2000:])
        return 1
    import pdfglyphs
    pages = pdfglyphs.extract(work + "/t.pdf")
    rows = [ln for pg in pages for ln in pg]
    print("[typst] строк в PDF", len(rows), "ожидалось", len(lines))
    bad = 0
    for k in range(0, min(len(rows), len(lines)) - 1, 2):
        a, b = rows[k], rows[k + 1]
        xa = [round(g[0] - a[0][0], 3) for g in a]
        xb = [round(g[0] - b[0][0], 3) for g in b]
        ta = [g[1] for g in a]; tb = [g[1] for g in b]
        if xa != xb or ta != tb:
            bad += 1
            d = [(i, x, y) for i, (x, y) in enumerate(zip(xa, xb)) if abs(x - y) > 0.001][:3]
            print("  РАЗЛИЧИЕ", meta[k], "len", len(xa), len(xb), d)
    print(f"[typst] пар строк {len(rows)//2}, плохих {bad}")
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["hb", "typst"])
    ap.add_argument("faces", nargs="*")
    ap.add_argument("--work", default=HERE + "/work/_var")
    a = ap.parse_args()
    faces = a.faces or sorted(F.FACE)
    sys.exit(1 if (run_hb(faces) if a.mode == "hb" else run_typst(faces, a.work)) else 0)
