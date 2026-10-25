"""tfmcache.py — разбор всех TFM один раз и кэш в pickle (формат: имя -> результат tfmlib.read_tfm)."""
import os, pickle, sys, glob
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))
import tfmlib
from paths import *

CACHE = FULL + "/tfm_all.pkl"
_mem = None


def _parse(path):
    try:
        return os.path.basename(path)[:-4], tfmlib.read_tfm(path)
    except Exception as e:
        return os.path.basename(path)[:-4], {"error": str(e)}


def build():
    files = sorted(glob.glob(TFMDIR + "/*.tfm"))
    with ProcessPoolExecutor(2) as ex:
        res = dict(ex.map(_parse, files, chunksize=20))
    pickle.dump(res, open(CACHE, "wb"))
    return res


def load():
    global _mem
    if _mem is None:
        _mem = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else build()
    return _mem


if __name__ == "__main__":
    r = build()
    bad = [k for k, v in r.items() if "error" in v]
    print("TFM разобрано:", len(r), "ошибок:", len(bad), bad[:5])
