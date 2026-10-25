Проверки: как повторить
=======================

Эти скрипты сравнивают результат с настоящим pdfLaTeX. Они лежат здесь как рабочие инструменты, использованные при создании пакета (см. ../REPORT.md).
Пути заданы относительно пакета: шрифты — ../../fonts/{auto,static}, помощник — ../../cm-super.typ, данные сборки — ../../build/data
(переопределение: CMS_FONTS, CMS_DATA, E2E_FONTS, TYPST=путь к typst). Рабочие каталоги (e2e/, work/, nfss2/) создаются рядом со скриптами.

Нужны: pdflatex (TeX Live 2023 с cm-super, ec, lh, babel), Typst 0.15.x, Python-пакеты uharfbuzz, PyMuPDF, pdfminer.six, fontTools, numpy, Pillow;
перед этим выполнена подготовка build/ (TFM в build/data/tfm, pfbinfo.json, tfm_all.pkl — см. ../../build/README.txt).

Скрипты (в порядке отчёта):
  nfss_probe.py        эталон NFSS: каждый \DeclareFontShape на сетке размеров → какой TFM выбирает настоящий LaTeX (nfss2/probe*.json; готовые файлы приложены)
  tfmtest.py FACE      проверка 1: метрики, кернинг, лигатуры по TFM (LaTeX) ↔ Typst со статическими шрифтами; run_all_faces.sh — все гарнитуры
  vartest.py hb|typst  проверка 2: слои авто-шрифта ↔ статические шрифты (HarfBuzz / Typst)
  boundary_scan.py     проверка 3a: переключение рисунков у границ и по всей оси opsz (HarfBuzz)
  boundary_typst.py    проверка 3b: то же в настоящем Typst (по ширинам или растрам)
  nfss_check.py        проверка 4: правила выбора рисунка в шрифте ↔ эталон NFSS (PROBE_FILE=probe_x.json для T2B/T2C/X2)
  e2e.py, e2e_cmp.py   проверка 5: сквозной тест LaTeX (NFSS + babel) ↔ Typst + cm-super.typ; e2e_cmp.py 12 11 10 печатает итог
  e2e_v.py             проверка 6: межстрочный интервал по командам кегля
  outlines_check.py    проверка 7: контуры всех глифов всех шрифтов == контуры исходных .pfb (точка в точку; нужен каталог .pfb: CMS_PFB)
  make_overlay.py      картинки-наложения pdfLaTeX (красный) и Typst (синий): python3 make_overlay.py 12 out.png [c] [--sizes]
  pdfglyphs.py, texts.py, run_latex.py — вспомогательное (извлечение позиций глифов из PDF, тестовые строки, сборка LaTeX-теста)

logs/ — логи прогонов, на которых основан отчёт; overlay-*.png — наложения.
