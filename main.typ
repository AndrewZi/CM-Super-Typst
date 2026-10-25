// ═════════════════════════════════════════════════════════════════════════════
//  main.typ — заготовка конспекта «как в pdfLaTeX»:
//      \documentclass[12pt,a4paper]{article} + babel russian + CM-Super (T2A/T1)
//
//  Что нужно в проекте: этот файл, cm-super.typ и шрифты fonts/auto/*.otf
//  (на typst.app — загрузите их в проект; в командной строке: typst compile --font-path fonts/auto main.typ).
//  Формулы набираются штатным New Computer Modern Math (математика CM-Super не содержит).
// ═════════════════════════════════════════════════════════════════════════════
#import "cm-super.typ": *

// ── страница ────────────────────────────────────────────────────────────────
#set page(paper: "a4", margin: (x: 2.5cm, y: 2.5cm), numbering: "1")

// ── шрифт и кегль класса: 12 pt, \baselineskip = 14.5 pt, язык — русский (кодировка T2A) ──
//    size: 10 | 11 | 12 — опция класса документа;  lang: "ru" ↔ babel russian, "en" ↔ английский (T1)
#show: cm-super.with(size: 12, lang: "ru")

// ── абзацы ──────────────────────────────────────────────────────────────────
// \parindent = 1.5em от 12 pt = 18 pt TeX (в LaTeX это фиксированная длина), \parskip = 0:
// расстояние между абзацами равно межстрочному (spacing = leading), поэтому строки идут в одном ритме.
#set par(
  justify: true,
  first-line-indent: (amount: tex-pt(18), all: true),     // красная строка и после заголовков (так делает babel russian)
  spacing: tex-pt(14.5 - 12),
)

// ── заголовки как \section и \subsection в article (12 pt) ──────────────────
// 1ex основного шрифта = 0.43045 em (XHEIGHT из TFM) = 5.1654 pt TeX
#let ex = 0.43045 * 12
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  v(tex-pt(3.5 * ex), weak: true)
  text(size: tex-pt(17.28), weight: 700, it)        // \Large\bfseries
  v(tex-pt(2.3 * ex), weak: true)
}
#show heading.where(level: 2): it => {
  v(tex-pt(3.25 * ex), weak: true)
  text(size: tex-pt(14.4), weight: 700, it)         // \large\bfseries
  v(tex-pt(1.5 * ex), weak: true)
}
#show heading.where(level: 3): it => {
  v(tex-pt(3.25 * ex), weak: true)
  text(size: tex-pt(12), weight: 700, it)           // \normalsize\bfseries
  v(tex-pt(1.5 * ex), weak: true)
}

// ═════════════════════════════════ документ ═════════════════════════════════
#align(center)[
  #text(size: tex-pt(17.28))[*Название конспекта*] \
  #v(tex-pt(6))
  #text(size: tex-pt(14.4))[Автор]
]

= Введение

Обычный текст: _курсив_ (`\emph`), *жирный* (`\textbf`), #textsc[капитель] (`\textsc`), #textsf[рубленый] (`\textsf`),
#texttt[машинописный] (`\texttt`). Формула в строке $a^2 + b^2 = c^2$ и выключная:
$ integral_0^1 x^2 dif x = 1 / 3. $

== Размеры и семейства

#footnotesize[\\footnotesize — как в LaTeX: 10 pt на интервале 12 pt.]

Внутри строки команды размера пишут с `leading: false`: #large(leading: false)[\\large]. Любое семейство CM-Super: #textfont("dunhill")[Dunhill], #textfont("funny")[Funny], #textfont("concrete")[Concrete].
