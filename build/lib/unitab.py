"""unitab.py — таблица Unicode -> имя глифа для CM-Super.
Источники (по убыванию приоритета): ручные переопределения; данные самого LaTeX (*enc.def + *enc.dfu: Unicode -> команда -> позиция -> имя глифа
из cm-super-*.enc); имена AGL, которые разобрал FontForge (pfbinfo.json); псевдонимы (NBSP, мягкий перенос, пробелы Unicode)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from paths import *
import unimap
from assemble import SPACES

# глифы-«акценты для текста» из TS1 — для отдельных знаков U+00B4 и т. п.
OVERRIDE = {0x00B4: "acute.ts1", 0x02D8: "breve.ts1", 0x02C7: "caron.ts1", 0x00A8: "dieresis.ts1", 0x00AF: "macron.ts1", 0x02DD: "hungarumlaut.ts1",
            0x1E9E: "SS"}
# кириллические буквы, которые в T2A рисуются латинскими глифами
CYR_AS_LATIN = {0x0406: "I", 0x0456: "i", 0x0408: "J", 0x0458: "j"}
ALIAS = {0x00A0: "space", 0x2010: "hyphen", 0x2011: "hyphen"}

_cache = {}


def unicode_table(base_pfb):
    if base_pfb in _cache:
        return _cache[base_pfb]
    pi = json.load(open(FULL + "/pfbinfo.json"))
    gl = pi[base_pfb]["glyphs"]
    names = set(gl)
    tab = {}
    # 1) AGL от FontForge
    for n, (w, u, bb) in gl.items():
        if u and u > 0 and u <= 0x10FFFF and n != ".notdef":
            tab.setdefault(u, n)
    # 2) данные LaTeX для имён, у которых Unicode ещё нет (и не затрагивая уже занятые коды)
    res, detail = unimap.build()
    for n, us in res.items():
        if n not in names:
            continue
        for u in us:
            if u not in tab:
                tab[u] = n
    # 3) переопределения и псевдонимы
    for u, n in {**OVERRIDE, **CYR_AS_LATIN, **ALIAS}.items():
        if n in names:
            tab[u] = n
    for n, (u, f) in SPACES.items():
        tab[u] = n
    # U+200C (ZWNJ) — compwordmark T1/T2 (afii61664)
    if "afii61664" in names:
        tab[0x200C] = "afii61664"
    _cache[base_pfb] = tab
    return tab


if __name__ == "__main__":
    t = unicode_table("sfrm1200")
    print(len(t))
    for u in (0x41, 0x27, 0x60, 0x22, 0x2014, 0x2013, 0xA0, 0xAD, 0xB4, 0x406, 0x451, 0x2116, 0x2026, 0x2003, 0x1E9E, 0xFB01, 0x2019, 0x201C, 0xAB):
        print(hex(u), t.get(u))
