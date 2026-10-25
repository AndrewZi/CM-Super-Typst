"""jobs.py — список всех сборок и запуск (последовательно/параллельно)."""
import os, sys, json, time, traceback
sys.path.insert(0, os.path.dirname(__file__))
from paths import *
import cmsfams as F
import build as B

OUTROOT = OUT


def all_jobs(include_static=True, include_var=True):
    ad = F.all_designs()
    jobs = []
    for face in sorted(F.FACE):
        grp = F.FACE[face][0]
        if include_var:
            jobs.append(dict(face=face, mode="var", tok=None, outdir=f"{OUTROOT}/auto"))
        if include_static and B.group_multi(grp):
            for d in ad[face]:
                jobs.append(dict(face=face, mode="static", tok=d["tok"], outdir=f"{OUTROOT}/static/{F.size_label(d['ds'])}", label=F.size_label(d["ds"])))
    return jobs


def job_names(j):
    ad = F.all_designs()
    d = None
    if j["mode"] == "static":
        d = [x for x in ad[j["face"]] if x["tok"] == j["tok"]][0]
    else:
        d = ad[j["face"]][0]
    nm = B.names_for(j["face"], j["mode"], d)
    return nm["typo_family"], nm["sty"], nm["ps"] + ".otf"


def run_job(j):
    ad = F.all_designs()
    d = None
    if j["mode"] == "static":
        d = [x for x in ad[j["face"]] if x["tok"] == j["tok"]][0]
    t = time.time()
    try:
        info = B.build_font(j["face"], j["mode"], j["outdir"], d, verbose=False, tag=f"{j['face']}_{j['mode']}_{j['tok'] or 'var'}")
        return dict(job=j, ok=True, info={k: v for k, v in info.items() if k != "stats"}, stats=info["stats"], secs=time.time() - t)
    except Exception as e:
        return dict(job=j, ok=False, err=traceback.format_exc()[-1500:], secs=time.time() - t)


if __name__ == "__main__":
    js = all_jobs()
    print(len(js), "jobs;", sum(1 for j in js if j["mode"] == "var"), "var,", sum(1 for j in js if j["mode"] == "static"), "static")
    seen = {}
    dup = 0
    for j in js:
        fam, sty, fn = job_names(j)
        key = (fam, sty)
        if key in seen:
            dup += 1
            print("DUP", key, j, seen[key])
        seen[key] = j
        pk = (j["outdir"], fn)
    files = {}
    for j in js:
        fam, sty, fn = job_names(j)
        k = (j["outdir"], fn)
        if k in files:
            print("FILE DUP", k, j, files[k])
        files[k] = j
    print("dups", dup, "families", len({k[0] for k in seen}))
    fams = {}
    for (fam, sty), j in seen.items():
        fams.setdefault(fam, []).append(sty)
    for fam in sorted(fams):
        print(f"  {fam}: {', '.join(sorted(fams[fam]))}")
