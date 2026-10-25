import sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from paths import *
import cmsmetrics
designs = json.load(open(FULL + "/designs.json"))
pfbi = json.load(open(FULL + "/pfbinfo.json"))
tot = collections.Counter()
worst = []
nokern = []
for key, tf in sorted(designs.items()):
    pfb = key.split("|")[0]
    m = cmsmetrics.design_metrics(tf)
    glyphs = pfbi[pfb]["glyphs"]
    missing_adv = [g for g in glyphs if g not in m["adv"] and g != ".notdef"]
    extra = [g for g in m["adv"] if g not in glyphs]
    # сравнение ширины TFM и PFB (в единицах 1/1000)
    dif = []
    for g, w in m["adv"].items():
        if g in glyphs:
            d = w * 1000 - glyphs[g][0]
            dif.append((abs(d), g, d))
    dif.sort(reverse=True)
    tot["designs"] += 1
    tot["conf"] += len(m["conflicts"]); tot["kconf"] += len(m["kconflicts"])
    if m["other_ops"]: tot["otherops"] += 1
    if extra: tot["extra"] += 1; print("extra", key, extra[:5])
    if dif and dif[0][0] > 1.5: worst.append((key, dif[0], len([x for x in dif if x[0] > 1.5])))
    if not m["kern"]: nokern.append(key)
    tot["miss_%s" % ",".join(sorted(missing_adv)[:4])] += 1
print(tot.most_common(20))
print("max TFM-PFB width diffs >1.5/1000:", len(worst))
for w in worst[:25]: print("  ", w)
print("no kern:", nokern)
