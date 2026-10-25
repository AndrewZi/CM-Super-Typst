# -*- coding: utf-8 -*-
"""make_overlay.py — наложение строк pdfLaTeX (красный) и Typst (синий): совпадение даёт чёрный цвет.

    python3 make_overlay.py CLASS OUT.png [VARIANT] [--dpi 300]
      CLASS   — 12 | 11 | 10 (результаты e2e.py);
      VARIANT — "c" (сквозной тест e2e.py, по умолчанию) или "v" (тест межстрочного интервала e2e_v.py).
Строки выравниваются по началу первого глифа (общий сдвиг страницы не считается расхождением),
дальше любое расхождение метрик/кернинга/размера видно цветной каймой.
"""
import sys, os, json
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "e2e")

ROWS = [
    # (ctx, style, size, подпись)
    ("ru", "rm", "normalsize", "Roman 12 pt · ru (T2A)"),
    ("en", "rm", "normalsize", "Roman 12 pt · en (T1)"),
    ("ru", "it", "normalsize", "Italic · ru"),
    ("ru", "sl", "normalsize", "Slanted · ru"),
    ("ru", "sc", "normalsize", "Small Caps · ru"),
    ("ru", "bx", "normalsize", "Bold Extended · ru"),
    ("ru", "bx it", "normalsize", "Bold Italic · ru"),
    ("en", "sf", "normalsize", "Sans · en"),
    ("ru", "sf bx", "normalsize", "Sans Bold · ru"),
    ("ru", "tt", "normalsize", "Typewriter · ru"),
    ("ru", "rm", "tiny", "Roman tiny (6 pt)"),
    ("ru", "rm", "Huge", "Roman Huge (24.88 pt)"),
    ("ru", "dh", "normalsize", "Dunhill"),
    ("ru", "fib", "normalsize", "Fibonacci"),
    ("ru", "funny", "normalsize", "Funny"),
    ("ru", "ccr", "normalsize", "Concrete"),
    ("ru", "br", "normalsize", "Bright"),
]


SIZE_CMDS = ["tiny", "scriptsize", "footnotesize", "small", "normalsize", "large", "Large", "LARGE", "huge", "Huge"]
SIZE_LABEL = {"tiny": "\\tiny", "scriptsize": "\\scriptsize", "footnotesize": "\\footnotesize", "small": "\\small", "normalsize": "\\normalsize",
              "large": "\\large", "Large": "\\Large", "LARGE": "\\LARGE", "huge": "\\huge", "Huge": "\\Huge"}
ROWS_SIZES = [("ru", st, sz, f"{lab} · {SIZE_LABEL[sz]}") for st, lab in (("rm", "Roman"), ("it", "Italic"), ("bx", "Bold")) for sz in SIZE_CMDS]


def first_origin(page):
    d = page.get_text("rawdict")
    for b in d["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                for ch in sp["chars"]:
                    if ch["c"].strip():
                        return ch["origin"], sp["size"], ch.get("bbox")
    return None, None, None


def last_x(page):
    d = page.get_text("rawdict")
    mx = 0
    for b in d["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                for ch in sp["chars"]:
                    if ch["c"].strip():
                        mx = max(mx, ch["bbox"][2])
    return mx


def dark(pix):
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    g = a[..., :3].mean(axis=2) if pix.n >= 3 else a[..., 0]
    return 1.0 - g / 255.0


def render_at_origin(page, o, left, top, w, h, z):
    """Страница, обрезанная так, что начало первого глифа попадает в точку (left, top) растра ТОЧНО (без округления до пикселя)."""
    page.set_cropbox(page.mediabox)
    x0, y0 = o[0] - left, o[1] - top
    x0, y0 = max(x0, 0.0), max(y0, 0.0)
    page.set_cropbox(pymupdf.Rect(o[0] - left, o[1] - top, o[0] - left + w, o[1] - top + h))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), colorspace=pymupdf.csGRAY, alpha=False)
    page.set_cropbox(page.mediabox)
    return dark(pix)


def overlay_row(dl, dt, idx, dpi):
    pl, pt = dl[idx], dt[idx]
    (ol, sl, _), (ot, st, _) = first_origin(pl)[0:3], first_origin(pt)[0:3]
    if ol is None or ot is None:
        return None
    size = max(sl, st)
    xr = max(last_x(pl) - ol[0], last_x(pt) - ot[0]) + 4
    top, bot = size * 1.0, size * 0.35
    z = dpi / 72.0
    w, h = xr + 4, top + bot
    A = render_at_origin(pl, ol, 4, top, w, h, z)
    B = render_at_origin(pt, ot, 4, top, w, h, z)
    hh, ww = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
    A, B = A[:hh, :ww], B[:hh, :ww]
    rgb = np.empty((hh, ww, 3))
    rgb[..., 0] = 255 * (1 - B)
    rgb[..., 1] = 255 * (1 - B) * (1 - A)
    rgb[..., 2] = 255 * (1 - A)
    ink_l, ink_t = int((A > 0.5).sum()), int((B > 0.5).sum())
    both = int(((A > 0.5) & (B > 0.5)).sum())
    only = int(((A > 0.5) ^ (B > 0.5)).sum())
    return Image.fromarray(rgb.astype(np.uint8)), (ink_l, ink_t, both, only)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cls = int(args[0])
    out = args[1]
    var = args[2] if len(args) > 2 else "c"
    dpi = 300
    if "--dpi" in sys.argv:
        dpi = int(sys.argv[sys.argv.index("--dpi") + 1])
    rows_def = ROWS_SIZES if "--sizes" in sys.argv else ROWS
    L = json.load(open(f"{W}/c{cls}_lines.json"))
    dl = pymupdf.open(f"{W}/{var}{cls}_l.pdf")
    dt = pymupdf.open(f"{W}/{var}{cls}_t.pdf")
    rows = []
    for ctx, style, size, label in rows_def:
        ids = [l["id"] for l in L if (l["ctx"], l["style"], l["size"]) == (ctx, style, size)]
        if not ids:
            continue
        r = overlay_row(dl, dt, ids[0] - 1, dpi)
        if r is None:
            continue
        rows.append((label, ids[0]) + r)
    fnt_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    fnt = ImageFont.truetype(fnt_path, int(dpi * 0.075))
    fntb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(dpi * 0.09))
    pad = int(dpi * 0.04)
    Wd = max(im.width for _, _, im, _ in rows) + 2 * pad
    lab_h = int(dpi * 0.11)
    Hd = sum(im.height + lab_h + pad for _, _, im, _ in rows) + int(dpi * 0.30)
    canvas = Image.new("RGB", (Wd, Hd), (255, 255, 255))
    dr = ImageDraw.Draw(canvas)
    dr.text((pad, pad), f"pdfLaTeX (красный) и Typst + CM-Super (синий), класс {cls} pt: чёрный = точное совпадение", font=fntb, fill=(0, 0, 0))
    y = int(dpi * 0.30)
    for label, i, im, st in rows:
        dr.text((pad, y), f"{label}", font=fnt, fill=(80, 80, 80))
        y += lab_h
        canvas.paste(im, (pad, y))
        y += im.height + pad
    canvas.save(out, optimize=True)
    print("OK", out, canvas.size, [(r[0], r[3]) for r in rows])


if __name__ == "__main__":
    main()
