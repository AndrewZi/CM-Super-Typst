"""paths.py — пути (относительно папки build/; переопределяются переменными окружения)."""
import os
_BUILD = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SP = os.path.abspath(os.path.join(_BUILD, ".."))                              # корень пакета CM-Super-Typst
FULL = os.environ.get("CMS_DATA", _BUILD + "/data")                           # designs.json, tfm/, enc/ (+ pfbinfo.json, tfm_all.pkl после подготовки)
TFMDIR = os.environ.get("CMS_TFM", FULL + "/tfm")
PFBDIR = os.environ.get("CMS_PFB", "/usr/share/texmf/fonts/type1/public/cm-super")   # *.pfb из пакета cm-super (TeX Live / CTAN)
ENCDIR = os.environ.get("CMS_ENC", FULL + "/enc")
OUT = os.environ.get("CMS_OUT", _BUILD + "/out")                              # результат сборки: out/auto, out/static/<размер>
WORK = OUT + "/work"
