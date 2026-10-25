# -*- coding: utf-8 -*-
"""Собирает pdfLaTeX-тест для одной «семьи/формы/размера» и извлекает позиции глифов."""
import os, sys, subprocess, json, shutil, textwrap
sys.path.insert(0, os.path.dirname(__file__))
import texts

PRE = r"""\documentclass[%(cls)s]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1,T2A]{fontenc}
\usepackage{textcomp}
\usepackage[russian]{babel}
\usepackage[paperwidth=400mm,paperheight=%(h)smm,margin=10mm,top=10mm,left=10mm]{geometry}
\pagestyle{empty}\parindent0pt\frenchspacing
\begin{document}
%(sel)s
%(body)s
\end{document}
"""

def tex_escape(s):
    out = []
    for ch in s:
        out.append({"$": r"\$", "%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "\\": r"\textbackslash{}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}.get(ch, ch))
    return "".join(out)


def make_tex(lines, sel, cls="12pt", h=None):
    body = "\n".join(r"\noindent\hbox{%s}\par\vspace{3pt}" % tex_escape(ln) for ln in lines)
    h = h or (30 + 12 * len(lines))
    return PRE % dict(cls=cls, sel=sel, body=body, h=h)

def compile_tex(tex, workdir, name):
    os.makedirs(workdir, exist_ok=True)
    p = os.path.join(workdir, name + ".tex")
    open(p, "w", encoding="utf-8").write(tex)
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", name + ".tex"], cwd=workdir, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout.decode("utf-8", "replace")[-2500:])
    return os.path.join(workdir, name + ".pdf")

if __name__ == "__main__":
    wd = sys.argv[1]
    sel = sys.argv[2] if len(sys.argv) > 2 else ""
    pdf = compile_tex(make_tex(texts.LINES, sel), wd, "t")
    print(pdf)
