# -*- coding: utf-8 -*-
"""e2e_v.py — вертикальные метрики: шаг строк (\\baselineskip) в LaTeX и Typst для всех команд кегля классов 10/11/12 pt."""
import os, sys, subprocess, shutil, json, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import e2e, pdfglyphs
W = e2e.W
SIZES = e2e.SIZE_CMDS
LINES = ["Съешь же ещё этих мягких", "The quick brown fox jumps", "Теорема Лагранжа Te AV", "Hxg 123 (скобки) Ёжик"]


def run(cls):
    tex = [r"\documentclass[%dpt]{article}" % cls, r"\usepackage[T1,T2A]{fontenc}", r"\usepackage[utf8]{inputenc}",
           r"\usepackage[english,russian]{babel}", r"\usepackage[paperwidth=2000pt,paperheight=400pt,margin=10pt]{geometry}",
           r"\pagestyle{empty}\setlength{\parindent}{0pt}\setlength{\parskip}{0pt}", r"\begin{document}", r"\raggedright"]
    for sz in SIZES:
        body = r"\\ ".join(LINES)
        tex.append(r"{\%s %s\par}\newpage" % (sz, body))
    tex.append(r"\end{document}")
    open(f"{W}/v{cls}_l.tex", "w").write("\n".join(tex))
    env = dict(os.environ); env["TFMFONTS"] = e2e.TFMDIR + "//:"
    subprocess.run(["pdflatex", "-interaction=nonstopmode", f"v{cls}_l.tex"], cwd=W, capture_output=True, env=env)
    typ = ['#import "cm-super.typ": *', '#set page(width: 2000pt, height: 400pt, margin: 10pt)', '#set par(justify: false)',
           '#show: cm-super.with(size: %d, lang: "ru")' % cls]
    for i, sz in enumerate(SIZES):
        if i:
            typ.append("#pagebreak()")
        body = " \\ ".join(LINES)
        typ.append("#%s[%s]" % (sz, body))
    shutil.copy(e2e.HELPER, f"{W}/cm-super.typ")
    open(f"{W}/v{cls}_t.typ", "w").write("\n".join(typ))
    r = subprocess.run([e2e.TYPST, "compile", "--ignore-system-fonts", "--font-path", e2e.FONTDIR, f"{W}/v{cls}_t.typ", f"{W}/v{cls}_t.pdf"], capture_output=True)
    if r.returncode:
        print(r.stderr.decode()[-1500:]); sys.exit(1)
    res = []
    A = pdfglyphs.extract(f"{W}/v{cls}_l.pdf", with_size=True, with_y=True)
    B = pdfglyphs.extract(f"{W}/v{cls}_t.pdf", with_size=True, with_y=True)
    worst = 0.0
    for sz, pa, pb in zip(SIZES, A, B):
        ya = [ln[0][5] for ln in pa]
        yb = [ln[0][5] for ln in pb]
        pa_ = [ya[i] - ya[i + 1] for i in range(len(ya) - 1)]
        pb_ = [yb[i] - yb[i + 1] for i in range(len(yb) - 1)]
        fsa = pa[0][0][4] / e2e.BP; fsb = pb[0][0][4] / e2e.BP
        d = max(abs(x - y) for x, y in zip(pa_, pb_)) if pa_ and len(pa_) == len(pb_) else 999
        worst = max(worst, d)
        res.append((sz, round(fsa, 3), round(fsb, 3), [round(x / e2e.BP, 3) for x in pa_], [round(x / e2e.BP, 3) for x in pb_], round(d, 4)))
    return res, worst


if __name__ == "__main__":
    for cls in [int(x) for x in sys.argv[1:]] or [12, 11, 10]:
        res, worst = run(cls)
        print(f"класс {cls}: макс. расхождение шага строк {worst:.4f} bp")
        for r in res:
            print("  ", r)
