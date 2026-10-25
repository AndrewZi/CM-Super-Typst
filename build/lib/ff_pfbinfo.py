# fontforge -lang=py -script ff_pfbinfo.py : имена глифов, ширины, габариты, Unicode (по именам AGL) для всех .pfb CM-Super
import fontforge, json, glob, os
import sys
_HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
PFB = os.environ.get("CMS_PFB", "/usr/share/texmf/fonts/type1/public/cm-super")
OUT = os.path.join(os.environ.get("CMS_DATA", os.path.join(_HERE, "..", "data")), "pfbinfo.json")
res = {}
for p in sorted(glob.glob(PFB + "/*.pfb")):
    f = fontforge.open(p)
    base = os.path.basename(p)[:-4]
    gl = {}
    for g in f.glyphs():
        bb = g.boundingBox()
        gl[g.glyphname] = [g.width, g.unicode, [round(x, 1) for x in bb]]
    res[base] = {"em": f.em, "fullname": f.fullname, "family": f.familyname, "weight": f.weight, "italicangle": f.italicangle,
                 "fontname": f.fontname, "glyphs": gl}
    f.close()
json.dump(res, open(OUT, "w"))
print("done", len(res))
