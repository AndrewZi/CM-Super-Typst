"""assemble.py — этап fontTools: из «сырого» OTF (FontForge) делает готовый шрифт для Typst.
Что делает: ширины и кернинг из TFM, лигатуры/капитель/oldstyle-цифры/русские тире (GSUB), cmap, имена, OS/2, post, hhea,
и, для «авто-размерных» шрифтов, ось opsz (fvar) + FeatureVariations (rvrn), переключающие рисунок по кеглю."""
import os, sys, math, collections, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._f_v_a_r import Axis
from fontTools.otlLib import builder as ob
from fontTools.varLib.featureVars import addFeatureVariations
from fontTools.pens.boundsPen import BoundsPen

UPEM = 2000
TEX2BP = 72.0 / 72.27
AXIS_MIN, AXIS_DEF, AXIS_MAX = 5.0, 12.0, 36.0
CYR_LANGS = ["RUS ", "UKR ", "BEL ", "BGR ", "SRB ", "MKD ", "KAZ ", "KIR ", "TAJ ", "MNG ", "TAT ", "BSH ", "CHU ", "SAH ", "ABK ", "OSS ", "CHE ", "CSL "]
CYR_PAIRS = [("emdash", "emdash.cyr"), ("guillemotleft", "guillemotleft.cyr"), ("guillemotright", "guillemotright.cyr")]
ONUM = [("zero", "zerooldstyle"), ("one", "oneoldstyle"), ("two", "twooldstyle"), ("three", "threeoldstyle"), ("four", "fouroldstyle"),
        ("five", "fiveoldstyle"), ("six", "sixoldstyle"), ("seven", "sevenoldstyle"), ("eight", "eightoldstyle"), ("nine", "nineoldstyle"),
        ("dollar", "dollaroldstyle"), ("cent", "centoldstyle")]
# Unicode-пробелы: имя глифа -> (код, формула ширины от QUAD/ширин глифов)
SPACES = {"uni2000": (0x2000, "q/2"), "uni2001": (0x2001, "q"), "uni2002": (0x2002, "q/2"), "uni2003": (0x2003, "q"),
          "uni2004": (0x2004, "q/3"), "uni2005": (0x2005, "q/4"), "uni2006": (0x2006, "q/6"), "uni2007": (0x2007, "zero"),
          "uni2008": (0x2008, "period"), "uni2009": (0x2009, "q/6"), "uni200A": (0x200A, "q/12"), "uni200B": (0x200B, "0"),
          "uni200D": (0x200D, "0"), "uni202F": (0x202F, "q/6"), "uni205F": (0x205F, "q*4/18"), "uni00AD": (0x00AD, "0")}
# «невидимые по умолчанию» символы Unicode (ZWNJ, ZWSP, ZWJ, мягкий перенос): шейпер скрывает их и обнуляет ширину ТОЛЬКО пока глиф не подменён в GSUB.
# Поэтому у них нет вариантов по размеру (rvrn) и нет капитальных подмен (smcp/c2sc).
NO_VARIANT = {"afii61664", "uni200B", "uni200D", "uni00AD"}
EXTRA_EMPTY = list(SPACES)


def rnd(x):
    return int(math.floor(x + 0.5))


class Layer:
    """Один слой глифов в итоговом шрифте: рисунок (дизайн-размер) или его капитель."""

    def __init__(self, suffix, metrics, names, caps=False, design_key=None, rng=None):
        self.suffix, self.m, self.names, self.caps, self.key, self.rng = suffix, metrics, set(names), caps, design_key, rng

    def gn(self, n):
        return n + self.suffix


def layer_advances(layer):
    """{имя глифа в слое: ширина в em} — из TFM, а где TFM нет — None (оставим ширину из .pfb)"""
    m = layer.m
    out = {}
    q = m["quad"]
    for n in layer.names:
        if n == "space":
            out[n] = m["space"]
        elif n in m["adv"]:
            out[n] = m["adv"][n]
    return out


def space_widths(layer):
    m = layer.m
    q = m["quad"]
    res = {}
    zero = m["adv"].get("zero", 0.5)
    period = m["adv"].get("period", 0.278)
    for nm, (u, f) in SPACES.items():
        if nm not in layer.names:
            continue
        env = {"q": q, "zero": zero, "period": period}
        res[nm] = eval(f, {}, env) if f != "0" else 0.0
    return res


def build_cmap(base_names, uni_table):
    cm = {}
    for u, n in uni_table.items():
        if n in base_names:
            cm[u] = n
    return cm


def lig_rules(m, names, sfx):
    """Правила liga (простые LIG из TFM): {(a,b,...): результат}. Многошаговые цепочки раскрываются до исходных последовательностей."""
    pairs = dict(m["lig"])
    for k, v in m["lig_cyr"].items():
        pairs.setdefault(k, v)
    srcs = collections.defaultdict(set)         # результат -> множество последовательностей входных глифов (кортежи)
    for (a, b), c in pairs.items():
        if c in (a, b):
            continue
        srcs[c].add(((a,), (b,)))
    memo = {}

    def seqs(g, depth=0):
        if g in memo:
            return memo[g]
        res = {(g,)}
        if depth < 4 and g in srcs:
            for (sa, sb) in srcs[g]:
                for x in seqs(sa[0], depth + 1):
                    for y in seqs(sb[0], depth + 1):
                        res.add(x + y)
        memo[g] = res
        return res
    rules = {}
    for (a, b), c in pairs.items():
        if c in (a, b):
            continue
        for x in seqs(a):
            for y in seqs(b):
                seq = x + y
                if all(s in names for s in seq) and c in names:
                    rules[tuple(s + sfx for s in seq)] = c + sfx
    # убрать правила, у которых вход совпадает с выходом из одного глифа
    return {k: v for k, v in rules.items() if len(k) >= 2}


def upper_to_lower_map(cmap, glyph_names):
    """для c2sc: имя заглавного глифа -> имя строчного (по Unicode)"""
    res = {}
    for u, n in cmap.items():
        ch = chr(u)
        if not ch.isupper():
            continue
        lo = ch.lower()
        if len(lo) != 1 or lo == ch:
            continue
        ln = cmap.get(ord(lo))
        if ln and ln in glyph_names and n != ln:
            res[n] = ln
    return res


def make_script_list(script_langs, feature_indices_by_langsys):
    """script_langs: {tag: [langtags]}; feature_indices_by_langsys: функция (script, lang|None) -> [индексы]"""
    sl = ot.ScriptList()
    sl.ScriptRecord = []
    for st in sorted(script_langs, key=lambda t: (t != "DFLT", t)):
        sr = ot.ScriptRecord()
        sr.ScriptTag = st
        sc = ot.Script()
        sc.DefaultLangSys = _langsys(feature_indices_by_langsys(st, None))
        sc.LangSysRecord = []
        for lt in sorted(script_langs[st]):
            r = ot.LangSysRecord()
            r.LangSysTag = lt
            r.LangSys = _langsys(feature_indices_by_langsys(st, lt))
            sc.LangSysRecord.append(r)
        sc.LangSysCount = len(sc.LangSysRecord)
        sr.Script = sc
        sl.ScriptRecord.append(sr)
    sl.ScriptCount = len(sl.ScriptRecord)
    return sl


def _langsys(idx):
    ls = ot.LangSys()
    ls.LookupOrder = None
    ls.ReqFeatureIndex = 0xFFFF
    ls.FeatureIndex = sorted(idx)
    ls.FeatureCount = len(ls.FeatureIndex)
    return ls


def make_table(cls, lookups, features, script_langs, feat_by_langsys):
    t = cls()
    t.Version = 0x00010000
    t.LookupList = ot.LookupList()
    t.LookupList.Lookup = lookups
    t.LookupList.LookupCount = len(lookups)
    t.FeatureList = ot.FeatureList()
    t.FeatureList.FeatureRecord = []
    for tag, lk in features:
        fr = ot.FeatureRecord()
        fr.FeatureTag = tag
        fr.Feature = ot.Feature()
        fr.Feature.FeatureParams = None
        fr.Feature.LookupListIndex = list(lk)
        fr.Feature.LookupCount = len(lk)
        t.FeatureList.FeatureRecord.append(fr)
    t.FeatureList.FeatureCount = len(features)
    t.ScriptList = make_script_list(script_langs, feat_by_langsys)
    return t


def chunk_pairs(pairs, gid, limit=14000):
    """делим словарь пар на подтаблицы по первому глифу (не больше limit записей в подтаблице)"""
    by_first = collections.defaultdict(dict)
    for (a, b), v in pairs.items():
        by_first[a][(a, b)] = v
    chunks, cur, n = [], {}, 0
    for a in sorted(by_first, key=lambda g: gid[g]):
        d = by_first[a]
        if n + len(d) > limit and cur:
            chunks.append(cur)
            cur, n = {}, 0
        cur.update(d)
        n += len(d)
    if cur:
        chunks.append(cur)
    return chunks


def build_layout(font, design_layers, caps_of, cmap, opts):
    """Строит GSUB и GPOS. design_layers: [Layer(non-caps)], caps_of: {suffix дизайна: Layer капители или None}"""
    gid = font.getReverseGlyphMap()
    glyphs = set(gid)
    c2sc, smcp, onum, liga, cyr = {}, {}, {}, {}, {}
    tabs = {"L": {}, "R": {}, "X": {}}       # R — русский контекст (метрики T2A), L — латинский (T1), X — церковнославянский (X2)
    srcname = {"L": "kern_L", "R": "kern", "X": "kern_X"}
    n_kernzero = 0
    all_layers = []
    for L in design_layers:
        all_layers.append(L)
        C = caps_of.get(L.suffix)
        if C is not None:
            all_layers.append(C)
    locl_lat = {}                  # подмена глифов на «двойники» с латинскими ширинами (T1/TS1)
    for L in all_layers:
        wv = {n for n in L.m.get("wvar", {}) if n in L.names}
        for n in wv:
            locl_lat[n + L.suffix] = n + ".lat" + L.suffix
        for tn, dst in tabs.items():
            for (a, b), v in L.m[srcname[tn]].items():
                if a in L.names and b in L.names:
                    x = rnd(v * UPEM)
                    if x:
                        if tn == "L":
                            a, b = (a + ".lat" if a in wv else a), (b + ".lat" if b in wv else b)
                        dst[(a + L.suffix, b + L.suffix)] = x
                    elif tn == "R":
                        n_kernzero += 1
        for k, v in lig_rules(L.m, L.names, L.suffix).items():
            liga[k] = v
        # русские варианты тире и «ёлочек» (T2A)
        for a, b in CYR_PAIRS:
            if a in L.names and b in L.names:
                cyr[a + L.suffix] = b + L.suffix
    # латинский контекст: рисунки 5/6/7 pt sans-serif (они есть только в кириллических кодировках) заменяются масштабированным рисунком 8 pt (как T1 в LaTeX);
    # глифы, которые есть только в TS1, остаются в «своём» рисунке (TS1 в LaTeX, как и T2A, использует рисунки по размерам)
    lmap = opts.get("lmap") or {}
    ts1_only = opts.get("ts1_only") or set()
    by_suffix = {L.suffix: L for L in design_layers}
    for L in design_layers:
        tgt = lmap.get(L.suffix)
        if tgt is None:
            continue
        T = by_suffix[tgt]
        wvT = {n for n in T.m.get("wvar", {}) if n in T.names}
        for n in L.names:
            if n in T.names and n != ".notdef" and n not in ts1_only:
                locl_lat[n + L.suffix] = (n + ".lat" if n in wvT else n) + T.suffix
    # капитель (\\scshape): шрифт капители есть только в T1 и в кириллических кодировках (в TS1 его нет: NFSS берёт TS1 из Roman).
    # Поэтому в латинском контексте знаки, которых нет в T1, а в кириллическом — знаки, которых нет в T2A/T2B/T2C/X2 (но есть в TS1),
    # остаются обычными (из Roman): так же поступает LaTeX
    smcp_R = {}
    ts1_only_R = opts.get("smcp_exR") or set()
    for L in design_layers:
        s = L.suffix
        C = caps_of.get(s)
        if C is not None:
            for n in L.names:
                if n in C.names and n != ".notdef" and n not in NO_VARIANT:
                    if n not in ts1_only:
                        smcp[n + s] = n + C.suffix
                    if n not in ts1_only_R:
                        smcp_R[n + s] = n + C.suffix
            u2l = upper_to_lower_map({u: n for u, n in cmap.items() if n in L.names}, L.names)
            for up, lo in u2l.items():
                if lo in C.names and lo not in NO_VARIANT and up not in NO_VARIANT:
                    c2sc[up + s] = lo + C.suffix
        for dg, od in ONUM:
            if dg in L.names and od in L.names:
                onum[dg + s] = od + s
    lookups = []
    feats = []
    idx = {}

    def add(tag, subtables):
        subtables = [x for x in subtables if x is not None]
        if not subtables:
            return
        lk = ob.buildLookup(subtables)
        lookups.append(lk)
        idx[tag] = len(lookups) - 1
    add("c2sc", [ob.buildSingleSubstSubtable(c2sc)] if c2sc else [])
    if smcp_R == smcp:
        smcp_R = {}
    add("smcp", [ob.buildSingleSubstSubtable(smcp)] if smcp else [])
    add("smcp_R", [ob.buildSingleSubstSubtable(smcp_R)] if smcp_R else [])
    add("onum", [ob.buildSingleSubstSubtable(onum)] if onum else [])
    add("liga", [ob.buildLigatureSubstSubtable(liga)] if liga else [])
    add("locl", [ob.buildSingleSubstSubtable(cyr)] if cyr else [])
    add("locl_lat", [ob.buildSingleSubstSubtable(locl_lat)] if locl_lat else [])
    feat_defs = [("c2sc", "c2sc"), ("liga", "liga"), ("locl", "locl"), ("locl_lat", "locl"), ("onum", "onum"), ("smcp", "smcp"), ("smcp_R", "smcp")]
    gsub_feats = [(tag, [idx[name]]) for name, tag in feat_defs if name in idx]
    findex = {name: i for i, (name, tag) in enumerate([d for d in feat_defs if d[0] in idx])}
    script_langs = {"DFLT": list(CYR_LANGS), "latn": list(CYR_LANGS), "cyrl": ["CSL "]}

    def feat_for(script, lang, features, findex):
        cyr_ctx = (script == "cyrl") or (lang is not None)       # русский контекст (T2A); иначе латинский (T1)
        res = []
        for name, i in findex.items():
            if name == "locl" and not cyr_ctx:
                continue
            if name == "locl_lat" and cyr_ctx:
                continue
            if name == "smcp" and cyr_ctx and "smcp_R" in findex:
                continue
            if name == "smcp_R" and not cyr_ctx:
                continue
            res.append(i)
        return res
    gsub = make_table(ot.GSUB, lookups, gsub_feats, script_langs, lambda s, l: feat_for(s, l, gsub_feats, findex))
    fg = newTable("GSUB")
    fg.table = gsub
    font["GSUB"] = fg
    # GPOS kern. Пары, у которых первый глиф — compwordmark (U+200C): HarfBuzz/rustybuzz обнуляет ширину невидимых символов ПОСЛЕ GPOS,
    # поэтому кёрн TeX (23, x) переносим на второй глиф (XPlacement + XAdvance) — отдельным lookup «ZW».
    def split_zw(tab):
        zw, rest = {}, {}
        for (a, b), x in tab.items():
            if a.split(".")[0] == "afii61664":
                zw[("afii61664", b)] = x
            else:
                rest[(a, b)] = x
        return zw, rest
    zws = {}
    for tn in tabs:
        zws[tn], tabs[tn] = split_zw(tabs[tn])
    zw_common = {k: x for k, x in zws["R"].items() if all(zws[t].get(k) == x for t in zws)}
    zw_diff = {tn: {k: x for k, x in zws[tn].items() if k not in zw_common} for tn in zws}
    keys_all = set.intersection(*[set(t) for t in tabs.values()])
    common_keys = {k for k in keys_all if all(tabs[t][k] == tabs["R"][k] for t in tabs)}
    common = {k: tabs["R"][k] for k in common_keys}
    spec = {tn: {k: x for k, x in t.items() if k not in common_keys} for tn, t in tabs.items()}

    def pv(x):
        return (ob.buildValue({"XAdvance": x}), None)

    def pv2(x):
        return (None, ob.buildValue({"XPlacement": x, "XAdvance": x}))
    glookups, gidx = [], {}
    nchunks = 0
    sets = [("common", {k: pv(x) for k, x in common.items()}), ("zw_common", {k: pv2(x) for k, x in zw_common.items()})]
    for tn in ("L", "R", "X"):
        sets.append(("spec_" + tn, {k: pv(x) for k, x in spec[tn].items()}))
        sets.append(("zw_" + tn, {k: pv2(x) for k, x in zw_diff[tn].items()}))
    for name, tab in sets:
        chunks = chunk_pairs(tab, gid) if tab else []
        nchunks += len(chunks)
        if chunks:
            glookups.append(ob.buildLookup([ob.buildPairPosGlyphsSubtable(ch, gid) for ch in chunks]))
            gidx[name] = len(glookups) - 1
    # особенности: по одному 'kern' на таблицу; одинаковые наборы lookup'ов сливаем
    gfeats, ftab = [], {}
    seen_sets = {}
    for tn in ("L", "R", "X"):
        lks = [gidx[n] for n in ("common", "zw_common", "spec_" + tn, "zw_" + tn) if n in gidx]
        key = tuple(lks)
        if key not in seen_sets:
            seen_sets[key] = len(gfeats)
            gfeats.append(("kern", lks))
        ftab[tn] = seen_sets[key]
    if not glookups:
        gfeats, ftab = [], {}

    def gpos_feats(script, lang):
        if not gfeats:
            return []
        if lang == "CSL ":
            return [ftab["X"]]
        return [ftab["R"]] if (script == "cyrl" or lang is not None) else [ftab["L"]]
    gpos = make_table(ot.GPOS, glookups, gfeats, {"DFLT": list(CYR_LANGS), "latn": list(CYR_LANGS), "cyrl": ["CSL "]}, gpos_feats)
    fp = newTable("GPOS")
    fp.table = gpos
    font["GPOS"] = fp
    kernR = tabs["R"]
    kernL = tabs["L"]
    stats = dict(kern=len(kernR) + len(zws['R']), kern_L=len(kernL) + len(zws['L']), kern_X=len(tabs['X']) + len(zws['X']), kern_common=len(common), kern_zw=len(zws['R']), kern_chunks=nchunks, kern_zero=n_kernzero, liga=len(liga), smcp=len(smcp), c2sc=len(c2sc),
                 onum=len(onum), cyr=len(cyr))
    return stats


def set_names(font, p):
    """p: словарь параметров имён (см. build.py)"""
    nm = font["name"]
    nm.names = []
    rec = {0: p["copyright"], 1: p["id1"], 2: p["id2"], 3: p["uid"], 4: p["full"], 5: p["version"], 6: p["ps"], 13: p["license"], 14: p["license_url"]}
    if p.get("typo_family") and p["typo_family"] != p["id1"]:
        rec[16] = p["typo_family"]
        rec[17] = p["typo_style"]
    if p.get("axis_name_id"):
        rec[p["axis_name_id"]] = "Optical size"
    for nid, s in sorted(rec.items()):
        nm.setName(s, nid, 3, 1, 0x409)
        if nid in (1, 2, 3, 4, 6, 16, 17):
            nm.setName(s, nid, 1, 0, 0)
    cff = font["CFF "].cff
    cff.fontNames[0] = p["ps"]
    top = cff.topDictIndex[0]
    top.FullName, top.FamilyName, top.Weight = p["full"], p["typo_family"] or p["id1"], ("Bold" if p["weight"] >= 600 else "Regular" if p["weight"] >= 400 else "Light")
    top.version = "0.3.4"
    top.Notice = p["copyright"]
    top.ItalicAngle = p["italic_angle"]
    top.isFixedPitch = 1 if p["mono"] else 0
    top.UnderlinePosition, top.UnderlineThickness = -200, 80


def fix_tables(font, p, cmap, scale_ascent=1600, scale_descent=-400):
    head, hhea, os2, post = font["head"], font["hhea"], newTable("OS/2"), font["post"]
    head.unitsPerEm = UPEM
    bold = p["id2"] in ("Bold", "Bold Italic")
    head.macStyle = (1 if bold else 0) | (2 if p["italic"] else 0) | (0 if p["width"] >= 5 else 0x20)
    head.fontRevision = 0.3
    head.flags = 3
    hhea.ascent, hhea.descent, hhea.lineGap = scale_ascent, scale_descent, 0
    ang = p["italic_angle"]
    if ang:
        hhea.caretSlopeRise, hhea.caretSlopeRun = 1000, int(round(1000 * math.tan(math.radians(-ang))))
    else:
        hhea.caretSlopeRise, hhea.caretSlopeRun = 1, 0
    hhea.caretOffset = 0
    # габариты по глифам x и H основного слоя
    gs = font.getGlyphSet()

    def ymax(name):
        if name not in gs:
            return 0
        bp = BoundsPen(gs)
        gs[name].draw(bp)
        return bp.bounds[3] if bp.bounds else 0
    xh, ch = ymax(cmap.get(ord("x"), "x")), ymax(cmap.get(ord("H"), "H"))
    cff_bbox = font["CFF "].cff.topDictIndex[0].FontBBox
    os2.version = 4
    os2.xAvgCharWidth = int(round(sum(font["hmtx"][g][0] for g in cmap.values()) / max(1, len(cmap))))
    os2.usWeightClass = p["weight"]
    os2.usWidthClass = p["width"]
    os2.fsType = 0
    os2.ySubscriptXSize, os2.ySubscriptYSize, os2.ySubscriptXOffset, os2.ySubscriptYOffset = 1300, 1200, 0, 280
    os2.ySuperscriptXSize, os2.ySuperscriptYSize, os2.ySuperscriptXOffset, os2.ySuperscriptYOffset = 1300, 1200, 0, 960
    os2.yStrikeoutSize, os2.yStrikeoutPosition = 80, 540
    os2.sFamilyClass = 0
    pan = font_panose(p["kind"], p["weight"], p["width"])
    os2.panose = pan
    os2.ulUnicodeRange1 = os2.ulUnicodeRange2 = os2.ulUnicodeRange3 = os2.ulUnicodeRange4 = 0
    os2.achVendID = "NONE"
    sel = 0
    if p["italic"]:
        sel |= 0x01
    if p["oblique"]:
        sel |= 0x200
    if bold:
        sel |= 0x20
    if p["id2"] == "Regular":
        sel |= 0x40
    sel |= 0x80      # USE_TYPO_METRICS
    os2.fsSelection = sel
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = scale_ascent, scale_descent, 0
    os2.usWinAscent = max(scale_ascent, int(cff_bbox[3]) + 1)
    os2.usWinDescent = max(-scale_descent, int(-cff_bbox[1]) + 1)
    os2.ulCodePageRange1, os2.ulCodePageRange2 = 0x00000005 | 0x00000010, 0
    os2.sxHeight, os2.sCapHeight = xh, ch
    os2.usDefaultChar, os2.usBreakChar, os2.usMaxContext = 0, 32, 3
    os2.usLowerOpticalPointSize = os2.usUpperOpticalPointSize = 0
    font["OS/2"] = os2
    os2.recalcUnicodeRanges(font)
    os2.usFirstCharIndex = min(cmap) if cmap else 0
    os2.usLastCharIndex = min(max(cmap), 0xFFFF) if cmap else 0
    post.formatType = 3.0
    post.italicAngle = ang
    post.underlinePosition, post.underlineThickness = -200, 80
    post.isFixedPitch = 1 if p["mono"] else 0
    post.minMemType42 = post.maxMemType42 = post.minMemType1 = post.maxMemType1 = 0


def font_panose(kind, weight, width):
    wt = 8 if weight >= 700 else 6 if weight >= 600 else 4 if weight <= 300 else 5
    ser = {"serif": 2, "sans": 11, "mono": 9}.get(kind, 2)
    return _panose([2, ser, wt, 3 if kind == "mono" else 2, 0, 0, 0, 0, 0, 0])


def _panose(vals):
    from fontTools.ttLib.tables.O_S_2f_2 import Panose
    pn = Panose()
    for k, v in zip(("bFamilyType", "bSerifStyle", "bWeight", "bProportion", "bContrast", "bStrokeVariation", "bArmStyle", "bLetterForm", "bMidline", "bXHeight"), vals):
        setattr(pn, k, v)
    return pn


def build_cmap_table(font, cmap):
    t = newTable("cmap")
    t.tableVersion = 0
    t.tables = []
    for pid, eid in ((0, 3), (3, 1)):
        st = _cmap_format4()
        st.platformID, st.platEncID, st.language = pid, eid, 0
        st.cmap = {u: n for u, n in cmap.items() if u <= 0xFFFF}
        t.tables.append(st)
    hi = {u: n for u, n in cmap.items() if u > 0xFFFF}
    if hi:
        from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
        st = CmapSubtable.newSubtable(12)
        st.platformID, st.platEncID, st.language = 3, 10, 0
        st.cmap = dict(cmap)
        t.tables.append(st)
    font["cmap"] = t


def _cmap_format4():
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
    return CmapSubtable.newSubtable(4)


def add_fvar(font, axis_name_id):
    fv = newTable("fvar")
    ax = Axis()
    ax.axisTag = "opsz"
    ax.minValue, ax.defaultValue, ax.maxValue = AXIS_MIN, AXIS_DEF, AXIS_MAX
    ax.axisNameID = axis_name_id
    ax.flags = 0
    fv.axes = [ax]
    fv.instances = []
    font["fvar"] = fv


def add_hvar(font):
    """Минимальная HVAR (все дельты нулевые). Нужна rustybuzz/Typst: у переменного CFF-шрифта без HVAR при opsz != default
    ширины глифов считаются по габаритам контура (xMax+xMin), а у пробела получается 0."""
    t = newTable("HVAR")
    h = ot.HVAR()
    h.Version = 0x00010000
    vs = ot.VarStore()
    vs.Format = 1
    rl = ot.VarRegionList()
    rl.RegionAxisCount = 1
    reg = ot.VarRegion()
    ax = ot.VarRegionAxis()
    ax.StartCoord, ax.PeakCoord, ax.EndCoord = 0.0, 1.0, 1.0
    reg.VarRegionAxis = [ax]
    rl.Region = [reg]
    rl.RegionCount = 1
    vs.VarRegionList = rl
    vd = ot.VarData()
    vd.VarRegionIndex = [0]
    vd.VarRegionCount = 1
    vd.NumShorts = 0
    vd.Item = []
    vd.ItemCount = 0
    vs.VarData = [vd]
    vs.VarDataCount = 1
    h.VarStore = vs
    h.AdvWidthMap = None
    h.LsbMap = None
    h.RsbMap = None
    t.table = h
    font["HVAR"] = t


def norm_opsz(v):
    v = min(max(v, AXIS_MIN), AXIS_MAX)
    return (v - AXIS_DEF) / (AXIS_MAX - AXIS_DEF) if v >= AXIS_DEF else (v - AXIS_DEF) / (AXIS_DEF - AXIS_MIN)


Q14 = 16384          # единица F2Dot14: нормализованные координаты осей хранятся и сравниваются целыми числами k/16384


def opsz_cut(boundary_tex):
    """Верхний предел диапазона рисунка в целых F2Dot14 для границы NFSS `boundary_tex` (пт TeX): наименьшее целое, не меньшее
    точного значения. Так сама граница (равенство в правиле NFSS — берётся меньший размер) при любом способе округления координаты
    шейпером (к ближайшему, вниз, вверх) остаётся у нижнего рисунка; а выше границы нижний рисунок «держится» не дольше одного кванта
    оси (24/16384 = 0,0015 пт выше 12 пт, 7/16384 = 0,0004 пт ниже)."""
    c = norm_opsz(boundary_tex * TEX2BP) * Q14
    return int(math.ceil(c - 1e-6))


def add_rvrn(font, design_layers, default_suffix):
    """FeatureVariations: для каждого рисунка, кроме основного, подмена базовых глифов на name+suffix в его диапазоне opsz.
    Диапазоны соседних рисунков строятся в целых F2Dot14 вплотную: верх нижнего = opsz_cut(граница), низ верхнего = opsz_cut(граница) + 1,
    поэтому нет ни щелей (в щель попал бы основной рисунок 12 pt), ни перекрытий. Основной рисунок — без условий (всё, что не покрыто)."""
    base_layer = [L for L in design_layers if L.suffix == default_suffix][0]
    subs = []
    for L in sorted(design_layers, key=lambda L: L.rng[0]):
        if L.suffix == default_suffix:
            continue
        lo_tex, hi_tex = L.rng
        qlo = -Q14 if lo_tex == float("-inf") else opsz_cut(lo_tex) + 1
        qhi = Q14 if hi_tex == float("inf") else opsz_cut(hi_tex)
        qlo, qhi = max(-Q14, min(Q14, qlo)), max(-Q14, min(Q14, qhi))
        if qhi < qlo:
            continue
        mapping = {n + default_suffix: n + L.suffix for n in L.names if n in base_layer.names and n != ".notdef" and n not in NO_VARIANT}
        subs.append(([{"opsz": (qlo / Q14, qhi / Q14)}], mapping))
    if subs:
        addFeatureVariations(font, subs)
    return len(subs)
