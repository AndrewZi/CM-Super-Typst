// Пример: конспект «как в LaTeX» (article, 12pt, babel russian, T2A/T1, CM-Super).
// Положите рядом cm-super.typ и шрифты (*.otf) — они подхватываются автоматически.
#import "cm-super.typ": *

#set page(paper: "a4", margin: (x: 2.5cm, y: 2.5cm))
#show: cm-super.with(size: 12, lang: "ru")
#set par(justify: true, first-line-indent: (amount: tex-pt(18), all: true), spacing: tex-pt(14.5 - 12), leading: tex-pt(14.5 - 12))

// \section, \subsection — как в классе article (жирный, 17.28/14.4 pt; отступы заданы в ex основного шрифта)
// 1ex = высота строчной «x» CM-Super Roman 12 pt = 0.43045 em (параметр XHEIGHT из TFM)
#let ex = 0.43045 * 12
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  v(tex-pt(3.5 * ex), weak: true)
  text(size: tex-pt(17.28), weight: 700, it)
  v(tex-pt(2.3 * ex), weak: true)
}
#show heading.where(level: 2): it => {
  v(tex-pt(3.25 * ex), weak: true)
  text(size: tex-pt(14.4), weight: 700, it)
  v(tex-pt(1.5 * ex), weak: true)
}

#align(center)[
  #text(size: tex-pt(24.88), weight: 700)[Конспект лекций] \
  #v(tex-pt(8))
  #large(leading: false)[Computer Modern Super #sym.dash.en как в pdfLaTeX] \
  #v(tex-pt(6))
  #textsc[Иван Петров] · #textit[1 сентября 2026]
]

= Введение

Это обычный абзац на русском языке с _курсивом_ (`\emph`), *жирным* (`\textbf`), #textsl[наклонным] (`\textsl`),
#textsc[капителью] (`\textsc`: Small Caps), #textsf[рубленым] (`\textsf`) и #texttt[машинописным] (`\texttt`) начертаниями.
Лигатуры: fi fl ff ffi ffl; кернинг: AVAWATA Te To Ty; «ёлочки», „лапки“ и тире — вот так.

#foreignlanguage("en")[English fragment (T1 metrics): The quick brown fox jumps over the lazy dog. “Quoted text”, AVATAR, Waffle office.]

== Размеры шрифта

// Команды размера: в строке — leading: false (иначе они меняют межстрочный интервал и начинают новый абзац)
#tiny(leading: false)[\\tiny] #scriptsize(leading: false)[\\scriptsize] #footnotesize(leading: false)[\\footnotesize]
#small(leading: false)[\\small] #normalsize(leading: false)[\\normalsize] #large(leading: false)[\\large]
#Large(leading: false)[\\Large] #LARGE(leading: false)[\\LARGE] #huge(leading: false)[\\huge] #Huge(leading: false)[\\Huge]

// Отдельным абзацем — вместе с интервалом (\baselineskip) из таблицы класса article
#footnotesize[Сноска: \\footnotesize — 10 pt на интервале 12 pt, как в LaTeX. Строка продолжается, чтобы показать
межстрочный интервал: съешь же ещё этих мягких французских булок, да выпей чаю.]

Произвольный размер, как `\fontsize{13}{15}\selectfont` (LaTeX берёт ближайший рисунок 12 pt без масштабирования):
#fontsize(13, 15, leading: false)[13 pt → рисунок 12 pt]. Без привязки: #fontsize(13, 15, snap: false, leading: false)[масштабирование 12 pt → 13 pt].

== Формулы

Встроенная формула $a^2 + b^2 = c^2$ и выключная:
$ integral_0^1 x^2 dif x = 1 / 3, quad sum_(k=1)^n k = (n(n+1)) / 2. $

#block(inset: (left: 1.5em))[
  #textbf[Теорема] (#textit[Лагранжа]). #textit[Пусть $f$ дифференцируема на $[a, b]$. Тогда существует $c in (a, b)$ такое, что
  $f'(c) = (f(b) - f(a)) / (b - a)$.]
]

== Семейства CM-Super

#table(columns: 3, stroke: 0.4pt, inset: 4pt,
  [*Семейство*], [*LaTeX*], [*Образец*],
  [CM-Super], [`\rmfamily`], [Hamburgefonstiv Съешь ещё],
  [CM-Super Sans], [`\sffamily`], [#sffamily[Hamburgefonstiv Съешь ещё]],
  [CM-Super Typewriter], [`\ttfamily`], [#ttfamily[Hamburgefonstiv Съешь ещё]],
  [Typewriter Proportional], [`\fontfamily{cmvtt}`], [#vttfamily[Hamburgefonstiv Съешь ещё]],
  [CM-Super Dunhill], [`\fontfamily{cmdh}`], [#textfont("dunhill")[Hamburgefonstiv Съешь ещё]],
  [CM-Super Concrete], [`\fontfamily{ccr}`], [#textfont("concrete")[Hamburgefonstiv Съешь ещё]],
  [CM-Super Funny], [`\fontfamily{cmfr}`], [#textfont("funny")[Hamburgefonstiv Съешь ещё]],
  [CM-Super Fibonacci], [`\fontfamily{cmfib}`], [#textfont("fibonacci")[Hamburgefonstiv Съешь ещё]],
  [CM-Super Bright], [`\fontfamily{cmbr}` (T2A)], [#textfont("bright")[Hamburgefonstiv Съешь ещё]],
)

#v(tex-pt(6))
Любое сочетание NFSS: #nfss(family: "cmss", series: "bx", shape: "sl")[cmss/bx/sl Съешь ещё], #nfss(family: "cmtt", shape: "it")[cmtt/m/it Съешь ещё],
#nfss(family: "cmr", series: "bx", shape: "sc")[cmr/bx/sc Съешь ещё], #nfss(family: "cmr", series: "b")[cmr/b/n Съешь ещё],
#nfss(family: "cmbr", series: "sb", shape: "sl")[cmbr/sb/sl Съешь ещё], #nfss(family: "cmss", series: "sbc")[cmss/sbc/n Съешь ещё].
