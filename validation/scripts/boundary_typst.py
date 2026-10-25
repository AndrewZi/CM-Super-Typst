# -*- coding: utf-8 -*-
"""boundary_typst.py — то же, что boundary_scan.py, но настоящим Typst: как «авто-размерный» шрифт переключает рисунок у границ.

Для каждой границы между рисунками (середина между соседними размерами списка NFSS) набирается пара одинаковых букв (та, у которой ширина в двух рисунках различается; иначе «НН») кеглем b + k·STEP пт TeX
(k = -N..N) переменным шрифтом и теми же буквами статическими шрифтами нижнего и верхнего рисунков на том же кегле.
По расстоянию между глифами (оно у разных рисунков разное) определяется, какой рисунок выбрал Typst: «нижний», «верхний» или «другой»;
если расстояния у обоих рисунков одинаковы (моноширинные шрифты и т. п.), сравниваются растры строк (1200 dpi, начало первого глифа в одной и той же точке).
Требуется: нижний … нижний, верхний … верхний (один переход, без «другого»), на самой границе — нижний.
Запуск: python3 boundary_typst.py [FACE ...]
"""
import os, sys, subprocess, shutil, warnings, collections
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "scripts"))
from paths import *
import cmsfams as F
import build as B
import assemble as A
import tfmtest as T
import pdfglyphs
import numpy as np
import pymupdf

N = 6
STEP = 0.0006                   # пт TeX (квант оси выше 12 пт = 0,0015 пт Typst)
WORK = HERE + "/work/_bnd"


def probe_text(path_lo, path_up):
    """Буква, ширина которой у нижнего и верхнего рисунков различается (кириллица — раньше латиницы); если такой нет — «Н»."""
    from fontTools.ttLib import TTFont
    a, b = TTFont(path_lo), TTFont(path_up)
    ca, cb = a.getBestCmap(), b.getBestCmap()
    ha, hb = a["hmtx"], b["hmtx"]
    best = None
    for u in list(range(0x410, 0x450)) + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)):
        if u in ca and u in cb:
            d = abs(ha[ca[u]][0] - hb[cb[u]][0]) / a["head"].unitsPerEm
            if d >= 0.004 and (best is None or d > best[0]):
                best = (d, u)
        if best and best[0] >= 0.012:
            break
    ch = chr(best[1]) if best else "\u041d"
    return ch + ch


def styl(face):
    grp, sty, wt, it, ob, wd, capsf = F.FACE[face]
    return wt, ("italic" if it else ("oblique" if ob else "normal")), (100 if wd == 5 else 75)


def main():
    faces = sys.argv[1:] or sorted(F.FACE)
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    lines, meta = [], []
    for face in faces:
        pl = B.plan(face, "var")
        if not pl["var"]:
            continue
        d0 = F.all_designs()[face][0]
        vnm = B.names_for(face, "var", d0)
        layers = sorted(pl["layers"], key=lambda L: L.rng[0])
        for i in range(len(layers) - 1):
            lo, up = layers[i], layers[i + 1]
            b = lo.rng[1]
            fonts = {}
            paths = {}
            for key, L in (("lo", lo), ("up", up)):
                dface = F.face_of(L.d["pfb"])
                spath, snm = T.font_file(dface, L.d)
                paths[key] = spath
                w, s, st = styl(dface)
                fonts[key] = (snm["typo_family"], w, s, st)
            txt = probe_text(paths["lo"], paths["up"])
            w, s, st = styl(face)
            fonts["var"] = (vnm["typo_family"], w, s, st)
            for k in range(-N, N + 1):
                sz = b + k * STEP
                for key in ("var", "lo", "up"):
                    fam, w_, s_, st_ = fonts[key]
                    # после каждой строки — зазор 1,4 кегля: растр строки не должен захватывать соседние (нужно для сравнения по растру)
                    lines.append(f'#text(font: "{fam}", size: {sz * A.TEX2BP:.6f}pt, weight: {w_}, style: "{s_}", stretch: {st_}%, lang: "ru", fallback: false)[{txt}]\n#v({1.4 * sz * A.TEX2BP:.3f}pt)')
                    meta.append((face, b, k, key, lo.d["ds"], up.d["ds"]))
    typ = '#set page(width: 220pt, height: 760pt, margin: 5pt)\n#set par(leading: 0pt, spacing: 1pt)\n#set text(hyphenate: false)\n' + "\n\n".join(lines)
    open(WORK + "/t.typ", "w").write(typ)
    cmd = [T.TYPST, "compile", "--ignore-system-fonts", "--font-path", f"{T.OUTROOT}/auto", "--font-path", f"{T.OUTROOT}/static", WORK + "/t.typ", WORK + "/t.pdf"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        print(r.stderr.decode("utf-8", "replace")[-3000:])
        sys.exit(2)
    pages = pdfglyphs.extract(WORK + "/t.pdf", drop=(), with_y=True)
    rows, where = [], []
    for pi, pg in enumerate(pages):
        for ln in pg:
            rows.append(ln)
            where.append(pi)
    print(f"[typst] строк в PDF {len(rows)}, ожидалось {len(lines)}", flush=True)
    if len(rows) != len(lines):
        sys.exit(2)
    adv = []
    for ln in rows:
        if len(ln) != 2:
            adv.append(None)
        else:
            adv.append(ln[1][0] - ln[0][0])
    doc = pymupdf.open(WORK + "/t.pdf")

    def pixels(idx, size):
        """растр строки: обрезка так, что начало первого глифа попадает в точку (4, 1.0*size) растра ровно; 1200 dpi"""
        ln, pi = rows[idx], where[idx]
        page = doc[pi]
        H = page.mediabox.height
        ox, oy = ln[0][0], H - ln[0][4]
        z = 1200 / 72.0
        w, h = size * 1.9 + 8, size * 1.3
        page.set_cropbox(pymupdf.Rect(ox - 4, oy - size, ox - 4 + w, oy - size + h))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), colorspace=pymupdf.csGRAY, alpha=False)
        page.set_cropbox(page.mediabox)
        return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).astype(np.int32)
    res = collections.OrderedDict()
    idx_of = {}
    for i, ((face, b, k, key, dlo, dup), a) in enumerate(zip(meta, adv)):
        res.setdefault((face, b, dlo, dup), {}).setdefault(k, {})[key] = a
        idx_of[(face, b, k, key)] = i
    tot = collections.Counter()
    per_face = collections.OrderedDict()
    for (face, b, dlo, dup), byk in res.items():
        seq = []
        for k in range(-N, N + 1):
            v = byk[k]
            if v["var"] is None or v["lo"] is None or v["up"] is None:
                seq.append("?")
            elif abs(v["lo"] - v["up"]) < 1e-3:
                # расстояние между глифами у рисунков одинаково (моноширинные, часть Bright/Fibonacci) — сравниваем растры
                i_v, i_l, i_u = (idx_of[(face, b, k, key)] for key in ("var", "lo", "up"))
                sz = (b + k * STEP) * A.TEX2BP
                Av, Al, Au = pixels(i_v, sz), pixels(i_l, sz), pixels(i_u, sz)
                h = min(Av.shape[0], Al.shape[0], Au.shape[0]); wd = min(Av.shape[1], Al.shape[1], Au.shape[1])
                Av, Al, Au = Av[:h, :wd], Al[:h, :wd], Au[:h, :wd]
                d_lu = np.abs(Al - Au).sum()
                if d_lu < 255 * 20:
                    seq.append("=")                        # рисунки неразличимы и по растру
                else:
                    dl, du = np.abs(Av - Al).sum(), np.abs(Av - Au).sum()
                    seq.append("lo" if dl < 0.05 * d_lu else "up" if du < 0.05 * d_lu else "other")
            elif abs(v["var"] - v["lo"]) < 1e-3:
                seq.append("lo")
            elif abs(v["var"] - v["up"]) < 1e-3:
                seq.append("up")
            else:
                seq.append("other")
        tot["boundaries"] += 1
        tot["points"] += len(seq)
        informative = [x for x in seq if x != "="]
        ok = bool(informative) and all(x in ("lo", "up") for x in informative)
        if ok:
            ups = [i for i, x in enumerate(seq) if x == "up"]
            if ups:
                ok = all(x in ("up", "=") for x in seq[ups[0]:])
        tie = seq[N]
        if ok and tie == "up":
            ok = False
        if not informative:
            tot["uninformative"] += 1
        if not ok:
            tot["bad"] += 1
            per_face.setdefault(face, []).append((b, dlo, dup, seq))
        else:
            per_face.setdefault(face, [])
    for face, bad in per_face.items():
        nm = B.names_for(face, "var", F.all_designs()[face][0])
        print(f"[typst-bnd] {face:7s} {nm['typo_family']} / {nm['typo_style']}: плохих границ {len(bad)}  {'OK' if not bad else 'ПЛОХО'}")
        for b, dlo, dup, seq in bad[:5]:
            print("     граница", b, f"{dlo}→{dup}", seq)
    print(f"итого: границ {tot['boundaries']}, точек {tot['points']}, плохих границ {tot['bad']}, границ, где рисунки неразличимы {tot['uninformative']}")
    sys.exit(1 if tot["bad"] else 0)


if __name__ == "__main__":
    main()
