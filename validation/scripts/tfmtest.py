# -*- coding: utf-8 -*-
"""tfmtest.py — сверка шрифтов CM-Super для Typst с pdfLaTeX на уровне кодов TFM.

Для каждого рисунка (face, design) и каждой кодировки (T1, T2A, T2B, T2C, X2, TS1), а также для капители:
  * pdfLaTeX набирает строки из кодов символов через \\font\\f=<tfm> (естественная ширина, \\char"XX), кернинг/лигатуры — из TFM;
  * Typst набирает те же строки из Unicode-символов статическим шрифтом (рисунок = дизайн-размер) —
    кернинг/лигатуры — из OpenType;
  * из обоих PDF извлекаются положения начала каждого глифа и сравниваются построчно.
Запуск: python3 tfmtest.py FACE [tok ...] — все рисунки гарнитуры (или заданные).
"""
import os, sys, json, random, subprocess, collections, unicodedata, time, shutil, re, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "scripts"))
import warnings
warnings.filterwarnings("ignore")
from paths import *
import cmsfams as F
import tfmcache
import tfmlib
import build as B
import jobs
from fontTools.ttLib import TTFont
import pymupdf

TYPST = os.environ.get("TYPST", "typst")
OUTROOT = os.environ.get("CMS_FONTS", os.path.join(HERE, "..", "..", "fonts"))
ENCS = ["t1", "t2a", "t2b", "t2c", "x2", "ts1"]
ENCNAMES = {e: tfmlib.read_enc(f"{ENCDIR}/cm-super-{e}.enc")[1] for e in ENCS}
BP = 72.0 / 72.27
CYR = ("t2a", "t2b", "t2c", "x2")


def font_file(face, d):
    """Путь к статическому шрифту рисунка d гарнитуры face"""
    nm = B.names_for(face, "static", d)
    if B.group_multi(F.FACE[face][0]):
        return f"{OUTROOT}/static/{F.size_label(d['ds'])}/{nm['ps']}.otf", nm
    return f"{OUTROOT}/auto/{nm['ps']}.otf", nm


_inv_cache = {}


def inverse_cmap(path):
    """имя глифа -> Unicode (наименьший код, но не пробелы/служебные); '.cyr' -> как у базового глифа"""
    if path in _inv_cache:
        return _inv_cache[path]
    f = TTFont(path)
    cm = f.getBestCmap()
    inv = {}
    for u, n in sorted(cm.items()):
        if n not in inv:
            inv[n] = u
    # исключения: для hyphen берём U+002D, для endash — U+2013 (а не цифровое тире U+2012)
    inv["hyphen"] = 0x2D
    if cm.get(0x2013) == "endash":
        inv["endash"] = 0x2013
    for n in list(inv):
        pass
    res = (inv, set(f.getGlyphOrder()))
    _inv_cache[path] = res
    return res


def code_unicode(enc, code, inv):
    nm = ENCNAMES[enc][code]
    if nm == ".notdef":
        return None
    if nm in inv:
        return inv[nm]
    if nm.endswith(".cyr") and nm[:-4] in inv:
        return inv[nm[:-4]]
    return None


def tex_code_str(codes):
    return "".join('\\char"%02X' % c for c in codes)


def typst_str(us):
    out = []
    for u in us:
        ch = chr(u)
        if ch.isalnum() and ord(ch) < 128:
            out.append(ch)
        elif ch == " ":
            out.append(" ")
        else:
            out.append("\\u{%X}" % u)
    return "".join(out)


def gen_units(face, d, kind, rng, caps_scale=1.0):
    """Список тестовых «страниц»: dict(enc, tfm, lines=[tokens...]) для рисунка d (kind='base' | 'caps').
    Токен — кортеж кодов. Строка — список токенов."""
    cache = tfmcache.load()
    if kind == "base":
        tf = d["tfms"]
    else:
        cd = F.caps_design_for(face, d)
        if not cd:
            return []
        tf = cd["tfms"]
    path, nm = font_file(face, d)
    inv, glyphs = inverse_cmap(path)
    import cmsmetrics
    mm = cmsmetrics.design_metrics(tf)
    lost_by_enc = collections.defaultdict(set)
    for cf in mm["conflicts"]:
        if cf[0] != "designsize":
            lost_by_enc[cf[1]].add(cf[0])
    units = []
    for enc in ENCS:
        if enc not in tf:
            continue
        t = cache[tf[enc]]
        chars = t["chars"]
        tsconf = set()
        lost = set()      # раньше исключали глифы с разной шириной в T1/TS1/T2A; теперь для них есть «латинские двойники»
        ok = {}
        for c in chars:
            u = code_unicode(enc, c, inv)
            if u is None:
                continue
            ch = chr(u)
            # символы, которые Typst/HarfBuzz трактуют особо
            if u in (0x20, 0xA0, 0xAD, 0x200B, 0x200C, 0x200D, 0x2028, 0x2029, 0x202F, 0x205F) or 0x2000 <= u <= 0x200A:
                continue
            if unicodedata.category(ch) in ("Cc", "Cs", "Zl", "Zp", "Mn", "Me"):
                continue                      # комбинирующие знаки: шейпер обнуляет их ширину по Unicode (это штатное поведение)
            if ENCNAMES[enc][c] in lost:
                continue                      # ширина глифа в этой кодировке отличается от выбранной (T2A главнее) — известное ограничение
            if enc == "ts1" and abs(mm["adv_L"].get(ENCNAMES[enc][c], 0.0) - chars[c].get("wd", 0.0)) > 2.0e-4:
                tsconf.add(ENCNAMES[enc][c])  # глиф есть и в T1, и в TS1 с разной шириной: в Unicode-тексте это один символ, берётся T1
                continue
            ok[c] = u
        # коды с одним Unicode, но разными метриками (разные glyph name -> один Unicode) исключаем
        byu = collections.defaultdict(list)
        for c, u in ok.items():
            byu[u].append(c)
        for u, cs in byu.items():
            if len(cs) > 1:
                names = {ENCNAMES[enc][c] for c in cs}
                ws = {round(chars[c].get("wd", 0), 5) for c in cs}
                if len(names) > 1 or len(ws) > 1:
                    for c in cs:
                        ok.pop(c, None)
        if not ok:
            continue
        pairs = t["pairs"]
        lines = []
        # A: все символы по одному
        codes = sorted(ok)
        toks = [(c,) for c in codes]
        # B: пары с кернингом (включая границу слова — «пара» с пробелом добавляем отдельно)
        kp = sorted((a, b) for (a, b), v in pairs.items() if v[0] == "KRN" and a in ok and b in ok)
        lp = sorted((a, b) for (a, b), v in pairs.items() if v[0] == "LIG" and a in ok and b in ok)
        toks_k = [p for p in kp]
        toks_l = [p for p in lp]
        # D: тройки и четвёрки из алфавита лигатур
        alpha = sorted({x for p in lp for x in p})
        trip = []
        if alpha:
            trip = [(a, b, c) for a in alpha for b in alpha for c in alpha]
            rng.shuffle(trip)
            trip = trip[:2500]
            quad = [tuple(rng.choice(alpha) for _ in range(4)) for _ in range(1200)]
            trip += quad
        # E: случайные слова из букв
        letters = [c for c in codes if chr(ok[c]).isalpha()]
        words = []
        if len(letters) > 4:
            for _ in range(1500):
                n = rng.randint(2, 9)
                words.append(tuple(rng.choice(letters) for _ in range(n)))
        # F: слова из алфавита, пробела-границы: «x» + пробел (проверка кернов правой границы)
        bk = sorted({a for (a, b), v in pairs.items() if v[0] == "KRN" and a in ok and b == t.get("boundary")})
        toks_b = [(a,) for a in bk]
        # G: пары-лигатура/керн с «пробельным» окружением: обычные пары после пробела
        # compwordmark (код 23, U+200C): TeX-кёрны (23, x) — отдельный набор
        zc = [c for c in chars if ENCNAMES[enc][c] == "afii61664"]
        okz = dict(ok)
        toks_zw = []
        if zc:
            z = zc[0]
            okz[z] = 0x200C
            toks_zw = sorted((z, b) for (a, b), v in pairs.items() if a == z and v[0] == "KRN" and b in ok)
        sets = [("all", toks), ("kern", toks_k), ("lig", toks_l), ("chain", trip), ("words", words), ("bound", toks_b), ("zw", toks_zw)]
        if enc == "ts1":
            # символы TS1 в LaTeX набираются только отдельными командами (\\textXXX); цепочки/лигатуры ASCII-знаков идут через T1
            sets = [x for x in sets if x[0] in ("all", "kern", "bound")]
        units.append(dict(enc=enc, tfm=tf[enc], ds_font=t["designsize"], tsconf=sorted(tsconf), sets=sets, ok=ok, okz=okz, kind=kind, inv=inv, wd={c: d.get("wd", 0.0) for c, d in chars.items()}))
    return units


def make_lines(tokens, size_pt, wd, width_pt=3500):
    """делит токены на строки так, чтобы строка заведомо помещалась в width_pt:
    оценка по ширинам TFM (wd: код -> доля em) с запасом 15 % на кернинг и по 0.6 em на пробел"""
    lines, cur, n = [], [], 0.0
    for tok in tokens:
        w = (sum(max(wd.get(c, 0.0), 0.2) for c in tok) * 1.15 + 0.6) * size_pt
        if cur and n + w > width_pt:
            lines.append(cur)
            cur, n = [], 0.0
        cur.append(tok)
        n += w
    if cur:
        lines.append(cur)
    return lines


def latex_doc(pages, workdir, name="t"):
    """pages: список dict(tfm, size_pt(TeX), lines=[tokens...]). Возвращает путь к PDF."""
    os.makedirs(workdir, exist_ok=True)
    out = [r"\documentclass{article}",
           r"\usepackage[paperwidth=4100pt,paperheight=16000pt,margin=10pt]{geometry}",
           r"\pagestyle{empty}\setlength{\parindent}{0pt}\setlength{\parskip}{0pt}\setlength{\baselineskip}{14pt}",
           r"\begin{document}", r"\raggedright"]
    for pg in pages:
        out.append((r"\font\f=%s at %.5fpt \relax" % (pg["tfm"], pg["at"])) if pg.get("at") else (r"\font\f=%s \relax" % pg["tfm"]))
        for ln in pg["lines"]:
            body = r"\ ".join(tex_code_str(tok) for tok in ln)
            out.append(r"\noindent\hbox{\f %s}\par\vskip 0pt" % body)
        out.append(r"\newpage")
    out.append(r"\end{document}")
    p = os.path.join(workdir, name + ".tex")
    open(p, "w").write("\n".join(out))
    env = dict(os.environ)
    env["TFMFONTS"] = TFMDIR + "//:"
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", name + ".tex"], cwd=workdir, capture_output=True, env=env)
    if r.returncode != 0:
        raise RuntimeError("pdflatex: " + r.stdout.decode("utf-8", "replace")[-1500:])
    return os.path.join(workdir, name + ".pdf")


def typst_doc(pages, workdir, fontdirs, name="t"):
    os.makedirs(workdir, exist_ok=True)
    out = ['#set page(width: 4100pt, height: auto, margin: 10pt)',
           '#set par(justify: false, leading: 4pt, spacing: 4pt)']
    for k, pg in enumerate(pages):
        if k:
            out.append("#pagebreak()")
        sty = pg["style"]
        # стиль/вес/растяжение выбирают нужное начертание в семействе
        out.append(f'#set text(font: "{pg["family"]}", size: {pg["size_pt"] * BP:.6f}pt, weight: {pg["weight"]}, style: "{sty}", stretch: {pg["stretch"]}%,'
                   f' fallback: false, lang: "{pg["lang"]}", script: "{pg["script"]}", hyphenate: false{pg.get("extra", "")})')
        for ln in pg["tlines"]:
            out.append("#text(" + '"' + " ".join(typst_str(tok) for tok in ln) + '")')
            out.append("")
    p = os.path.join(workdir, name + ".typ")
    open(p, "w").write("\n".join(out))
    cmd = [TYPST, "compile", "--ignore-system-fonts"]
    for fd in fontdirs:
        cmd += ["--font-path", fd]
    cmd += [p, os.path.join(workdir, name + ".pdf")]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("typst: " + r.stderr.decode("utf-8", "replace")[-2000:])
    return os.path.join(workdir, name + ".pdf"), r.stderr.decode("utf-8", "replace")


def extract(pdf):
    import pdfglyphs
    return pdfglyphs.extract(pdf)


def _norm(t):
    return unicodedata.normalize("NFKD", t)


def compare(lat, typ, size_pt, tol_em=0.0025, verbose=3, enc=None, inv=None):
    """Сравнение по «шагам» (разности позиций соседних глифов): ошибки округления не накапливаются.
    Допуск tol_em·кегль. Дополнительно сверяется тождество глифов (по тексту ToUnicode), где оно известно."""
    size = size_pt * BP
    tol = tol_em * size
    st = dict(lines=0, glyphs=0, maxstep=0.0, bad_lines=0, drift=0.0, ident_bad=0, examples=[], idpairs=collections.Counter())
    if len(lat) != len(typ):
        st["err"] = f"число строк: LaTeX {len(lat)}, Typst {len(typ)}"
    for i, (a, b) in enumerate(zip(lat, typ)):
        st["lines"] += 1
        if len(a) != len(b):
            st["bad_lines"] += 1
            if len(st["examples"]) < verbose:
                st["examples"].append((i, "число глифов", len(a), len(b)))
            continue
        worst, wi = 0.0, -1
        ident = 0
        for j in range(len(a) - 1):
            da = a[j + 1][0] - a[j][0]
            db = b[j + 1][0] - b[j][0]
            d = abs(da - db)
            if d > worst:
                worst, wi = d, j
        for j in range(len(a)):
            # тождество глифа: код LaTeX -> имя по enc-файлу -> Unicode (по cmap шрифта) против текста кластера Typst
            if enc is not None:
                u = code_unicode(enc, a[j][3], inv)
                ta = _norm(chr(u)) if u is not None else ""
            else:
                ta = _norm(a[j][1])
            tb = _norm(b[j][1])
            if ta and tb and ta != tb and not tb.startswith("(cid"):
                ident += 1
                st["idpairs"][(ta, tb)] += 1
        st["glyphs"] += len(a)
        st["maxstep"] = max(st["maxstep"], worst / size)
        st["drift"] = max(st["drift"], abs((a[-1][0] - a[0][0]) - (b[-1][0] - b[0][0])) / size)
        st["ident_bad"] += ident
        if worst > tol or ident:
            st["bad_lines"] += 1
            if len(st["examples"]) < verbose:
                st["examples"].append((i, "step" if worst > tol else "ident", round(worst / size, 5), wi, len(a), ident))
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("face")
    ap.add_argument("toks", nargs="*")
    ap.add_argument("--kinds", default="base,caps")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sample", type=float, default=1.0, help="доля токенов, используемых в тесте")
    ap.add_argument("--tol", type=float, default=0.02)
    ap.add_argument("--work", default=None)
    args = ap.parse_args()
    face = args.face
    ad = F.all_designs()
    designs = [d for d in ad[face] if not args.toks or d["tok"] in args.toks]
    rng = random.Random(args.seed)
    work = args.work or f"{HERE}/work/{face}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    grp, sty, wt, it, ob, wd, capsf = F.FACE[face]
    style = "italic" if it else ("oblique" if ob else "normal")
    stretch = 100 if wd == 5 else 75
    pages_l, pages_t, meta, invs = [], [], [], []
    designs_size = {d["tok"]: d["ds"] for d in designs}
    fontdirs = set()
    for d in designs:
        path, nm = font_file(face, d)
        fontdirs.add(os.path.dirname(path))
        for kind in args.kinds.split(","):
            for u in gen_units(face, d, kind, rng):
                ds = d["ds"]
                for sname, toks in u["sets"]:
                    if not toks:
                        continue
                    if args.sample < 1.0:
                        toks = [t for t in toks if rng.random() < args.sample]
                        if not toks:
                            continue
                    lines = make_lines(toks, ds, u["wd"])
                    okmap = u["okz"] if sname == "zw" else u["ok"]
                    tlines = [[[okmap[c] for c in tok] for tok in ln] for ln in lines]
                    cyr = u["enc"] in CYR
                    pages_l.append(dict(tfm=u["tfm"], lines=lines, at=(ds if abs(u["ds_font"] - ds) > 1e-3 else None)))
                    extra = ', features: (smcp: 1)' if kind == "caps" else ', features: (smcp: 0)'      # set-правила накапливаются: сбрасываем smcp для обычных страниц
                    pages_t.append(dict(family=nm["typo_family"], size_pt=ds, weight=nm["weight"], style=style, stretch=stretch,
                                        lang=("cu" if u["enc"] == "x2" else "ru") if cyr else "en", script="cyrl" if cyr else "latn", tlines=tlines, extra=extra))
                    meta.append((face, d["tok"], kind, u["enc"], sname, u["tfm"], len(toks)))
                    invs.append(u["inv"])
    json.dump([dict(meta=list(m), tfm=p["tfm"], lines=p["lines"]) for m, p in zip(meta, pages_l)], open(work + "/pages.json", "w"))
    t0 = time.time()
    lpdf = latex_doc(pages_l, work + "/tex")
    t1 = time.time()
    tpdf, warn = typst_doc(pages_t, work + "/typ", sorted(fontdirs))
    t2 = time.time()
    L = extract(lpdf)
    T = extract(tpdf)
    t3 = time.time()
    print(f"[{face}] pages: latex {len(L)}, typst {len(T)}; times: latex {t1-t0:.0f}s typst {t2-t1:.0f}s extract {t3-t2:.0f}s; typst warnings: {len(warn.splitlines())}")
    if len(L) != len(T):
        print("  !! число страниц не совпало")
    tot = collections.Counter()
    worst = []
    idp = collections.Counter()
    for k, m in enumerate(meta):
        if k >= len(L) or k >= len(T):
            break
        st = compare(L[k], T[k], designs_size[(m[1])], enc=m[3], inv=invs[k])
        tot["lines"] += st["lines"]
        tot["glyphs"] += st["glyphs"]
        tot["bad_lines"] += st["bad_lines"]
        flag = "OK " if st["bad_lines"] == 0 and "err" not in st else "BAD"
        if flag == "BAD":
            worst.append((flag, m, st))
        tot["maxstep"] = max(tot["maxstep"], st["maxstep"])
        tot["ident_bad"] += st["ident_bad"]
        idp.update(st["idpairs"])
    print(f"  итого: строк {tot['lines']}, глифов {tot['glyphs']}, плохих строк {tot['bad_lines']}, несовпадений глифов {tot['ident_bad']}, макс. шаг {tot['maxstep']:.5f} em")
    for flag, m, st in worst[:40]:
        print("  ", flag, m, {k: v for k, v in st.items() if k not in ("examples", "idpairs")}, st["examples"][:2])
    if idp:
        print("  несовпадения тождества (LaTeX -> Typst):", [(a, b, n) for (a, b), n in idp.most_common(25)])
    json.dump(dict(face=face, tot=dict(tot), worst=[(f, list(m), {k: v for k, v in st.items() if k != "idpairs"}) for f, m, st in worst]), open(work + "/result.json", "w"), default=str)
    return tot["bad_lines"]


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
