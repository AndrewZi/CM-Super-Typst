# -*- coding: utf-8 -*-
"""boundary_scan.py — как «авто-размерный» шрифт переключает рисунок вблизи границ и по всей оси opsz.

Проверка делается движком HarfBuzz (uharfbuzz) прямо по готовым OTF из OUT/out/auto (или из каталога $E2E_FONTS):
  1. вокруг каждой границы между рисунками (середина между соседними размерами списка NFSS, пт TeX) берётся 2*N+1 размеров с шагом
     STEP (0,0003 пт, это меньше кванта оси: 24/16384 = 0,0015 пт) и по имени глифа (суффикс «.dTOK») определяется, какой рисунок выбран;
     требуется: последовательность рисунков = нижний, …, нижний, верхний, …, верхний (один переход, без «чужого» рисунка и возвратов),
     переход — выше номинальной границы и не дальше 1,5 кванта от неё; на самой границе — нижний (как NFSS: при равенстве меньший размер);
  2. по всей оси (4…40 пт TeX с шагом 0,01 пт) рисунок совпадает с ожидаемым (диапазоны из cmsfams), кроме полосы ±3 кванта у границ.
Запуск: python3 boundary_scan.py [FACE ...]   (по умолчанию — все гарнитуры с несколькими рисунками)
"""
import os, sys, re, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "scripts"))
from paths import *
import cmsfams as F
import build as B
import assemble as A
from fontTools.ttLib import TTFont
import uharfbuzz as hb

BP = A.TEX2BP
FONTDIR = os.environ.get("E2E_FONTS", os.path.join(HERE, "..", "..", "fonts", "auto"))
N = 12                       # точек с каждой стороны границы
STEP = 0.0003                # шаг, пт TeX
QUANT_HI = 24.0 / 16384      # квант оси выше 12 пт (пт Typst)
QUANT_LO = 7.0 / 16384       # квант ниже 12 пт
SUF = re.compile(r"\.d(\d+)")


def quantum_tex(opsz):
    return (QUANT_HI if opsz >= A.AXIS_DEF else QUANT_LO) / BP


def probe_char(cm):
    """символ из кириллицы (контекст R без подмен «Sans 5–7 pt → 8 pt») — «Н»; запасной вариант — «H»"""
    return "Н" if 0x41D in cm else "H"


def main():
    faces = sys.argv[1:] or sorted(F.FACE)
    tot = dict(faces=0, boundaries=0, points=0, bad=0, coarse=0, flip_far=0, tie_upper=0)
    for face in faces:
        pl = B.plan(face, "var")
        if not pl["var"]:
            continue
        d0 = F.all_designs()[face][0]
        nm = B.names_for(face, "var", d0)
        path = f"{FONTDIR}/{nm['ps']}.otf"
        tt = TTFont(path)
        order = tt.getGlyphOrder()
        ch = probe_char(tt.getBestCmap())
        script, lang = ("Cyrl", "rus") if ch != "H" else ("Latn", "eng")
        fb = hb.Face(hb.Blob.from_file_path(path))
        fnt = hb.Font(fb)

        def design_at(s_tex):
            fnt.set_variations({"opsz": s_tex * BP})
            b = hb.Buffer()
            b.add_str(ch)
            b.direction = "ltr"
            b.script = script
            b.language = lang
            hb.shape(fnt, b, {})
            g = order[b.glyph_infos[0].codepoint]
            m = SUF.search(g)
            return m.group(1) if m else "default"

        layers = sorted(pl["layers"], key=lambda L: L.rng[0])
        default_tok = [L for L in layers if L.suffix == ""][0].d["tok"]
        tok_of = {L.suffix[2:] if L.suffix else "default": L.d["tok"] for L in layers}
        rngs = [(("default" if L.suffix == "" else L.suffix[2:]), L.rng[0], L.rng[1]) for L in layers]
        bounds = [r[2] for r in rngs[:-1]]
        nb = 0
        bad = []
        flips = []
        for i, b in enumerate(bounds):
            lo_name, up_name = rngs[i][0], rngs[i + 1][0]
            seq = [design_at(b + k * STEP) for k in range(-N, N + 1)]
            tot["points"] += len(seq)
            nb += 1
            # допустимы только нижний и верхний, один переход
            ok = all(x in (lo_name, up_name) for x in seq)
            if ok:
                first_up = [j for j, x in enumerate(seq) if x == up_name]
                if first_up:
                    j0 = first_up[0]
                    ok = all(x == up_name for x in seq[j0:]) and j0 >= 1
                    flip_k = j0 - N                         # переход происходит между (flip_k-1) и flip_k шагами
                else:
                    ok = False
                    flip_k = None
            else:
                flip_k = None
            if not ok:
                bad.append((b, lo_name, up_name, seq))
                continue
            q = quantum_tex(b * BP) / STEP                   # квант в шагах
            if not (1 <= flip_k <= 1.6 * q + 1):             # переход — выше границы, не дальше 1,5 кванта
                tot["flip_far"] += 1
                bad.append((b, lo_name, up_name, f"переход не там: через {flip_k} шагов после границы (квант {q:.1f} шага)"))
            if seq[N] != lo_name:
                tot["tie_upper"] += 1
                bad.append((b, lo_name, up_name, "на самой границе выбран не нижний рисунок"))
            flips.append(flip_k)
        # по всей оси
        coarse_bad = []
        s = 4.0
        while s <= 40.0:
            near = any(abs(s - b) <= 3 * quantum_tex(b * BP) for b in bounds)
            if not near:
                exp = [n for n, lo, hi in rngs if lo < s <= hi][0]
                got = design_at(s)
                tot["coarse"] += 1
                if got != exp:
                    coarse_bad.append((round(s, 3), exp, got))
            s = round(s + 0.01, 4)
        status = "OK" if not bad and not coarse_bad else "ПЛОХО"
        print(f"[scan] {face:7s} {nm['typo_family']} / {nm['typo_style']}: границ {nb}, переходы (шагов от границы) {sorted(set(flips))}, "
              f"плохих границ {len(bad)}, плохих точек оси {len(coarse_bad)}  {status}", flush=True)
        for x in bad[:6]:
            print("     граница", x[0], x[1], "→", x[2], x[3])
        for x in coarse_bad[:6]:
            print("     ось", x)
        tot["faces"] += 1
        tot["boundaries"] += nb
        tot["bad"] += len(bad) + len(coarse_bad)
    print(f"итого: гарнитур {tot['faces']}, границ {tot['boundaries']}, точек у границ {tot['points']}, точек по оси {tot['coarse']}, "
          f"плохих {tot['bad']}, переход не там {tot['flip_far']}, на самой границе выбран верхний {tot['tie_upper']}")
    sys.exit(1 if tot["bad"] else 0)


if __name__ == "__main__":
    main()
