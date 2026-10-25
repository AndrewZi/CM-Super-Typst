# -*- coding: utf-8 -*-
"""outlines_check.py — контуры всех глифов всех шрифтов пакета == контуры исходных .pfb CM-Super.

Для каждого файла (fonts/auto/*.otf — все слои рисунков и капители; fonts/static/<размер>/*.otf — каждый рисунок) для каждого глифа определяется слой
(по суффиксу имени: «.dTOK» — рисунок, «.cc» / «.cc.dTOK» — капитель, без суффикса — основной рисунок) и исходный глиф того .pfb, из которого слой построен
(двойники «имя.ts1», «имя.cyr», «имя.alt» … берутся с того же глифа), и сравниваются команды контура и координаты всех точек.
Единица em в OpenType-шрифтах — 2000, у Type 1 — 1000, поэтому координаты .pfb удваиваются. Допуск — ноль: контуры совпадают точка в точку.
Исключения: многоточие LaTeX (собирается заново из трёх точек с кернами из TFM) и пустые служебные глифы; они перечисляются в итоге отдельно.
Запуск: python3 outlines_check.py [FACE ...]      Код возврата 1, если есть расхождения.
"""
import os, sys, collections, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "scripts"))
from paths import *
import cmsfams as F
import build as B
import tfmtest as T
from fontTools.t1Lib import T1Font
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

SYNTH = {"ellipsis"}            # собирается из точек заново (см. spec["synth"] в ffmaster.py)
_pfb_cache = {}


def load_pfb(pfb):
    """глифы Type 1 (как T1Font.parse, но шрифты без Subrs — «невидимый» SliTeX — тоже читаются)"""
    if pfb in _pfb_cache:
        return _pfb_cache[pfb]
    from fontTools.misc import psLib, psCharStrings, eexec
    t1 = T1Font(PFBDIR + "/" + pfb + ".pfb")
    font = psLib.suckfont(t1.data, t1.encoding)
    cs = font["CharStrings"]
    lenIV = font["Private"].get("lenIV", 4)
    subrs = font["Private"].get("Subrs", [])
    for g, s in cs.items():
        s, _ = eexec.decrypt(s, 4330)
        cs[g] = psCharStrings.T1CharString(s[lenIV:], subrs=subrs)
    for i in range(len(subrs)):
        s, _ = eexec.decrypt(subrs[i], 4330)
        subrs[i] = psCharStrings.T1CharString(s[lenIV:], subrs=subrs)
    if len(_pfb_cache) > 40:
        _pfb_cache.clear()
    _pfb_cache[pfb] = cs
    return cs


def draw(gs, n):
    """команды контура; незамкнутый контур Type 1 (endPath) при заливке замыкается сам, а CFF требует замкнутых — приводим к closePath"""
    p = RecordingPen()
    gs[n].draw(p)
    return [("closePath" if o == "endPath" else o, a) for o, a in p.value], sum(1 for o, _ in p.value if o == "endPath")


def check_font(path, layers, tot, show):
    ot = TTFont(path)
    gso = ot.getGlyphSet()
    k = ot["head"].unitsPerEm / 1000.0
    nonempty = sorted([L for L in layers if L.suffix], key=lambda L: -len(L.suffix))
    default = [L for L in layers if L.suffix == ""]
    assert len(default) == 1, path
    default = default[0]
    bad, unmapped, n, pts, skipped = [], [], 0, 0, 0
    for g in ot.getGlyphOrder():
        L, r = default, g
        for C in nonempty:
            if g.endswith(C.suffix) and len(g) > len(C.suffix):
                L, r = C, g[:-len(C.suffix)]
                break
        gs = load_pfb(L.d["pfb"])
        base = r
        while base not in gs and "." in base[1:]:
            base = base.rsplit(".", 1)[0]
        if base not in gs:
            unmapped.append(g)
            pen = RecordingPen()
            gso[g].draw(pen)
            if pen.value:                                   # глиф без исходного должен быть пустым (пробелы Юникода, мягкий перенос)
                bad.append((g, "нет исходного, контур непустой"))
            continue
        if base in SYNTH:
            skipped += 1
            continue
        a, oa = draw(gs, base)
        b, _ = draw(gso, g)
        tot["open_contours"] += oa
        n += 1
        if [o for o, _ in a] != [o for o, _ in b]:
            bad.append((g, "команды"))
            continue
        dmax = 0.0
        for (o1, x1), (o2, x2) in zip(a, b):
            for p, q in zip(x1, x2):
                dmax = max(dmax, abs(p[0] * k - q[0]), abs(p[1] * k - q[1]))
                pts += 1
        tot["worst"] = max(tot["worst"], dmax)
        if dmax > 0.0:
            bad.append((g, dmax))
    tot["fonts"] += 1
    tot["glyphs"] += n
    tot["points"] += pts
    tot["bad"] += len(bad)
    tot["synth"] += skipped
    tot["unmapped"] += len(unmapped)
    for g in unmapped:
        tot["unmapped_names"][g] += 1
    print(f"[outl] {show:46s} слоёв {len(layers):2d}, глифов {n:6d}, точек {pts:8d}, расхождений {len(bad)}, без исходного {len(unmapped)}  {'OK' if not bad else 'ПЛОХО ' + str(bad[:4])}", flush=True)


def main():
    faces = sys.argv[1:] or list(F.FACE)
    tot = collections.Counter()
    tot["unmapped_names"] = collections.Counter()
    done = set()
    for face in faces:
        d0 = F.all_designs()[face][0]
        # «авто-размерный» шрифт: все слои
        pl = B.plan(face, "var")
        path = f"{T.OUTROOT}/auto/{B.names_for(face, 'var', d0)['ps']}.otf"
        if path not in done:
            done.add(path)
            check_font(path, pl["layers"] + pl["caps"], tot, os.path.relpath(path, T.OUTROOT))
        # статические шрифты: каждый рисунок
        if B.group_multi(F.FACE[face][0]):
            for d in F.all_designs()[face]:
                spath, nm = T.font_file(face, d)
                if spath in done:
                    continue
                done.add(spath)
                ps = B.plan(face, "static", d)
                check_font(spath, ps["layers"] + ps["caps"], tot, os.path.relpath(spath, T.OUTROOT))
    um = tot["unmapped_names"]
    print(f"итого: шрифтов {tot['fonts']}, глифов {tot['glyphs']}, точек {tot['points']}, расхождений {tot['bad']}, наибольшее смещение точки {tot['worst']} ед. (1/2000 em); "
          f"многоточие собирается заново: {tot['synth']}; глифов без исходного (служебные пустые): {tot['unmapped']} ({len(um)} имён: {', '.join(sorted(um)[:12])}{' …' if len(um) > 12 else ''}); "
          f"незамкнутых контуров Type 1, замкнутых при конвертации: {tot['open_contours']}")
    sys.exit(1 if tot["bad"] else 0)


if __name__ == "__main__":
    main()
