# -*- coding: utf-8 -*-
"""nfss_probe.py — «эталон» выбора шрифта настоящим LaTeX (NFSS): для каждого объявления \\DeclareFontShape
(кодировка/семейство/серия/начертание) и сетки размеров получает имя TFM (+ at-размер), которое выбирает \\selectfont.
Результат: nfss2/probe.json = {"ENC/fam/ser/shp": {"size": "tfmname [at X]"}}"""
import os, sys, json, subprocess, re, collections, shutil, concurrent.futures as cf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "lib"))
from paths import TFMDIR
HERE = os.path.dirname(os.path.abspath(__file__))
W = HERE + "/nfss2"
os.makedirs(W, exist_ok=True)
LISTED = [5, 6, 7, 8, 9, 10, 10.95, 12, 14.4, 17.28, 20.74, 24.88, 29.86, 35.83]
SLITEX = [7, 8, 10, 12, 13.82, 16.59, 19.907, 23.89, 28.66, 34.4, 41.28]
mids = [(LISTED[i] + LISTED[i + 1]) / 2 for i in range(len(LISTED) - 1)]
sizes = {x / 4 for x in range(16, 4 * 44 + 1)} | set(LISTED) | set(SLITEX)
for m in mids:
    for dx in (-0.02, 0.02):
        sizes.add(round(m + dx, 3))
sizes = sorted(sizes)


def fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def decls():
    out = []
    for line in open(HERE + "/nfss1/nfss.txt"):
        if line.startswith("@@DFS "):
            key, spec, load = line[6:].rstrip("\n").split(" @@ ")
            out.append((key, spec))
    return out


def run_one(i, key, encs_ok=("T1", "T2A", "TS1")):
    enc, fam, ser, shp = key.split("/")
    tex = [r"\documentclass{article}", r"\usepackage[T1,T2A,T2B,T2C,X2]{fontenc}", r"\usepackage{textcomp}",
           r"\newwrite\lf\immediate\openout\lf=p%d.txt" % i,
           r"\def\probe#1{\fontsize{#1}{#1}\usefont{%s}{%s}{%s}{%s}\immediate\write\lf{#1 \fontname\font}}" % (enc, fam, ser, shp),
           r"\begin{document}"]
    tex += [r"\probe{%s}" % fmt(s) for s in sizes]
    tex += [r"\end{document}"]
    open(f"{W}/p{i}.tex", "w").write("\n".join(tex))
    env = dict(os.environ); env["TFMFONTS"] = TFMDIR + "//:"; env["MKTEXTFM"] = "0"
    subprocess.run(["pdflatex", "-interaction=batchmode", f"p{i}.tex"], cwd=W, capture_output=True, env=env)
    res = {}
    try:
        for ln in open(f"{W}/p{i}.txt"):
            s, name = ln.strip().split(" ", 1)
            res[s] = name
    except FileNotFoundError:
        pass
    for ext in ("aux", "log", "pdf", "tex", "txt"):
        try:
            os.remove(f"{W}/p{i}.{ext}")
        except OSError:
            pass
    return key, res


def main():
    encs = tuple(os.environ.get("PROBE_ENCS", "T1,T2A,TS1").split(","))
    ds = [(i, k) for i, (k, s) in enumerate(decls()) if k.split("/")[0] in encs]
    out = {}
    with cf.ThreadPoolExecutor(2) as ex:
        futs = [ex.submit(run_one, i, k) for i, k in ds]
        for n, f in enumerate(futs):
            k, r = f.result()
            out[k] = r
            if n % 20 == 0:
                print(n, len(ds), k, flush=True)
    json.dump(out, open(W + "/" + os.environ.get("PROBE_OUT", "probe.json"), "w"), indent=0)
    print("done", len(out))


if __name__ == "__main__":
    main()
