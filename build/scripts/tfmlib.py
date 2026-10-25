"""tfmlib.py — чтение метрик TeX (TFM) через tftopl и разбор PL.
Что даёт: ширины символов, таблицу лигатур/кернинга (в виде пар «код слева, код справа» -> кернинг или лигатура),
параметры шрифта (SPACE, STRETCH, SHRINK, XHEIGHT, QUAD ...). Все величины — в долях кегля дизайна (em).
Кодировки (.enc, dvips) читаются функцией read_enc: список из 256 имён глифов.
"""
import re
import subprocess

LIG_OPS = ("LIG", "/LIG", "/LIG>", "LIG/", "LIG/>", "/LIG/", "/LIG/>", "/LIG/>>")


def tftopl(path):
    r = subprocess.run(["tftopl", path], capture_output=True, text=True, errors="replace")
    if r.returncode not in (0, 1) or not r.stdout.strip():
        raise RuntimeError(f"tftopl {path}: {r.stderr[:200]}")
    return r.stdout


def _tokens(s):
    return re.findall(r"\(|\)|[^\s()]+", s)


def _parse_list(tok, i):
    """tok[i] == '(' -> (список, индекс после ')')"""
    assert tok[i] == "("
    i += 1
    out = []
    while tok[i] != ")":
        if tok[i] == "(":
            sub, i = _parse_list(tok, i)
            out.append(sub)
        else:
            out.append(tok[i])
            i += 1
    return out, i + 1


def _code(items):
    """['C','f'] | ['O','101'] | ['D','65'] -> int"""
    k, v = items[0], items[1]
    if k == "C":
        return ord(v)
    if k == "O":
        return int(v, 8)
    if k == "D":
        return int(v)
    raise ValueError(items)


def _real(items):
    assert items[0] == "R", items
    return float(items[1])


def parse_pl(text):
    tok = _tokens(text)
    i = 0
    top = []
    while i < len(tok):
        if tok[i] == "(":
            sub, i = _parse_list(tok, i)
            top.append(sub)
        else:
            i += 1
    res = {"designsize": None, "fontdimen": {}, "chars": {}, "boundary": None, "family": None, "coding": None}
    lig_items = None
    for it in top:
        key = it[0]
        if key == "DESIGNSIZE":
            res["designsize"] = _real(it[1:])
        elif key == "FAMILY":
            res["family"] = " ".join(it[1:])
        elif key == "CODINGSCHEME":
            res["coding"] = " ".join(it[1:])
        elif key == "BOUNDARYCHAR":
            res["boundary"] = _code(it[1:])
        elif key == "FONTDIMEN":
            for p in it[1:]:
                if p[0] == "PARAMETER":
                    res["fontdimen"][f"P{int(p[2])}"] = _real(p[3:])
                else:
                    res["fontdimen"][p[0]] = _real(p[1:])
        elif key == "LIGTABLE":
            lig_items = it[1:]
        elif key == "CHARACTER":
            code = _code(it[1:3])
            d = {}
            for p in it[3:]:
                if isinstance(p, list) and p[0] in ("CHARWD", "CHARHT", "CHARDP", "CHARIC"):
                    d[p[0][4:].lower()] = _real(p[1:])
            res["chars"][code] = d
    res["lig"] = _program(lig_items or [])
    return res


def _program(items):
    """Собираем программу из LIGTABLE: {метка (код или 'B'): [инструкции]}; выполняем её по правилам TeX"""
    instrs = []
    labels = {}
    pending = []
    for p in items:
        op = p[0]
        if op == "LABEL":
            pending.append("B" if p[1] == "BOUNDARYCHAR" else _code(p[1:]))
        elif op in LIG_OPS or op == "KRN":
            for lab in pending:
                labels[lab] = len(instrs)
            pending = []
            ins = {"op": op, "next": _code(p[1:3]), "stop": False, "skip": 0}
            if op == "KRN":
                ins["kern"] = _real(p[3:])
            else:
                ins["lig"] = _code(p[3:5])
            instrs.append(ins)
        elif op == "STOP":
            instrs[-1]["stop"] = True
        elif op == "SKIP":
            instrs[-1]["skip"] = int(p[2])
    return {"instrs": instrs, "labels": labels}


def pairs(prog, left_codes=None):
    """Вычисляем для каждого кода слева и кода справа, что делает TeX: {(a, b): ('KRN', значение) | ('LIG', op, код)}"""
    instrs, labels = prog["instrs"], prog["labels"]
    out = {}
    for a, start in labels.items():
        if a == "B":
            continue
        pos = start
        seen = set()
        while 0 <= pos < len(instrs):
            ins = instrs[pos]
            b = ins["next"]
            if (a, b) not in out:
                out[(a, b)] = ("KRN", ins["kern"]) if ins["op"] == "KRN" else ("LIG", ins["op"], ins["lig"])
            if ins["stop"]:
                break
            pos += 1 + ins["skip"]
            if pos in seen:
                break
            seen.add(pos)
    boundary = {}
    if "B" in labels:
        pos = labels["B"]
        while 0 <= pos < len(instrs):
            ins = instrs[pos]
            b = ins["next"]
            if b not in boundary:
                boundary[b] = ("KRN", ins["kern"]) if ins["op"] == "KRN" else ("LIG", ins["op"], ins["lig"])
            if ins["stop"]:
                break
            pos += 1 + ins["skip"]
    return out, boundary


def read_tfm(path):
    pl = parse_pl(tftopl(path))
    pl["pairs"], pl["left_boundary"] = pairs(pl["lig"])
    return pl


def read_enc(path):
    """dvips .enc -> (имя кодировки, список из 256 имён)"""
    s = open(path, encoding="latin-1").read()
    s = re.sub(r"%[^\n]*", "", s)
    names = re.findall(r"/([A-Za-z0-9_.\-]+)", s)
    assert len(names) == 257, (path, len(names))
    return names[0], names[1:]
