// Пример со статическими шрифтами CM-Super: рисунок (дизайн-размер) задаётся именем шрифта и не зависит от кегля.
// Нужны только файлы из fonts/static/ (помощник cm-super.typ и авто-шрифты не требуются): typst compile --font-path fonts/static example-static.typ
// Имя шрифта — «<семейство> <размер рисунка>»; размеры: 5, 6, 7, 8, 9, 10, 10.95, 12, 14.4, 17.28, 20.74, 24.88, 29.86, 35.83.
#set page(paper: "a4", margin: (x: 2cm, y: 1.5cm))
#set text(font: "CM-Super 12", size: 11.955pt, lang: "ru", top-edge: "ascender", bottom-edge: "descender", fallback: false)   // 12 pt TeX = 11,955 pt Typst
#show raw: set text(font: "CM-Super Typewriter 10", size: 9.963pt)
#set par(leading: 0.5em, spacing: 0.5em)

#let sizes = (5, 6, 7, 8, 9, 10, 10.95, 12, 14.4, 17.28, 20.74, 24.88, 29.86, 35.83)
#let label(name) = text(font: "CM-Super Sans 10", size: 8pt)[#name]

#text(font: "CM-Super Sans 12", size: 14pt)[*Статические шрифты: один рисунок на файл*]

Один и тот же текст набран кеглем 22 pt, а рисунок меняется от 5 до 35,83 pt: у малых рисунков буквы шире, x-height крупнее, засечки толще.
В TeX это `\font\x=ecrm0500 at 22pt` (рисунок 5 pt, увеличенный до 22 pt), а здесь — имя шрифта «CM-Super 5».

#for s in sizes [
  #let name = "CM-Super " + str(s)
  #text(font: name, size: 22pt)[Hamburgefonstiv Съешь ещё] #h(1em) #label(name) \
]

#v(1em)
#text(font: "CM-Super Sans 12", size: 11pt)[*Sans и Typewriter*]

#for s in (5, 8, 12, 24.88) [
  #let sans = "CM-Super Sans " + str(s)
  #text(font: sans, size: 22pt)[Hamburgefonstiv Съешь ещё] #h(1em) #label(sans) \
]
#for s in (8, 12, 24.88) [
  #let tt = "CM-Super Typewriter " + str(s)
  #text(font: tt, size: 22pt)[Hamburgefonstiv Съешь ещё] #h(1em) #label(tt) \
]

#v(1em)
Курсив, жирный и капитель — те же рисунки: #text(style: "italic")[Computer Modern], #text(weight: 700)[Computer Modern], #text(features: (smcp: 1))[Computer Modern].
