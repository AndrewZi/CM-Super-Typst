// ════════════════════════════════════════════════════════════════════════════
//  cm-super.typ — CM-Super в Typst «как в pdfLaTeX»
//
//  Подключение (шрифты .otf лежат в проекте рядом с этим файлом):
//
//      #import "cm-super.typ": *
//      #show: cm-super.with(size: 12, lang: "ru")
//
//  Что даёт:
//    • tex-pt(x)         — «пункты TeX» → длина Typst (1 pt TeX = 0.996264 pt Typst);
//    • cm-super          — оформление документа: шрифт, кегль и интерлиньяж класса article/book/report (10/11/12 pt);
//    • команды кегля     — tiny … Huge и fontsize(размер, интерлиньяж, …), как в LaTeX;
//    • команды начертаний — rmfamily/sffamily/ttfamily, bfseries/mdseries, itshape/slshape/scshape/upshape,
//                           textrm/textsf/texttt/textbf/textit/textsl/textsc/…, nfss(семейство, серия, начертание);
//    • nfss-size(x)      — «привязка» кегля к размеру, который выберет NFSS (LaTeX берёт ближайший из размеров
//                           в .fd-файле БЕЗ масштабирования; список зависит от семейства);
//    • design(ds)[…]     — зафиксировать рисунок (дизайн-размер) ds, как `\font\x=ecss0500 at …` (нужны fonts/static).
//  Лицензия шрифтов CM-Super: GPL-2+ с исключением для шрифтов (см. README). Этот файл — общественное достояние (CC0).
// ════════════════════════════════════════════════════════════════════════════

// ─── единицы ────────────────────────────────────────────────────────────────
/// 1 pt TeX = 1/72.27 дюйма, 1 pt в Typst (и в PDF) = 1/72 дюйма.
#let tex-pt(x) = x * 72 / 72.27 * 1pt
/// Длина Typst → пункты TeX (число).
#let _to-tex(len) = len / 1pt * 72.27 / 72

// ─── размеры, перечисленные в .fd-файлах LaTeX ─────────────────────────────
// Для размера, которого нет в списке, NFSS берёт ближайший из списка (при равенстве — меньший)
// и подгружает шрифт именно этого размера, НЕ масштабируя его до запрошенного.
#let std-sizes = (5, 6, 7, 8, 9, 10, 10.95, 12, 14.4, 17.28, 20.74, 24.88, 29.86, 35.83)
#let size-lists = (
  std: std-sizes,                                                           // cmr, cmss, cmtt, cmvtt, cmdh, cmbr, cmtl
  short: (5, 6, 7, 8, 9, 10, 10.95, 12, 14.4, 17.28, 20.74, 24.88),         // Concrete (ccr), cmsd, полужирный узкий Sans (sbc)
  fib: (5, 6, 7, 8, 9, 10, 10.95, 12, 14.4, 17.28, 20.74),                  // Fibonacci (cmfib) в T1: размеров 24.88+ нет
  funny: (9, 10, 10.95, 12, 14.4, 17.28, 20.74, 24.88, 29.86, 35.83),       // Funny (cmfr)
  slitex: (7, 8, 10, 12, 13.82, 16.59, 19.907, 23.89, 28.66, 34.4, 41.28),  // SliTeX (lcmss), прямое начертание
  slitex-sl: (13.82, 16.59, 19.907, 23.89, 28.66, 34.4, 41.28),             // SliTeX: наклонное/жирное и lcmtt
)

/// Ближайший размер из списка (при равенстве — меньший), как в `\try@size@substitution` ядра LaTeX.
/// `x` — в пунктах TeX; `kind` — ключ из `size-lists` или массив размеров.
#let nfss-size(x, kind: "std") = {
  let list = if type(kind) == str { size-lists.at(kind) } else { kind }
  let best = list.first()
  for s in list {
    if calc.abs(s - x) < calc.abs(best - x) { best = s }
  }
  best
}

// ─── классы документа: (кегль, \baselineskip) в пунктах TeX ─────────────────
// Значения взяты из size10.clo, size11.clo, size12.clo.
#let _classes = (
  "10": (normalsize: (10, 12), small: (9, 11), footnotesize: (8, 9.5), scriptsize: (7, 8), tiny: (5, 6),
         large: (12, 14), Large: (14.4, 18), LARGE: (17.28, 22), huge: (20.74, 25), Huge: (24.88, 30)),
  "11": (normalsize: (10.95, 13.6), small: (10, 12), footnotesize: (9, 11), scriptsize: (8, 9.5), tiny: (6, 7),
         large: (12, 14), Large: (14.4, 18), LARGE: (17.28, 22), huge: (20.74, 25), Huge: (24.88, 30)),
  "12": (normalsize: (12, 14.5), small: (10.95, 13.6), footnotesize: (10, 12), scriptsize: (8, 9.5), tiny: (6, 7),
         large: (14.4, 18), Large: (17.28, 22), LARGE: (20.74, 25), huge: (24.88, 30), Huge: (24.88, 30)),
)
#let _cls = state("cm-super-class", 12)

// ─── семейства ─────────────────────────────────────────────────────────────
/// Запасной шрифт для знаков, которых нет в CM-Super (греческий, математические символы и т. п.).
#let fallback-fonts = ("New Computer Modern",)
#let families = (
  rm: "CM-Super", sf: "CM-Super Sans", tt: "CM-Super Typewriter", vtt: "CM-Super Typewriter Proportional",
  dunhill: "CM-Super Dunhill", fibonacci: "CM-Super Fibonacci", funny: "CM-Super Funny", concrete: "CM-Super Concrete",
  bright: "CM-Super Bright", bright-tt: "CM-Super Bright Typewriter", sans-quotation: "CM-Super Sans Quotation",
  slitex: "CM-Super SliTeX", slitex-tt: "CM-Super SliTeX Typewriter",
  slitex-invisible: "CM-Super SliTeX Invisible", slitex-tt-invisible: "CM-Super SliTeX Typewriter Invisible",
  classical: "CM-Super Classical", variant: "CM-Super Variant", upright: "CM-Super Upright",
)
#let _font(key) = (families.at(key), ..fallback-fonts)

// ─── текущее семейство и «вид» списка размеров ──────────────────────────────
// (внутри `context`; Typst хранит имена шрифтов в нижнем регистре)
#let _wmap = (thin: 100, extralight: 200, light: 300, regular: 400, medium: 500, semibold: 600, bold: 700, extrabold: 800, black: 900)
#let _weight-int(w) = if type(w) == int { w } else { _wmap.at(w, default: 400) }
#let _cur-family() = {
  let f = text.font
  if f.len() == 0 { return "" }
  let x = f.first()
  lower(if type(x) == str { x } else { x.name })
}
// Языки, для которых таблицы метрик берутся из кодировки T2A (кириллица)
#let _cyr-langs = ("ru", "uk", "be", "bg", "sr", "mk", "kk", "ky", "tg", "mn", "tt", "ba", "cu", "sah", "ab", "os", "ce")
/// Какой список размеров NFSS относится к семейству `name` (в нижнем регистре) при текущем начертании и языке.
#let _kind-of(name0, style, weight, stretch, lang) = {
  // статический шрифт «CM-Super Sans 10» (рисунок зафиксирован): список размеров — как у исходного семейства
  let name = name0.replace(regex("\\s+\\d+(\\.\\d+)?$"), "")
  if name == lower(families.fibonacci) { if lang in _cyr-langs { "short" } else { "fib" } }  // в T2A у Fibonacci есть размер 24.88
  else if name == lower(families.funny) { "funny" }
  else if name == lower(families.concrete) { "short" }
  else if name == lower(families.sf) and stretch < 100% { "short" }
  else if name in (lower(families.slitex), lower(families.slitex-invisible)) {
    if style != "normal" or weight > 400 { "slitex-sl" } else { "slitex" }
  }
  else if name in (lower(families.slitex-tt), lower(families.slitex-tt-invisible)) { "slitex-sl" }
  else { "std" }
}
#let _cur-kind() = _kind-of(_cur-family(), text.style, _weight-int(text.weight), text.stretch, text.lang)

// ─── оформление документа ───────────────────────────────────────────────────
/// Основная функция: `#show: cm-super.with(size: 12, lang: "ru")`.
///  - `size` — опция класса (`\documentclass[12pt]{article}`): 10, 11 или 12;
///  - `lang` — основной язык (`"ru"` ↔ babel/russian и кодировка T2A; `"en"` ↔ T1; см. README);
///  - `leading` — задать интерлиньяж по `\baselineskip` класса;
///  - `math-font` — математический шрифт New Computer Modern Math (в Typst он штатный; близок к CM-math);
///  - `raw-font` — моноширинный шрифт CM-Super Typewriter для `raw` (``код`` и блоки кода); кегль — как у окружающего текста, как у \texttt.
#let cm-super(body, size: 12, lang: "ru", region: none, leading: true, math-font: true, raw-font: true) = {
  assert(size in (10, 11, 12), message: "size: 10, 11 или 12 (опция класса документа)")
  let (s, b) = _classes.at(str(size)).normalsize
  _cls.update(size)
  set text(font: _font("rm"), size: tex-pt(s), lang: lang, region: region, top-edge: "ascender", bottom-edge: "descender")
  show: it => if leading { set par(leading: tex-pt(b - s)); it } else { it }
  show math.equation: it => if math-font { set text(font: "New Computer Modern Math"); it } else { it }
  // Typst набирает raw на 0.8 em; в LaTeX \texttt — того же кегля, что окружающий текст, поэтому компенсируем множитель
  show raw: it => if raw-font { context { set text(font: _font("tt"), size: text.size / 0.8); it } } else { it }
  body
}

// ─── язык ──────────────────────────────────────────────────────────────────
/// `\foreignlanguage{lang}{...}` — другая кодировка/таблица кернинга внутри абзаца.
#let foreignlanguage(lang, body) = text(lang: lang, body)
/// `\selectlanguage{lang}` — как декларация: `#show: selectlanguage.with("en")`.
#let selectlanguage(lang, body) = text(lang: lang, body)

// ─── кегль ─────────────────────────────────────────────────────────────────
/// `\fontsize{size}{baselineskip}\selectfont` для произвольных размеров в пунктах TeX.
/// При `snap: true` (по умолчанию) кегль заменяется ближайшим размером NFSS, как делает LaTeX
/// (13 pt → шрифт 12 pt); при `snap: false` — масштабируется нужный дизайн.
/// `kind: auto` — список размеров определяется по текущему семейству (Fibonacci, Funny, Concrete, SliTeX имеют свои).
/// `leading: true` задаёт и интерлиньяж (`\baselineskip`) — это нужно для целых абзацев и блоков; внутри строки
/// пишите `leading: false`: смена параметров абзаца посреди абзаца в Typst начинает новый абзац.
#let fontsize(size, baselineskip, body, snap: true, kind: auto, leading: true) = context {
  let k = if kind == auto { _cur-kind() } else { kind }
  let s = if snap { nfss-size(size, kind: k) } else { size }
  set text(size: tex-pt(s))
  if leading { set par(leading: tex-pt(baselineskip - s)); body } else { body }
}
#let _size-cmd(name, body, leading) = context {
  let (s0, b) = _classes.at(str(_cls.get())).at(name)
  let s = nfss-size(s0, kind: _cur-kind())
  set text(size: tex-pt(s))
  if leading { set par(leading: tex-pt(b - s)); body } else { body }
}
// Команды кегля LaTeX (размер и \baselineskip зависят от опции класса, заданной в `cm-super`).
// `#large[…]` — блочное использование (с интерлиньяжем); `#large(leading: false)[…]` — внутри строки.
#let tiny(body, leading: true) = _size-cmd("tiny", body, leading)
#let scriptsize(body, leading: true) = _size-cmd("scriptsize", body, leading)
#let footnotesize(body, leading: true) = _size-cmd("footnotesize", body, leading)
#let small(body, leading: true) = _size-cmd("small", body, leading)
#let normalsize(body, leading: true) = _size-cmd("normalsize", body, leading)
#let large(body, leading: true) = _size-cmd("large", body, leading)
#let Large(body, leading: true) = _size-cmd("Large", body, leading)
#let LARGE(body, leading: true) = _size-cmd("LARGE", body, leading)
#let huge(body, leading: true) = _size-cmd("huge", body, leading)
#let Huge(body, leading: true) = _size-cmd("Huge", body, leading)

// ─── рисунок «как есть»: статические шрифты (папка fonts/static) ────────────
/// Метка размера рисунка в имени статического шрифта: 5, 6, …, 10.95, 12, 14.4, 17.28 …
#let _dlabel(ds) = if calc.fract(ds) == 0 { str(int(ds)) } else { str(ds) }
/// Список шрифтов для рисунка `ds` семейства `key` (ключ из `families`), например `design-font("sf", 5)` → «CM-Super Sans 5».
/// Есть у семейств, у которых несколько рисунков: rm sf tt vtt dunhill fibonacci funny concrete bright classical variant upright.
#let design-font(key, ds) = (families.at(key) + " " + _dlabel(ds), ..fallback-fonts)
#let _key-of(name) = {
  for (k, v) in families { if lower(v) == name { return k } }
  none
}
/// Зафиксировать рисунок `ds` (дизайн-размер, пт TeX) у текущего семейства; кегль не меняется (рисунок масштабируется),
/// как `\font\x=ecss0500 at 12pt` в LaTeX. Нужны статические шрифты (fonts/static). `key:` — ключ семейства, если оно не определяется само.
#let design(ds, body, key: auto) = context {
  let k = if key == auto { _key-of(_cur-family()) } else { key }
  assert(k != none, message: "design(): не удалось определить семейство; задайте key: (см. families)")
  set text(font: design-font(k, ds))
  body
}

// ─── семейства: декларации (rmfamily …) и команды (textrm …) ──────────────
/// Любое семейство CM-Super по ключу из `families`: `#textfont("funny")[…]`.
/// Для семейств со своим списком размеров (Fibonacci, Funny, Concrete, SliTeX) текущий кегль
/// «привязывается» к ближайшему размеру этого списка — как при `\fontfamily{cmfr}\selectfont` в LaTeX.
#let textfont(key, body, kind: auto) = context {
  let name = families.at(key)
  let k = if kind == auto { _kind-of(lower(name), text.style, _weight-int(text.weight), text.stretch, text.lang) } else { kind }
  set text(font: _font(key))
  if k != "std" {
    set text(size: tex-pt(nfss-size(_to-tex(text.size), kind: k)))
    body
  } else { body }
}
#let rmfamily(body) = text(font: _font("rm"), body)
#let sffamily(body) = text(font: _font("sf"), body)
#let ttfamily(body) = text(font: _font("tt"), body)
#let vttfamily(body) = text(font: _font("vtt"), body)       // cmvtt — пропорциональный машинописный
#let textrm(body) = rmfamily(body)
#let textsf(body) = sffamily(body)
#let texttt(body) = ttfamily(body)
#let textvtt(body) = vttfamily(body)

// ─── серия ─────────────────────────────────────────────────────────────────
#let mdseries(body) = text(weight: 400, stretch: 100%, body)
#let bfseries(body) = text(weight: 700, stretch: 100%, body)   // bx — cmbx (расширенный жирный)
#let sbseries(body) = text(weight: 600, stretch: 100%, body)   // b (cmr) и sb (cmbr) — полужирный (не bx)
#let sbcseries(body) = text(font: _font("sf"), weight: 600, stretch: 75%, body)   // sbc — полужирный узкий Sans (cmssdc), другого sbc в CM-Super нет
#let textmd(body) = mdseries(body)
#let textbf(body) = bfseries(body)

// ─── начертание ────────────────────────────────────────────────────────────
#let upshape(body) = text(style: "normal", features: (smcp: 0), body)
#let itshape(body) = text(style: "italic", features: (smcp: 0), body)
#let slshape(body) = text(style: "oblique", features: (smcp: 0), body)
/// Капитель: в LaTeX `\scshape` ЗАМЕНЯЕТ курсив/наклонное, а прописные берутся из шрифта капители (eccc) — это и даёт smcp.
/// В Sans капители нет: LaTeX подставляет капитель Roman (cmss/m/sc → cmr/m/sc), так делаем и мы.
#let scshape(body) = context {
  if _cur-family() == lower(families.sf) {
    text(font: _font("rm"), style: "normal", features: (smcp: 1), body)
  } else {
    text(style: "normal", features: (smcp: 1), body)
  }
}
/// Наклонная капитель (`\fontshape{scsl}\selectfont`).
#let scslshape(body) = text(style: "oblique", features: (smcp: 1), body)
/// Прямой курсив (`ui`, шрифт cmu10): отдельное семейство.
#let ulshape(body) = text(font: _font("upright"), style: "normal", features: (smcp: 0), body)
#let normalfont(body) = text(font: _font("rm"), weight: 400, stretch: 100%, style: "normal", features: (smcp: 0), body)
#let textup(body) = upshape(body)
#let textit(body) = itshape(body)
#let textsl(body) = slshape(body)
#let textsc(body) = scshape(body)
#let textulc(body) = ulshape(body)
#let textnormal(body) = normalfont(body)

// ─── общий выбор шрифта как в NFSS ─────────────────────────────────────────
#let _nfss-families = (
  cmr: "rm", cmss: "sf", cmsd: "sf", cmtt: "tt", cmvtt: "vtt", cmdh: "dunhill", cmfib: "fibonacci", cmfr: "funny",
  ccr: "concrete", cmbr: "bright", cmtl: "bright-tt", lcmss: "slitex", lcmtt: "slitex-tt",
)
#let _nfss-series = (m: (400, 100%), md: (400, 100%), b: (600, 100%), sb: (600, 100%), bx: (700, 100%), bf: (700, 100%), sbc: (600, 75%))
#let _nfss-shapes = (n: upshape, up: upshape, it: itshape, sl: slshape, sc: scshape, scsl: scslshape, ui: ulshape)
/// `\fontfamily{…}\fontseries{…}\fontshape{…}\selectfont`: имена NFSS как в LaTeX.
///   семейства: cmr cmss cmsd cmtt cmvtt cmdh cmfib cmfr ccr cmbr cmtl lcmss lcmtt (cmsd считается как cmss, см. README);
///   серии: m, b, sb, bx, sbc;  начертания: n, it, sl, sc, scsl, ui (для lcmss/lcmtt ещё In, Isl, Iit — «невидимые»).
///   Правила NFSS, которые учтены: у cmr серия b — это полужирный cmb (ecrb), у остальных семейств b ≡ bx; серия sb существует
///   у cmbr; sbc — всегда Sans Semibold Condensed (ecssdc), в том числе из ccr; ccr/bx — это Roman Bold (cmr/bx) на размерах Concrete;
///   cmss/m/sc — капитель Roman.
///   Пример: `#nfss(family: "cmss", series: "bx", shape: "sl")[Жирный наклонный Sans]`.
#let nfss(body, family: none, series: none, shape: none) = {
  let inv = shape in ("In", "Isl", "Iit")
  assert(not inv or family in ("lcmss", "lcmtt"), message: "формы In/Isl/Iit есть только у SliTeX (lcmss, lcmtt)")
  let fam = family
  let kind = auto
  // у Sans капители нет: NFSS берёт капитель Roman (cmss/m/sc → cmr/m/sc)
  if shape == "sc" and fam in ("cmss", "cmsd") { fam = "cmr" }
  // sbc (полужирный узкий) есть только у Sans: в ccr и cmsd он тоже берётся из ecssdc
  if series == "sbc" { fam = "cmss" }
  // ccfonts: жирный Concrete — это Roman Bold, размеры — из списка Concrete
  if series in ("bx", "bf") and fam == "ccr" { fam = "cmr"; kind = "short" }
  let r = body
  // порядок вложенности: семейство — внутри (оно уже видит серию и начертание, нужные для списка размеров)
  if fam != none {
    let key = _nfss-families.at(fam)
    if inv { key += "-invisible" }
    r = textfont(key, r, kind: kind)
  }
  if series != none {
    let (w, st) = _nfss-series.at(series)
    // b: у cmr — полужирный cmb (ecrb); во всех остальных семействах b ≡ bx (ssub)
    if series == "b" and fam != none and fam != "cmr" { w = 700 }
    r = text(weight: w, stretch: st, r)
  }
  if shape != none {
    r = if shape == "In" { upshape(r) } else if inv { slshape(r) } else { _nfss-shapes.at(shape)(r) }
  }
  r
}

// ─── Concrete: в ccfonts жирный берётся из Computer Modern Roman ──────────
/// `\usepackage{ccfonts}`: гарнитура Concrete, а жирный (bx) подставляется из CM-Super (cmr/bx).
#let ccfonts(body) = {
  set text(font: _font("concrete"))
  show strong: set text(font: _font("rm"))
  body
}
