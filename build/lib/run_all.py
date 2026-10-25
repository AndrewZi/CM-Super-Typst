"""run_all.py — параллельная сборка всех шрифтов. Запуск: python3 -I run_all.py [var|static|all] [процессов]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(__file__))
from multiprocessing import Pool
import jobs

def work(j):
    return jobs.run_job(j)

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    js = jobs.all_jobs(include_var=what in ("var", "all"), include_static=what in ("static", "all"))
    # тяжёлые сначала
    js.sort(key=lambda j: (j["mode"] != "var", j["face"], j.get("tok") or ""))
    os.makedirs(jobs.OUTROOT, exist_ok=True)
    log = open(os.path.join(jobs.OUTROOT, f"build_log_{what}.jsonl"), "w")
    t0 = time.time()
    n_ok = n_bad = 0
    with Pool(nproc) as p:
        for k, r in enumerate(p.imap_unordered(work, js), 1):
            log.write(json.dumps(r, ensure_ascii=False) + "\n"); log.flush()
            if r["ok"]:
                n_ok += 1
            else:
                n_bad += 1
                print("FAIL", r["job"], r["err"][-400:], flush=True)
            if k % 10 == 0 or k == len(js):
                print(f"{k}/{len(js)} ok={n_ok} bad={n_bad} {time.time()-t0:.0f}s", flush=True)
    print("DONE", n_ok, n_bad, f"{time.time()-t0:.0f}s", flush=True)
