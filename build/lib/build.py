"""build.py — сборка одного шрифта CM-Super (OpenType/CFF) для Typst.

build_font(face, mode, outdir, design=None):
   mode 'var'    — «авто-размер»: все рисунки гарнитуры в одном файле, ось opsz + FeatureVariations (если рисунков > 1);
                   семейство называется без размера («CM-Super», «CM-Super Sans» …)
   mode 'static' — один рисунок (design) как отдельный шрифт; семейство «CM-Super 12», «CM-Super Sans 8» …
Результат: путь к .otf.
"""
import os, sys, json, subprocess, time, shutil
sys.path.insert(0, os.path.dirname(__file__))
from paths import *
import cmsfams as F
import cmsmetrics
import assemble as A
import unitab
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen

PFBINFO = None
FF = "fontforge"
COPYRIGHT = ("Copyright 2001, 2002 Vladimir Volovich (CM-Super 0.3.4), outlines after Computer Modern by Donald E. Knuth. "
             "OpenType conversion 2026: metrics, kerning and ligatures from the LaTeX TFM files. "
             "GNU GPL v2 or later with the font exception: embedding in documents is permitted.")
LICENSE = ("GNU General Public License v2 or later with the font exception: you may embed these fonts in PDF/PostScript documents "
           "regardless of the license of the document.")
LICENSE_URL = "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html"
RIBBI = ("Regular", "Bold", "Italic", "Bold Italic")


def pfbinfo():
    global PFBINFO
    if PFBINFO is None:
        PFBINFO = json.load(open(FULL + "/pfbinfo.json"))
    return PFBINFO


def group_multi(grp):
    """есть ли в группе гарнитура с несколькими рисунками (тогда у «статических» семейств в имени есть размер)"""
    ad = F.all_designs()
    return any(len(ad[f]) > 1 for f in F.FACE if F.FACE[f][0] == grp)


def names_for(face, mode, d):
    """Параметры таблицы name и стиля. d — основной рисунок."""
    grp, sty, wt, it, ob, wd, capsf = F.FACE[face]
    fam, ps, kind, rule, mono = F.GROUP[grp]
    famx, psfam = fam, ps
    if mode == "static" and group_multi(grp):
        famx = f"{fam} {F.size_label(d['ds'])}"
        psfam = ps + d["tok"]
    if sty in RIBBI:
        id1, id2 = famx, sty
    else:
        id1, id2 = f"{famx} {sty}", "Regular"
    full = famx if sty == "Regular" else f"{famx} {sty}"
    psname = f"{psfam}-{sty.replace(' ', '')}"
    return dict(id1=id1, id2=id2, full=full, ps=psname, typo_family=famx, typo_style=sty, family=famx, kind=kind, mono=mono, weight=wt,
                italic=it, oblique=ob, width=wd, grp=grp, sty=sty)


def run_ff(spec, workdir):
    os.makedirs(workdir, exist_ok=True)
    sp = os.path.join(workdir, "spec.json")
    json.dump(spec, open(sp, "w"))
    r = subprocess.run([FF, "-lang=py", "-script", os.path.join(os.path.dirname(__file__), "ffmaster.py"), sp], capture_output=True, text=True)
    if r.returncode or not os.path.exists(spec["out"]):
        raise RuntimeError("FontForge: " + (r.stderr or r.stdout)[-1500:])
    lines = r.stderr.strip().splitlines()
    return lines[-1] if lines else ""


def pfb_path(pfb):
    return f"{PFBDIR}/{pfb}.pfb"


def plan(face, mode, design=None):
    """Определяет слои шрифта. Возвращает dict(default, layers, caps_layers, caps_of, var)."""
    grp, sty, wt, it, ob, wd, capsf = F.FACE[face]
    fam, ps, kind, rule, mono = F.GROUP[grp]
    ad = F.all_designs()
    pinfo = pfbinfo()
    designs_all = ad[face]
    if mode == "static":
        assert design is not None
        chosen = [(design, float("-inf"), float("inf"))]
        default_d = design
    else:
        rngs, remap_ds = F.context_split(rule, designs_all)      # remap_ds: рисунки кириллического контекста, которые в латинском заменяются другими (sans 5–7 pt)
        chosen = []
        for dsv, lo, hi in rngs:
            d = min(designs_all, key=lambda x: (abs(x["ds"] - dsv), x["ds"]))
            chosen.append((d, lo, hi))
        if face in F.SUBST:
            # размеры меньше порога берутся из face-замены (по её собственному правилу выбора рисунка)
            sub_face, below = F.SUBST[face]
            t_lo = max(s for s in F.LISTED if s < below)
            thr = (t_lo + below) / 2.0                       # граница NFSS между соседними размерами списка
            sub_designs = ad[sub_face]
            new = []
            for dsv, lo, hi in F.design_ranges(rule, sub_designs):
                if lo >= thr:
                    continue
                d = min(sub_designs, key=lambda x: (abs(x["ds"] - dsv), x["ds"]))
                new.append((d, lo, min(hi, thr)))
            for d, lo, hi in chosen:
                if hi <= thr:
                    continue
                new.append((d, max(lo, thr), hi))
            chosen = new
        x0 = A.AXIS_DEF / A.TEX2BP
        default_d = [d for d, lo, hi in chosen if lo < x0 <= hi][0]
        # два диапазона могут указывать на один и тот же рисунок — объединяем
        merged = []
        for d, lo, hi in chosen:
            if merged and merged[-1][0] is d:
                merged[-1] = (d, merged[-1][1], hi)
            else:
                merged.append((d, lo, hi))
        chosen = merged
    layers = []
    for d, lo, hi in chosen:
        suf = "" if d is default_d else ".d" + d["tok"]
        m = cmsmetrics.design_metrics(d["tfms"])
        names = [n for n in pinfo[d["pfb"]]["glyphs"] if n != ".notdef"] + A.EXTRA_EMPTY
        if suf == "":
            names.append(".notdef")
        L = A.Layer(suf, m, names, caps=False, design_key=d["key"], rng=(lo, hi))
        L.d = d
        layers.append(L)
    # слои капители
    cap_layers, caps_of = {}, {}
    default_cap = F.caps_design_for(face, default_d)
    for L in layers:
        cd = F.caps_design_for(face, L.d)
        if not cd:
            continue
        if cd["key"] not in cap_layers:
            if default_cap is not None and cd["key"] == default_cap["key"]:
                suffix = ".cc"
            else:
                suffix = ".cc.d" + cd["tok"]
            m = cmsmetrics.design_metrics(cd["tfms"])
            names = [n for n in pinfo[cd["pfb"]]["glyphs"] if n != ".notdef"]
            C = A.Layer(suffix, m, names, caps=True, design_key=cd["key"])
            C.d = cd
            cap_layers[cd["key"]] = C
        caps_of[L.suffix] = cap_layers[cd["key"]]
    # порядок: основной слой первым
    layers.sort(key=lambda L: (L.suffix != "", L.d["ds"]))
    # замены рисунков для латинского контекста: суффикс слоя -> суффикс слоя-замены
    lmap = {}
    if mode != "static":
        for L in layers:
            for dsR, dsL in remap_ds.items():
                if L.d["ds"] == dsR:
                    tg = [T for T in layers if T.d["ds"] == dsL]
                    assert len(tg) == 1, (face, dsR, dsL)
                    lmap[L.suffix] = tg[0].suffix
    return dict(default=default_d, layers=layers, caps=list(cap_layers.values()), caps_of=caps_of, var=len(layers) > 1, lmap=lmap)


def expected_widths(pl):
    """{имя глифа с суффиксом: ширина в единицах em=UPEM}; отдельно — пробелы Unicode; и список синтетических глифов (многоточие)"""
    pinfo = pfbinfo()
    W, SP, SYN = {}, {}, []
    for L in pl["layers"] + pl["caps"]:
        pg = pinfo[L.d["pfb"]]
        sc = A.UPEM / float(pg["em"])
        adv = A.layer_advances(L)
        sp = A.space_widths(L) if not L.caps else {}
        for n in L.names:
            g = n + L.suffix
            if n in sp:
                SP[g] = A.rnd(sp[n] * A.UPEM)
            elif n in adv:
                W[g] = A.rnd(adv[n] * A.UPEM)
            elif n in pg["glyphs"]:
                W[g] = A.rnd(pg["glyphs"][n][0] * sc)
        for n, wl in L.m.get("wvar", {}).items():
            if n in L.names:
                W[n + ".lat" + L.suffix] = A.rnd(wl * A.UPEM)
        # многоточие как в LaTeX (\textellipsis = «.\kern\fontdimen3» ×3)
        if "ellipsis" in L.names and "period" in L.names and "period" in adv:
            step = A.rnd((adv["period"] + L.m["stretch"]) * A.UPEM)
            SYN.append({"glyph": "ellipsis" + L.suffix, "base": "period" + L.suffix, "n": 3, "step": step})
            W["ellipsis" + L.suffix] = 3 * step
    return W, SP, SYN


def alias_specs(pl):
    """двойники «имя.lat» глифов, у которых ширина в латинском контексте (T1/TS1) отличается от русского (T2A)"""
    out = []
    for L in pl["layers"] + pl["caps"]:
        for n in sorted(L.m.get("wvar", {})):
            if n in L.names:
                out.append({"src": n + L.suffix, "dst": n + ".lat" + L.suffix})
    return out


def build_font(face, mode, outdir, design=None, workroot=None, keep=False, verbose=True, tag=None):
    t0 = time.time()
    pinfo = pfbinfo()
    pl = plan(face, mode, design)
    layers, caps_layers, caps_of, default_d = pl["layers"], pl["caps"], pl["caps_of"], pl["default"]
    nm = names_for(face, mode, default_d)
    W, SPW, SYN = expected_widths(pl)
    work = os.path.join(workroot or WORK, tag or f"{face}_{mode}_{default_d['tok'] if mode == 'static' else 'var'}")
    os.makedirs(work, exist_ok=True)
    master = os.path.join(work, "master.otf")
    ff_layers = [{"pfb": pfb_path(L.d["pfb"]), "suffix": L.suffix} for L in layers + caps_layers]
    msg = run_ff({"out": master, "em": A.UPEM, "layers": ff_layers, "extra_empty": A.EXTRA_EMPTY, "widths": W, "synth": SYN, "aliases": alias_specs(pl)}, work)
    font = TTFont(master)
    for t in ("GDEF", "FFTM", "GSUB", "GPOS", "cmap"):
        if t in font:
            del font[t]
    glyph_order = font.getGlyphOrder()
    go = set(glyph_order)
    # Unicode -> глиф основного слоя
    cmap = unitab.unicode_table(default_d["pfb"])
    base_names = layers[0].names
    cm = {u: n for u, n in cmap.items() if n in base_names and n in go}
    # Unicode-пробелы: пустые глифы с нужной шириной (и в CFF, и в hmtx)
    cff = font["CFF "].cff
    top = cff.topDictIndex[0]
    cs = top.CharStrings
    hm = font["hmtx"].metrics
    for g, w in SPW.items():
        if g not in go:
            raise RuntimeError(f"нет пустого глифа {g}")
        pen = T2CharStringPen(w, None)
        newcs = pen.getCharString(private=cs[g].private, globalSubrs=cs[g].globalSubrs)
        cs[g] = newcs
        hm[g] = (w, 0)
    # проверка ширин
    bad = [(g, W[g], hm[g][0]) for g in W if g in go and hm[g][0] != W[g]]
    miss = [g for g in list(W) + list(SPW) if g not in go]
    if miss:
        raise RuntimeError(f"в шрифте нет глифов: {miss[:10]} (всего {len(miss)})")
    if bad:
        raise RuntimeError(f"ширины не совпали: {bad[:10]} (всего {len(bad)})")
    A.build_cmap_table(font, cm)
    _E = cmsmetrics._ENC
    ts1_only = (set(_E["ts1"]) - set(_E["t1"])) - {".notdef"}
    n_R = set(_E["t2a"]) | set(_E["t2b"]) | set(_E["t2c"]) | set(_E["x2"])
    smcp_exR = (set(_E["ts1"]) - n_R) - {".notdef"}
    stats = A.build_layout(font, layers, caps_of, cm, {"lmap": pl["lmap"], "ts1_only": ts1_only, "smcp_exR": smcp_exR})
    nrv = 0
    axis_id = 256
    if pl["var"]:
        A.add_fvar(font, axis_id)
        A.add_hvar(font)
        nrv = A.add_rvrn(font, layers, "")
    ang = float(pinfo[default_d["pfb"]]["italicangle"] or 0)
    p = dict(nm)
    p.update(copyright=COPYRIGHT, license=LICENSE, license_url=LICENSE_URL, uid=f"{nm['ps']};0.3.4;2026",
             version="Version 0.3.4; OpenType conversion 2026", italic_angle=ang, axis_name_id=axis_id if pl["var"] else None,
             is_regular=(nm["sty"] == "Regular"), italic_only_bold=False, cond_only=(nm["width"] != 5))
    A.set_names(font, p)
    A.fix_tables(font, p, cm)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, nm["ps"] + ".otf")
    font.save(out)
    if not keep:
        shutil.rmtree(work, ignore_errors=True)
    info = dict(path=out, size=os.path.getsize(out), layers=len(layers), caps=len(caps_layers), glyphs=len(go), stats=stats, rvrn=nrv, secs=time.time() - t0,
                family=nm["typo_family"], style=nm["sty"], ff=msg)
    if verbose:
        print(f"{face:7s} {mode:6s} {nm['typo_family']} / {nm['sty']}: {os.path.basename(out)} {info['size']//1024} KB, слоёв {len(layers)}+{len(caps_layers)}, "
              f"глифов {len(go)}, {stats}, rvrn={nrv}, {info['secs']:.1f} с", flush=True)
    return info


if __name__ == "__main__":
    face, mode, outdir = sys.argv[1:4]
    des = None
    if mode == "static":
        tok = sys.argv[4]
        des = [d for d in F.all_designs()[face] if d["tok"] == tok][0]
    build_font(face, mode, outdir, des, keep=True)
