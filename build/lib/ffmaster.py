# ffmaster.py — этап FontForge: склейка контуров нескольких .pfb в один OpenType (CFF) с суффиксами имён глифов.
# Запуск: fontforge -lang=py -script ffmaster.py spec.json
# spec.json: {"out": "...otf", "em": 2000,
#             "layers": [{"pfb": "...pfb", "suffix": ""}, {"pfb": "...pfb", "suffix": ".d0500"}, {"pfb": "...", "suffix": ".cc"}, ...],
#             "extra_empty": ["uni2003", ...]}      # пустые глифы (пробелы Unicode), создаются в каждом слое
# Первый слой — основа (его глифы остаются без суффикса). Остальные слои копируются как name+suffix.
import fontforge
import json
import sys

spec = json.load(open(sys.argv[1]))
EM = spec.get("em", 2000)
layers = spec["layers"]

base = fontforge.open(layers[0]["pfb"])
base.em = EM
base_names = [g.glyphname for g in base.glyphs()]
loaded = {layers[0]["pfb"]: base}
n_copied = 0
for lay in layers[1:]:
    p, suf = lay["pfb"], lay["suffix"]
    src = loaded.get(p)
    if src is None:
        src = fontforge.open(p)
        src.em = EM
        loaded[p] = src
    names = [g.glyphname for g in src.glyphs() if g.glyphname != ".notdef"]
    for name in names:
        src.selection.none()
        src.selection.select(name)
        src.copy()
        g = base.createChar(-1, name + suf)
        base.selection.none()
        base.selection.select(name + suf)
        base.paste()
        n_copied += 1
# пустые глифы для Unicode-пробелов: по одному на слой «дизайн» (суффиксы без .cc)
suffixes = [lay["suffix"] for lay in layers if ".cc" not in lay["suffix"]]
for suf in suffixes:
    for nm in spec.get("extra_empty", []):
        g = base.createChar(-1, nm + suf)
        g.width = 500
# безымянные (без юникода) глифы с суффиксом не должны попасть в cmap: обнуляем юникод у всех, кроме основного слоя
base_set = set(base_names)
for g in base.glyphs():
    if g.glyphname not in base_set and g.unicode != -1:
        g.unicode = -1
# двойники глифов («имя.lat»): те же контуры, другая ширина (латинский контекст)
n_al = 0
for al in spec.get("aliases", []):
    base.selection.none()
    base.selection.select(al["src"])
    base.copy()
    g = base.createChar(-1, al["dst"])
    base.selection.none()
    base.selection.select(al["dst"])
    base.paste()
    n_al += 1
# синтетические глифы: n копий глифа base со смещением step (многоточие LaTeX: «.» + \kern\fontdimen3, три раза)
n_syn = 0
for sy in spec.get("synth", []):
    g = base[sy["glyph"]]
    g.clear()
    for k in range(int(sy["n"])):
        g.addReference(sy["base"], (1, 0, 0, 1, k * int(sy["step"]), 0))
    n_syn += 1
# ширины (в единицах em=EM), заданные снаружи: меняют только advance, контур не сдвигается
n_w = 0
for name, w in spec.get("widths", {}).items():
    try:
        base[name].width = int(w)
        n_w += 1
    except Exception as e:
        print("width fail", name, e, file=sys.stderr)
flags = ("opentype",)
base.generate(spec["out"], flags=flags)
print("ffmaster: layers", len(layers), "glyphs", len(list(base.glyphs())), "copied", n_copied, "widths", n_w, "synth", n_syn, "aliases", n_al, file=sys.stderr)
