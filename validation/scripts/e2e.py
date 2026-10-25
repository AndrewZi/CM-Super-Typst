# -*- coding: utf-8 -*-
"""e2e.py — сквозная проверка «настоящий LaTeX (NFSS + babel, T1/T2A) ↔ Typst + cm-super.typ + variable-шрифты».

Каждая строка теста — \\hbox{...} (без переносов). Для каждой строки получаем из обоих PDF
  * позиции начала глифов — сравнение «по шагам» (допуск 0.0025 em);
  * гарнитуру (по PostScript-имени шрифта в PDF: SFRM1200 → sfrm, CMSuper-Regular → sfrm);
  * число глифов.
Запуск: python3 e2e.py [class_size ...]   (по умолчанию 12 11 10)
"""
import os, sys, re, json, subprocess, collections, itertools, shutil, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "build", "lib"))
import warnings
warnings.filterwarnings("ignore")
from paths import *
import cmsfams as F
import pdfglyphs
from fontTools.ttLib import TTFont

TYPST = os.environ.get("TYPST", "typst")
FONTDIR = os.environ.get("E2E_FONTS", os.path.join(HERE, "..", "..", "fonts", "auto"))
BP = 72.0 / 72.27
W = HERE + "/e2e"
os.makedirs(W, exist_ok=True)
HELPER = os.path.join(HERE, "..", "..", "cm-super.typ")

# ── тексты ────────────────────────────────────────────────────────────────────
TEXT = {
    "ru": "Съешь же ещё этих мягких французских булок, да выпей чаю. Эхо Ъ Ё 1234567890 (скобки) «ёлочки» — тире",
    "ru2": "Теорема Лагранжа: f(x) = AV Te To Wave, 2024 год; Ёж, щавель? Ыы!",
    "en": "The quick brown fox jumps over the lazy dog. Waffle office fl ffl ff. AVATAR Toy Wa Yo 1234567890 (brackets) “Quotes” ‘single’",
    "sym": "Cost: £5 €10 § ¶ © ® ™ ° ± × ÷ † ‡ • ‰ ½ ¼ ¾ ‹ › ¿ ¡ ¢ ¥ ª º µ ¬ № 0 1 2 3 4 5 6 7 8 9 @ * + = < > | /",
    "sym_ru": "Cost: £5 €10 § ¶ © ® ™ ° ± × ÷ † ‡ • ½ ¼ ¾ ¢ ¥ ª º µ ¬ № 0 1 2 3 4 5 6 7 8 9 @ * + = < > | /",
    "en2": "Fifty-five: Typewriter, T. A. V. Yes? No! [a] (b) 5 + 3 = 8; “AV” — dash – en",
}

# ── стили: (ключ, LaTeX-объявления, шаблон Typst с {} вместо тела) ───────────────
STY = [
    ("rm", "", "{}"),
    ("rmfamily", r"\rmfamily", "rmfamily({})"),
    ("it", r"\itshape", "itshape({})"),
    ("sl", r"\slshape", "slshape({})"),
    ("sc", r"\scshape", "scshape({})"),
    ("scsl", r"\fontshape{scsl}\selectfont", "scslshape({})"),
    ("ui", r"\fontshape{ui}\selectfont", "ulshape({})"),
    ("bx", r"\bfseries", "bfseries({})"),
    ("bx it", r"\bfseries\itshape", "bfseries(itshape({}))"),
    ("bx sl", r"\bfseries\slshape", "bfseries(slshape({}))"),
    ("bx sc", r"\bfseries\scshape", "bfseries(scshape({}))"),
    ("b", r"\fontseries{b}\selectfont", "sbseries({})"),
    ("sf", r"\sffamily", "sffamily({})"),
    ("sf sl", r"\sffamily\slshape", "sffamily(slshape({}))"),
    ("sf it", r"\sffamily\itshape", "sffamily(itshape({}))"),
    ("sf sc", r"\sffamily\scshape", "sffamily(scshape({}))"),
    ("sf bx", r"\sffamily\bfseries", "sffamily(bfseries({}))"),
    ("sf bx sl", r"\sffamily\bfseries\slshape", "sffamily(bfseries(slshape({})))"),
    ("sf sbc", r"\sffamily\fontseries{sbc}\selectfont", "sffamily(sbcseries({}))"),
    ("tt", r"\ttfamily", "ttfamily({})"),
    ("tt it", r"\ttfamily\itshape", "ttfamily(itshape({}))"),
    ("tt sl", r"\ttfamily\slshape", "ttfamily(slshape({}))"),
    ("tt sc", r"\ttfamily\scshape", "ttfamily(scshape({}))"),
    ("tt bx", r"\ttfamily\bfseries", "ttfamily(bfseries({}))"),
    ("vtt", r"\fontfamily{cmvtt}\selectfont", "vttfamily({})"),
    ("vtt it", r"\fontfamily{cmvtt}\selectfont\itshape", "vttfamily(itshape({}))"),
    ("dh", r"\fontfamily{cmdh}\selectfont", 'textfont("dunhill", {})'),
    ("fib", r"\fontfamily{cmfib}\selectfont", 'textfont("fibonacci", {})'),
    ("fib sl", r"\fontfamily{cmfib}\selectfont\slshape", 'slshape(textfont("fibonacci", {}))'),
    ("funny", r"\fontfamily{cmfr}\selectfont", 'textfont("funny", {})'),
    ("funny it", r"\fontfamily{cmfr}\selectfont\itshape", 'itshape(textfont("funny", {}))'),
    ("ccr", r"\fontfamily{ccr}\selectfont", 'textfont("concrete", {})'),
    ("ccr sl", r"\fontfamily{ccr}\selectfont\slshape", 'slshape(textfont("concrete", {}))'),
    ("ccr it", r"\fontfamily{ccr}\selectfont\itshape", 'itshape(textfont("concrete", {}))'),
    ("ccr sc", r"\fontfamily{ccr}\selectfont\scshape", 'scshape(textfont("concrete", {}))'),
    ("br", r"\fontfamily{cmbr}\selectfont", 'textfont("bright", {})'),
    ("br sl", r"\fontfamily{cmbr}\selectfont\slshape", 'slshape(textfont("bright", {}))'),
    ("br sb", r"\fontfamily{cmbr}\fontseries{sb}\selectfont", 'sbseries(textfont("bright", {}))'),
    ("br bx", r"\fontfamily{cmbr}\bfseries", 'bfseries(textfont("bright", {}))'),
    ("tl", r"\fontfamily{cmtl}\selectfont", 'textfont("bright-tt", {})'),
    ("tl sl", r"\fontfamily{cmtl}\selectfont\slshape", 'slshape(textfont("bright-tt", {}))'),
    ("slx", r"\fontfamily{lcmss}\selectfont", 'textfont("slitex", {})'),
    ("slx sl", r"\fontfamily{lcmss}\selectfont\slshape", 'slshape(textfont("slitex", {}))'),
    ("slx bx", r"\fontfamily{lcmss}\selectfont\bfseries", 'bfseries(textfont("slitex", {}))'),
    ("slxtt", r"\fontfamily{lcmtt}\selectfont", 'textfont("slitex-tt", {})'),
    ("slx it", r"\fontfamily{lcmss}\selectfont\itshape", 'itshape(textfont("slitex", {}))'),
    ("slx bx sl", r"\fontfamily{lcmss}\selectfont\bfseries\slshape", 'bfseries(slshape(textfont("slitex", {})))'),
    ("slx In", r"\fontfamily{lcmss}\fontshape{In}\selectfont", 'nfss({}, family: "lcmss", shape: "In")'),
    ("slx Isl", r"\fontfamily{lcmss}\fontshape{Isl}\selectfont", 'nfss({}, family: "lcmss", shape: "Isl")'),
    ("slx bx In", r"\fontfamily{lcmss}\fontseries{bx}\fontshape{In}\selectfont", 'nfss({}, family: "lcmss", series: "bx", shape: "In")'),
    ("slxtt it", r"\fontfamily{lcmtt}\selectfont\itshape", 'itshape(textfont("slitex-tt", {}))'),
    ("slxtt sl", r"\fontfamily{lcmtt}\selectfont\slshape", 'slshape(textfont("slitex-tt", {}))'),
    ("slxtt In", r"\fontfamily{lcmtt}\fontshape{In}\selectfont", 'nfss({}, family: "lcmtt", shape: "In")'),
]
# размерные команды
SIZE_CMDS = ["tiny", "scriptsize", "footnotesize", "small", "normalsize", "large", "Large", "LARGE", "huge", "Huge"]


def latex_size(sz):
    if isinstance(sz, str):
        return "\\" + sz + " "
    s, b = sz
    return r"\fontsize{%s}{%s}\selectfont " % (s, b)


def typst_size(sz, body):
    if isinstance(sz, str):
        return "%s(%s, leading: false)" % (sz, body)
    s, b = sz
    return "fontsize(%s, %s, %s, leading: false)" % (s, b, body)


def typ_str(t):
    return '"' + t.replace("\\", "\\\\").replace('"', '\\"') + '"'


EXOTIC = {"dh", "fib", "fib sl", "funny", "funny it", "ccr", "ccr sl", "ccr it", "ccr sc", "br", "br sl", "br sb", "br bx", "tl", "tl sl",
          "slx", "slx sl", "slx bx", "slxtt", "sf sbc",
          "slx it", "slx bx sl", "slx In", "slx Isl", "slx bx In", "slxtt it", "slxtt sl", "slxtt In"}
CTX_ONLY = {"scsl": ("ru-skip",), "br": ("ru",), "br sl": ("ru",), "br sb": ("ru",), "br bx": ("ru",), "tl": ("ru",), "tl sl": ("ru",)}


def make_lines(cls):
    """список строк: dict(id, ctx, style, size, text, tex, typ)"""
    lines = []
    sty = {k: (d, t) for k, d, t in STY}
    n = 0

    def add(ctx, skey, size, tkey):
        nonlocal n
        d, t = sty[skey]
        text = TEXT[tkey]
        only = CTX_ONLY.get(skey)
        if only == ("ru-skip",) and ctx == "ru":
            return                      # T2A/cmr/m/scsl не объявлено: LaTeX подставит другое начертание
        if only and only != ("ru-skip",) and ctx not in only:
            return                      # Bright объявлен в LaTeX только для T2A
        if skey == "rm" and False:
            pass
        # LaTeX
        body_tex = d + latex_size(size) + text
        if ctx == "en":
            tex = r"\hbox{\foreignlanguage{english}{\frenchspacing %s}}" % body_tex
        else:
            tex = r"\hbox{%s}" % body_tex
        # Typst: размер снаружи, стиль внутри (как «{\large\itshape …}»)
        if skey in EXOTIC:
            typ_expr = t.replace("{}", typst_size(size, typ_str(text)))      # семейство «видит» кегль: размер — внутри
        else:
            typ_expr = typst_size(size, t.replace("{}", typ_str(text)))
        if ctx == "en":
            typ_expr = 'foreignlanguage("en", %s)' % typ_expr
        n += 1
        lines.append(dict(id=n, ctx=ctx, style=skey, size=size, text=tkey, tex=tex, typ=typ_expr))

    # 1) все стили × {ru, en} на normalsize
    for skey, _, _ in STY:
        add("ru", skey, "normalsize", "ru")
        add("en", skey, "normalsize", "en")
    # 2) основные стили × все команды кегля × {ru, en}
    main = ["rm", "it", "sl", "sc", "bx", "bx it", "sf", "sf bx", "tt", "tt it"]
    for skey in main:
        for sz in SIZE_CMDS:
            if sz == "normalsize":
                continue
            add("ru", skey, sz, "ru2")
            add("en", skey, sz, "en2")
    # 2b) символы TS1 и пунктуация
    for skey in ["rm", "it", "sl", "bx", "sf", "tt", "sc", "vtt", "bx sc", "tt sc"]:
        add("ru", skey, "normalsize", "sym_ru")
        add("en", skey, "normalsize", "sym")
    # 3) \fontsize{x}{y} для разных x: ближайший размер NFSS
    for skey in ["rm", "it", "bx", "sf", "tt"]:
        for x in [4, 5.5, 6.4, 8.6, 9.5, 11, 11.4, 11.5, 13, 13.2, 16, 18, 22, 27, 33, 40, 50]:
            add("ru", skey, (x, x * 1.2), "ru2")
            add("en", skey, (x, x * 1.2), "en2")
    # 4) экзотические семейства × все команды кегля
    for skey in ["dh", "fib", "funny", "funny it", "ccr", "br", "br sl", "br sb", "br bx", "tl", "slx", "slx sl", "slx bx", "slxtt", "sf sbc",
                 "slx it", "slx bx sl", "slx In", "slx Isl", "slx bx In", "slxtt it", "slxtt sl", "slxtt In"]:
        for sz in SIZE_CMDS:
            add("ru", skey, sz, "ru2")
            add("en", skey, sz, "en2")
        for x in [4, 11, 13, 30, 50]:
            add("ru", skey, (x, x * 1.2), "ru2")
            add("en", skey, (x, x * 1.2), "en2")
    # 5) смешанные строки: смена начертания/языка/кегля внутри строки, пробелы в разных шрифтах
    MIX = [
        (r"Текст {\itshape курсив} текст {\bfseries жирный} и {\scshape Капитель Small Caps} дальше {\sffamily Sans} {\ttfamily Mono} конец",
         'Текст #itshape("курсив") текст #bfseries("жирный") и #scshape("Капитель Small Caps") дальше #sffamily("Sans") #ttfamily("Mono") конец'),
        (r"Пробелы внутри групп: {\itshape курсив }текст{\bfseries  жирный } и {\slshape наклонный }конец",
         'Пробелы внутри групп: #itshape("курсив ")текст#bfseries("жирный ") и #slshape("наклонный ")конец'),
        (r"Теорема {\bfseries\itshape Лагранжа} (Joseph-Louis Lagrange, {\itshape fl.\ 1770}) — {\small small text {\tiny tiny}}",
         'Теорема #bfseries(itshape("Лагранжа")) (Joseph-Louis Lagrange, #itshape("fl. 1770")) — #small(leading: false)[small text #tiny(leading: false)[tiny]]'),
        (r"Русский текст и \foreignlanguage{english}{English fragment AVA Te} снова русский: To Ту",
         'Русский текст и #foreignlanguage("en", "English fragment AVA Te") снова русский: To Ту'),
        (r"\foreignlanguage{english}{English with {\itshape italic} and {\bfseries bold} Wa Te}",
         '#foreignlanguage("en", [English with #itshape("italic") and #bfseries("bold") Wa Te])'),
        (r"{\Large Большой {\small маленький} большой} {\huge Huge} {\footnotesize foot}",
         '#Large(leading: false)[Большой #small(leading: false)[маленький] большой] #huge(leading: false)[Huge] #footnotesize(leading: false)[foot]'),
        (r"AVAWATA {\itshape AVAWATA} {\bfseries AVAWATA} {\scshape AVAWATA avawata}",
         'AVAWATA #itshape("AVAWATA") #bfseries("AVAWATA") #scshape("AVAWATA avawata")'),
        (r"fi fl ff ffi ffl {\itshape fi fl ff ffi ffl} {\ttfamily fi fl ff} {\sffamily fi fl ff ffi}",
         'fi fl ff ffi ffl #itshape("fi fl ff ffi ffl") #ttfamily("fi fl ff") #sffamily("fi fl ff ffi")'),
    ]
    for k, (tx, ty) in enumerate(MIX):
        n += 1
        lines.append(dict(id=n, ctx="ru", style="mixed", size="normalsize", text=f"mix{k}", tex=r"\hbox{%s}" % tx, typ=ty, markup=True))
    return lines


def tex_doc(cls, lines, name):
    pre = [r"\documentclass[%dpt]{article}" % cls,
           r"\usepackage[T1,T2A]{fontenc}",
           r"\usepackage[utf8]{inputenc}",
           r"\usepackage[english,russian]{babel}",
           r"\usepackage[paperwidth=4100pt,paperheight=120pt,margin=10pt]{geometry}",
           r"\pagestyle{empty}\setlength{\parindent}{0pt}\setlength{\parskip}{0pt}",
           r"\frenchspacing",
           r"\begin{document}", r"\raggedright"]
    out = list(pre)
    # по ~600 строк на странице
    for i, ln in enumerate(lines):
        out.append(r"\noindent" + ln["tex"] + r"\par\newpage")
    out.append(r"\end{document}")
    p = f"{W}/{name}.tex"
    open(p, "w").write("\n".join(out))
    env = dict(os.environ)
    env["TFMFONTS"] = TFMDIR + "//:"
    env["MKTEXTFM"] = "0"
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{name}.tex"], cwd=W, capture_output=True, env=env)
    if not os.path.exists(f"{W}/{name}.pdf"):
        raise RuntimeError("pdflatex: " + r.stdout.decode("utf-8", "replace")[-3000:])
    return f"{W}/{name}.pdf", f"{W}/{name}.log"


def typ_doc(cls, lines, name):
    out = ['#import "cm-super.typ": *',
           '#set page(width: 4100pt, height: 120pt, margin: 10pt)',
           '#set par(justify: false)',
           '#show: cm-super.with(size: %d, lang: "ru")' % cls]
    for i, ln in enumerate(lines):
        if i:
            out.append("#pagebreak()")
        out.append(ln["typ"] if ln.get("markup") else "#" + ln["typ"])
        out.append("")
    p = f"{W}/{name}.typ"
    shutil.copy(HELPER, f"{W}/cm-super.typ")
    open(p, "w").write("\n".join(out))
    r = subprocess.run([TYPST, "compile", "--ignore-system-fonts", "--font-path", FONTDIR, p, f"{W}/{name}.pdf"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("typst: " + r.stderr.decode("utf-8", "replace")[-3000:])
    return f"{W}/{name}.pdf", r.stderr.decode("utf-8", "replace")


# ── имена шрифтов ─────────────────────────────────────────────────────────────
CAPS2BASE = {"sfcc": "sfrm", "sfsc": "sfsl", "sfxc": "sfbx", "sfoc": "sfbl", "sftc": "sftt", "sfocc": "sform"}


def ps2face():
    m = {}
    for face, (grp, label, *_r) in F.FACE.items():
        prefix = F.GROUP[grp][1]
        m[f"{prefix}-{label.replace(' ', '')}"] = face
    return m


PS2FACE = ps2face()


def latex_face(fontname):
    n = fontname.split("+")[-1]
    f = re.sub(r"\d+$", "", n).lower()
    return CAPS2BASE.get(f, f)


def typst_face(fontname):
    n = fontname.split("+")[-1]
    return PS2FACE.get(n, "?" + n)


def extract_lines(pdf):
    """-> [[(x, text, fontname, cid, fontsize)]] — строки сверху вниз по всем страницам"""
    pages = pdfglyphs.extract(pdf, with_size=True)
    out = []
    for pg in pages:
        # одна строка на страницу; если несколько y-групп (не должно быть) — склеиваем слева направо
        row = sorted((g for ln in pg for g in ln), key=lambda g: g[0])
        out.append(row)
    return out


def main():
    classes = [int(x) for x in sys.argv[1:]] or [12, 11, 10]
    for cls in classes:
        lines = make_lines(cls)
        print(f"== класс {cls} pt: {len(lines)} строк", flush=True)
        name = f"c{cls}"
        lp, ll = tex_doc(cls, lines, name + "_l")
        tp, terr = typ_doc(cls, lines, name + "_t")
        if terr.strip():
            print("typst stderr:", terr[:800])
        lat = extract_lines(lp)
        typ = extract_lines(tp)
        print("   строк в PDF: LaTeX", len(lat), "Typst", len(typ), flush=True)
        json.dump(dict(lat=lat, typ=typ), open(f"{W}/{name}_glyphs.json", "w"))
        json.dump(lines, open(f"{W}/{name}_lines.json", "w"), ensure_ascii=False)
    print("ok")


if __name__ == "__main__":
    main()
