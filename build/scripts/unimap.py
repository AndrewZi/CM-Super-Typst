"""unimap.py — сопоставление имён глифов CM-Super с Unicode по таблицам самого LaTeX (*.def: команда -> позиция, *.dfu: Unicode -> команда)."""
import re, subprocess, json, sys
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))
from tfmlib import read_enc

from paths import SP, FULL, ENCDIR
ENCS = {"t1": "t1", "t2a": "t2a", "t2b": "t2b", "t2c": "t2c", "x2": "x2", "ts1": "ts1"}


def kp(name):
    return subprocess.check_output(["kpsewhich", name], text=True).strip()


def num(s):
    s = s.strip()
    if s.startswith('"'):
        return int(s[1:], 16)
    if s.startswith("'"):
        return int(s[1:], 8)
    if s.startswith("`"):
        r = s[1:]
        if r.startswith("\\"):
            r = r[1:]
        return ord(r[0])
    return int(s)


def parse_def(enc):
    """команда -> позиция (только \\DeclareTextSymbol)"""
    txt = open(kp(f"{enc}enc.def"), encoding="latin-1").read()
    txt = re.sub(r"(?m)%.*$", "", txt)
    out = {}
    for m in re.finditer(r"\\DeclareTextSymbol\s*\{(\\[A-Za-z@]+)\}\s*\{[^}]*\}\s*\{([^}]*)\}", txt):
        try:
            out[m.group(1)] = num(m.group(2))
        except (ValueError, IndexError):
            pass
    comp = {}
    for m in re.finditer(r"\\DeclareTextComposite\s*\{(\\[^}]*)\}\s*\{[^}]*\}\s*\{([^}]*)\}\s*\{([^}]*)\}", txt):
        try:
            comp[(m.group(1), m.group(2))] = num(m.group(3))
        except (ValueError, IndexError):
            pass
    return out, comp


def parse_dfu(enc):
    txt = open(kp(f"{enc}enc.dfu"), encoding="latin-1").read()
    txt = re.sub(r"(?m)%.*$", "", txt)
    return {int(m.group(1), 16): m.group(2) for m in re.finditer(r"\\DeclareUnicodeCharacter\s*\{([0-9A-Fa-f]+)\}\s*\{(.*)\}\s*$", txt, re.M)}


def build():
    res = {}   # glyphname -> set of unicode (из LaTeX)
    detail = {}
    for enc in ENCS:
        _, names = read_enc(f"{ENCDIR}/cm-super-{enc}.enc")
        sym, comp = parse_def(enc)
        dfu = parse_dfu(enc)
        for u, cmd in dfu.items():
            cmd = cmd.strip()
            if cmd in sym:
                slot = sym[cmd]
                if slot < 256 and names[slot] != ".notdef":
                    res.setdefault(names[slot], set()).add(u)
                    detail.setdefault(names[slot], []).append((enc, slot, u, cmd))
            else:
                # составной вид: \'e, \"{a} ...
                m = re.fullmatch(r"(\\[^A-Za-z@\s]|\\[A-Za-z@]+\s*)\s*\{?\s*(\\?[A-Za-z@]+)\s*\}?", cmd)
                if m:
                    key = (m.group(1).strip(), m.group(2))
                    if key in comp and comp[key] < 256 and names[comp[key]] != ".notdef":
                        res.setdefault(names[comp[key]], set()).add(u)
                        detail.setdefault(names[comp[key]], []).append((enc, comp[key], u, cmd))
    return res, detail


if __name__ == "__main__":
    res, detail = build()
    ff = json.load(open(f"{FULL}/probe/sfrm1200.json"))
    unm = [k for k, v in ff.items() if v in (None, -1, 0)]
    print("глифов с Unicode из LaTeX:", len(res))
    print("из 99 безымянных получили Unicode:", sum(1 for k in unm if k in res))
    for k in sorted(unm):
        print(f"  {k:28s}", [f"U+{u:04X}" for u in sorted(res.get(k, []))], detail.get(k, [])[:2])
    dis = [(k, ff[k], sorted(res[k])) for k in res if k in ff and ff[k] not in (None, -1, 0) and ff[k] not in res[k]]
    print("расхождения с AGL:", len(dis))
    for x in dis[:60]:
        print("  ", x[0], hex(x[1]), [hex(u) for u in x[2]])
