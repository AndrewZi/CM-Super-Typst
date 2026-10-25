# -*- coding: utf-8 -*-
"""pdfglyphs.py — точные позиции начала каждого глифа из PDF (pdfminer: ширины шрифта берутся как есть, без округления)."""
import collections, io, warnings
warnings.filterwarnings("ignore")
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFTextDevice
from pdfminer.pdffont import PDFUnicodeNotDefined


class Dev(PDFTextDevice):
    def __init__(self, rsrc):
        super().__init__(rsrc)
        self.glyphs = []

    def render_char(self, matrix, font, fontsize, scaling, rise, cid, ncs, graphicstate):
        e, f = matrix[4], matrix[5]
        w = font.char_width(cid)
        try:
            t = font.to_unichr(cid)
        except Exception:
            t = ""
        self.glyphs.append((e, f, t, font.fontname, cid, fontsize))
        return w * fontsize * scaling


def extract(path, merge=True, drop=("‌", " ", " "), with_size=False, with_y=False):
    """-> [страница][строка] -> [(x, text, font, cid)] — строки сверху вниз, глифы слева направо"""
    fp = open(path, "rb")
    parser = PDFParser(fp)
    doc = PDFDocument(parser)
    rm = PDFResourceManager()
    pages = []
    for page in PDFPage.create_pages(doc):
        dev = Dev(rm)
        PDFPageInterpreter(rm, dev).process_page(page)
        rows = collections.defaultdict(list)
        for (x, y, t, fn, cid, fs) in dev.glyphs:
            if t in drop:
                continue
            rows[round(y * 5)].append((x, t, fn, cid, fs) + ((y,) if with_y else ()) if with_size else ((x, t, fn, cid) + ((y,) if with_y else ())))
        lines = []
        for k in sorted(rows, reverse=True):      # PDF: y растёт вверх -> сверху вниз = по убыванию
            ln = sorted(rows[k], key=lambda g: g[0])
            lines.append(ln)
        pages.append(lines)
    fp.close()
    return pages
