# CM-Super для Typst — шрифты «как в pdfLaTeX»

Полная конвертация **CM-Super 0.3.4** (Type 1: 409 файлов, 422 рисунка) в OpenType для Typst:
**все дизайн-размеры 5 … 35,83 pt, все гарнитуры и начертания** (Roman, Italic, Slanted, Bold, Semibold, Small Caps, Sans, Typewriter, Dunhill, Fibonacci, Funny, Concrete, Bright, SliTeX …).
Ширины букв, кернинг и лигатуры взяты **из TFM-файлов LaTeX** (T1, T2A, T2B, T2C, X2, TS1), а рисунок для каждого кегля выбирается по тем же правилам, что у NFSS в pdfLaTeX.
Результат: контуры букв — те же, что в `.pfb` (сверены все точки всех глифов); текст набирается теми же глифами, на тех же позициях и в тех же размерах, что в pdfLaTeX; расхождения — только шум округления в PDF (≤ 0,0023 em, т. е. ≤ 0,03 pt на 12 pt).

> **Что не входит.** Математика: формулы Typst набирает штатным New Computer Modern Math, а не оригинальными cmmi/cmsy/cmex. Он близок, но не идентичен. Подробности и остальные ограничения — в разделе 8.

Версия пакета: 1.0 (2026-10-25). Typst: 0.15.x (проверено на 0.15.1).

---

## 1. Что в архиве

| Что | Где | Зачем |
|---|---|---|
| **Шрифты «авто-размер»**: 48 файлов, 41,3 МБ | `fonts/auto/` | Один файл на начертание, внутри все рисунки CM-Super. Typst сам выбирает рисунок по кеглю (ось `opsz`). **Основной вариант.** |
| **Статические шрифты**: 340 файлов, 39,8 МБ | `fonts/static/<размер>/` | Один рисунок на файл («CM-Super 12», «CM-Super Sans 8»…). Чтобы жёстко задать рисунок независимо от кегля. |
| Помощник **`cm-super.typ`** | корень | LaTeX-команды в Typst: `\large`, `\fontsize`, `\textsc`, `\bfseries`, NFSS-семейства, `tex-pt()` … |
| `main.typ`, `main.pdf` | корень | Заготовка «как `article`, 12 pt, русский» и её результат. |
| `example.typ`, `example.pdf` | корень | Пример: размеры, начертания, семейства, формулы. |
| `example-static.typ`, `example-static.pdf` | корень | Пример со статическими шрифтами: один и тот же текст рисунками 5 … 35,83 pt. |
| `validation/` | | Отчёт о сверке с pdfLaTeX (`REPORT.md`), логи, картинки-наложения, скрипты проверок. |
| `build/` | | Скрипты конвертации (FontForge + fontTools) — для воспроизводимости. |
| `docs/` | | Лицензии. |

Размеры указаны без сжатия. Архивы:

* `CM-Super-Typst-auto.zip` — авто-шрифты + помощник + примеры (**достаточно для работы**);
* `CM-Super-Typst-core.zip` — только Roman, Sans и Typewriter (15 файлов, 24,8 МБ) + помощник и `main.typ`: самый лёгкий вариант, остальные семейства в нём недоступны;
* `CM-Super-Typst-static.zip` — статические шрифты: **дополнение** к авто-шрифтам (помощнику нужны оба набора);
* `CM-Super-Typst-full.zip` — всё, включая отчёт о сверке, логи и скрипты.

---

## 2. Быстрый старт

### typst.app

1. Откройте проект и загрузите в него (кнопка *Upload* или перетаскиванием): `cm-super.typ` и **все `.otf` из `fonts/auto/`** (можно сразу папкой). Загруженные в проект шрифты Typst подхватывает сам, ничего настраивать не надо.
2. В начале документа:

```typst
#import "cm-super.typ": *
#show: cm-super.with(size: 12, lang: "ru")   // как \documentclass[12pt]{article} + babel russian
```

3. Дальше — как обычно: `*жирный*`, `_курсив_`, `#smallcaps[Капитель]`, `#large[крупнее]`, `#textsf[Sans]`, `#text(size: tex-pt(14.4))[14,4 pt TeX]` …

Заготовка целиком — `main.typ` (страница A4, поля 2,5 см, абзацы с красной строкой, заголовки как в `article`).

### Командная строка

```
typst compile --font-path fonts/auto main.typ
```

(для статических шрифтов добавьте `--font-path fonts/static`; имена не пересекаются).

### Без помощника

Достаточно подключить шрифт и задать кегль **в пунктах TeX** (12 pt TeX = 11,955 pt Typst):

```typst
#set text(font: "CM-Super", size: 11.955pt, lang: "ru", top-edge: "ascender", bottom-edge: "descender")
#set par(leading: 2.491pt, spacing: 2.491pt)    // \baselineskip 14,5 pt TeX − кегль 12 pt TeX, в pt Typst
```

> **Единицы.** В Typst 1 pt = 1/72 дюйма, в TeX 1 pt = 1/72,27 дюйма. LaTeX-овские «12 pt» — это `tex-pt(12)` = 11,955 pt Typst. Все длины из LaTeX переводите через `tex-pt()`. Помощник делает это сам.

> **Вертикальный ритм.** Шрифт задаёт строку высотой ровно 1 em (над базовой линией 0,8 em, под ней 0,2 em; `top-edge: "ascender"`, `bottom-edge: "descender"`), поэтому `leading = \baselineskip − кегль`, а расстояние между абзацами при `\parskip = 0` равно `leading`. Так интерлиньяж совпадает с LaTeX до 0,001 pt. Положение **первой** строки на странице определяют поля: в LaTeX первая базовая линия лежит на `\topskip` (12 pt в классе 12pt) ниже верхней границы текста, в Typst — на 0,8 em; чтобы совместить, добавьте к верхнему полю `tex-pt(12) * 0.2` ≈ 2,39 pt.

---

## 3. Как выбирается рисунок для кегля

У CM-Super для каждого начертания несколько **рисунков** (design sizes): буквы 5 pt нарисованы шире и с большим x-height, чем 17 pt. NFSS в LaTeX берёт рисунок из таблицы `.fd` и **не масштабирует** его до промежуточных кеглей: просьба о 13 pt даёт рисунок 12 pt при 12 pt (с предупреждением `size <12> substituted`).

**Авто-шрифты (`fonts/auto`)** воспроизводят это в Typst: Typst сам ставит ось `opsz` равной кеглю текста (в pt Typst), а границы между рисунками стоят там, где их ставит NFSS: по середине между соседними размерами списка (ближайший, при равенстве — меньший). На стандартных кеглях (5, 6, 7, 8, 9, 10, 10,95, 12, 14,4, 17,28, 20,74, 24,88, 29,86, 35,83 pt TeX) результат совпадает с LaTeX; достаточно `size: tex-pt(x)`.

| Рисунок, pt | Кегль, pt TeX | Кегль, pt Typst (значение оси `opsz`) |
|---:|:---|:---|
| 5 | ≤ 5,5 | ≤ 5,479 |
| 6 | 5,5 < x ≤ 6,5 | 5,479 < x ≤ 6,476 |
| 7 | 6,5 < x ≤ 7,5 | 6,476 < x ≤ 7,472 |
| 8 | 7,5 < x ≤ 8,5 | 7,472 < x ≤ 8,468 |
| 9 | 8,5 < x ≤ 9,5 | 8,468 < x ≤ 9,465 |
| 10 | 9,5 < x ≤ 10,475 | 9,465 < x ≤ 10,436 |
| 10,95 | 10,475 < x ≤ 11,475 | 10,436 < x ≤ 11,432 |
| 12 | 11,475 < x ≤ 13,2 | 11,432 < x ≤ 13,151 |
| 14,4 | 13,2 < x ≤ 15,84 | 13,151 < x ≤ 15,781 |
| 17,28 | 15,84 < x ≤ 19,01 | 15,781 < x ≤ 18,939 |
| 20,74 | 19,01 < x ≤ 22,81 | 18,939 < x ≤ 22,725 |
| 24,88 | 22,81 < x ≤ 27,37 | 22,725 < x ≤ 27,268 |
| 29,86 | 27,37 < x ≤ 32,845 | 27,268 < x ≤ 32,722 |
| 35,83 | > 32,845 | > 32,722 |

Границы заданы целыми значениями 14-битной оси: рисунки примыкают друг к другу без щелей и перекрытий; на самой границе берётся меньший рисунок (как у NFSS), выше границы он «держится» не дольше полутора квантов оси (квант — 24/16384 ≈ 0,0015 pt выше 12 pt и 7/16384 ≈ 0,0004 pt ниже).

Внутри диапазона рисунок **масштабируется** до фактического кегля, как у любого масштабируемого шрифта. Для промежуточных кеглей, где LaTeX не масштабирует, есть команда `fontsize()`:

* `#fontsize(13, 15)[текст]` — как `\fontsize{13}{15}\selectfont`: кегль «привязывается» к ближайшему размеру NFSS (13 → 12 pt, как в LaTeX), интерлиньяж 15 pt;
* `#fontsize(13, 15, snap: false)[текст]` — масштабирование рисунка 12 pt до 13 pt (поведение любого «плавающего» шрифта);
* то же без помощника: `text(size: tex-pt(12))` или `text(size: tex-pt(13))`.

**Команды кегля классов `article/report/book`** (размер / `\baselineskip` в pt TeX; `cm-super.with(size: 10 | 11 | 12)`):

| Команда | `10pt` | `11pt` | `12pt` |
|:---|:---:|:---:|:---:|
| `\tiny` | 5 / 6 | 6 / 7 | 6 / 7 |
| `\scriptsize` | 7 / 8 | 8 / 9,5 | 8 / 9,5 |
| `\footnotesize` | 8 / 9,5 | 9 / 11 | 10 / 12 |
| `\small` | 9 / 11 | 10 / 12 | 10,95 / 13,6 |
| `\normalsize` | 10 / 12 | 10,95 / 13,6 | 12 / 14,5 |
| `\large` | 12 / 14 | 12 / 14 | 14,4 / 18 |
| `\Large` | 14,4 / 18 | 14,4 / 18 | 17,28 / 22 |
| `\LARGE` | 17,28 / 22 | 17,28 / 22 | 20,74 / 25 |
| `\huge` | 20,74 / 25 | 20,74 / 25 | 24,88 / 30 |
| `\Huge` | 24,88 / 30 | 24,88 / 30 | 24,88 / 30 |

Пары «кегль / `\baselineskip`» — в pt TeX, как в `size10.clo`, `size11.clo`, `size12.clo`. В классе 12 pt `\huge` и `\Huge` совпадают.

Команды есть в помощнике под теми же именами (`#tiny[…]` … `#Huge[…]`); они меняют кегль **и** интерлиньяж. Внутри строки пишите `#large(leading: false)[…]` — смена интерлиньяжа посреди абзаца в Typst начинает новый абзац.

**Особенности семейств.** Те же правила, что в `.fd` LaTeX:

* **Основная сетка.** Roman, Italic, Slanted, Bold, Semibold, Upright, Dunhill, Classical, Variant и Sans в кириллической/«русской» кодировке (T2A, T2B, T2C, X2, TS1) имеют по 14 рисунков 5 … 35,83 pt, границы — по таблице выше.
* **Sans (`cmss`) в латинской кодировке T1.** В `t1cmss.fd` нет собственных рисунков 5–7 pt: LaTeX берёт на этих кеглях рисунок 8 pt. Шрифт делает так же для латиницы в абзацах с языком не из таблицы п. 5 (например, `lang: "en"`); кириллица и латиница внутри русского текста (T2A) набираются собственными рисунками 5, 6, 7 pt. Остальные рисунки одинаковы в обоих случаях.
* **Typewriter (`cmtt`, `cmvtt`).** Рисунки 8, 9, 10, 10,95, 12, 14,4, 17,28, 20,74, 24,88, 29,86, 35,83 pt; на кеглях меньше 8,5 pt берётся рисунок 8 pt: ≤ 8,5 → **8**; (8,5; 9,5] → **9**; (9,5; 10,475] → **10** и далее по основной сетке.
* **Bright (`cmbr`, T2A).** Рисунки 8, 9, 10, 17,28 pt (Regular, Slanted, Semibold, Semibold Slanted): ≤ 8,5 → **8**; (8,5; 9,5] → **9**; (9,5; 15,84] → **10**; > 15,84 → **17,28**.
* **Bright Bold (`cmbr/bx`).** Собственный рисунок только 10 pt; на кеглях ниже 9 pt LaTeX берёт Semibold 8 pt (`t2acmbr.fd`: `\DeclareFontShape … bx … <-9> sub*cmbr/sb/n`) — шрифт делает то же: ≤ 8,5 → **8**; > 8,5 → **10** (слои: Semibold 8, Bold 10).
* **Concrete (`ccr`).** Рисунки 5, 6, 7, 8, 9, 10 pt: ≤ 5,5 → **5**; (5,5; 6,5] → **6**; (6,5; 7,5] → **7**; (7,5; 8,5] → **8**; (8,5; 9,5] → **9**; > 9,5 → **10**. Курсив Concrete (`ccr/m/it`) — один рисунок 10 pt. `ccr/bx` в LaTeX — это Roman Bold (`ccfonts`), рисунки на сетке Concrete (5 … 24,88 pt).
* **Fibonacci (`cmfib`).** Рисунки 5, 6, 7, 8, 9, 10, 10,95, 12, 14,4, 17,28, 20,74, 24,88 pt (NFSS в T1 доходит до 20,74 pt, в T2A — до 24,88 pt; выше берётся самый крупный). **Funny (`cmfr`).** Рисунки 9, 10, 10,95, 12, 14,4, 17,28, 20,74, 24,88, 29,86, 35,83 pt; всё, что меньше 9,5 pt, — рисунок 9 pt.
* **SliTeX (`lcmss`, `lcmtt`), Sans Quotation, «невидимый» SliTeX.** Один рисунок (8 pt, у `lcmtt/m/it` — 10 pt), который масштабируется до любого кегля; NFSS берёт размеры 7, 8, 10, 12, 13,82, 16,59, 19,907, 23,89, 28,66, 34,4, 41,28 pt (для наклонного и жирного — с 13,82 pt), `textfont("slitex", …)` их учитывает.
* **Капитель** (`smcp`): у каждого рисунка своя капитель (eccc, ecsc, ecxc, ecoc, ectc, eocc); у Roman, Slanted, Bold, Bold Slanted, Typewriter — на все 14 (11) рисунков, у Concrete — один рисунок 10 pt.

**Статические шрифты** («CM-Super 12», «CM-Super Sans 5», «CM-Super Bright 17.28» …) нужны, когда рисунок надо задать явно, независимо от кегля — как `\font\x=ecss0500 at 12pt`:

```typst
#text(font: "CM-Super Sans 5", size: tex-pt(12))[рисунок 5 pt на кегле 12 pt]
#sffamily[#design(5)[то же через помощник]]       // design(...) — внутри семейства, например sffamily
```

Имя статического шрифта: `<семейство> <размер>`, размер — как в таблице выше (`5`, `10.95`, `17.28` …). Рисунок задаёт только форму букв; метрики (ширины, кернинг) — именно этого рисунка.

---

## 4. Семейства и начертания

Колонки: **Typst** — как запросить начертание (вместе с `font:` из заголовка группы: `weight`, `style`, `stretch`); **Файл** — имя файла в `fonts/auto/`; **Type 1** — исходный шрифт CM-Super (в скобках — имена TFM для T1 и T2A: `ecrm1200` ↔ `sfrm1200`); **NFSS** — как его выбирает LaTeX (`семейство/серия/начертание`; в квадратных скобках — если объявление есть не во всех кодировках: T1, T2A, T2B, T2C, X2, TS1); **Рисунки** — какие дизайн-размеры (pt) есть в файле.

**CM-Super** — `font: "CM-Super"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuper-Regular.otf` | `sfrm` (`ecrm` / `larm`) + капитель `sfcc` | `cmr/m/n`; `cmr/m/sc` (капитель); `cmsd/m/sc` (капитель); `cmss/m/sc` (капитель) | 5 … 35,83 (14) |
| `weight: 400, style: "italic"` | `CMSuper-Italic.otf` | `sfti` (`ecti` / `lati`) | `cmr/m/it` | 5 … 35,83 (14) |
| `weight: 400, style: "oblique"` | `CMSuper-Slanted.otf` | `sfsl` (`ecsl` / `lasl`) + капитель `sfsc` | `cmr/m/sl`; `cmr/m/scsl` (капитель) | 5 … 35,83 (14) |
| `weight: 700` | `CMSuper-Bold.otf` | `sfbx` (`ecbx` / `labx`) + капитель `sfxc` | `ccr/bx/n`; `cmr/bx/n`; `cmr/bx/sc` (капитель) | 5 … 35,83 (14) |
| `weight: 700, style: "italic"` | `CMSuper-BoldItalic.otf` | `sfbi` (`ecbi` / `labi`) | `ccr/bx/it`; `cmr/bx/it` | 5 … 35,83 (14) |
| `weight: 700, style: "oblique"` | `CMSuper-BoldSlanted.otf` | `sfbl` (`ecbl` / `labl`) + капитель `sfoc` | `ccr/bx/sl`; `cmr/bx/sl`; `cmr/b/scsl` (капитель); `cmr/bx/scsl` (капитель) | 5 … 35,83 (14) |
| `weight: 600` | `CMSuper-Semibold.otf` | `sfrb` (`ecrb` / `larb`) | `cmr/b/n` | 5 … 35,83 (14) |

**CM-Super Upright** — `font: "CM-Super Upright"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperUpright-Regular.otf` | `sfui` (`ecui` / `laui`) | `cmr/m/ui` | 5 … 35,83 (14) |

**CM-Super Classical** — `font: "CM-Super Classical"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400, style: "italic"` | `CMSuperClassical-Italic.otf` | `sfci` (`ecci` / `laci`) | — (нет в стандартных `.fd`: шрифт задаётся только по имени `\font`) | 5 … 35,83 (14) |

**CM-Super Dunhill** — `font: "CM-Super Dunhill"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperDunhill-Regular.otf` | `sfdh` (`ecdh` / `ladh`) | `cmdh/m/n` | 5 … 35,83 (14) |

**CM-Super Variant** — `font: "CM-Super Variant"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 700` | `CMSuperVariant-Bold.otf` | `sfbm` (`ecbm` / `labm`) | — (нет в стандартных `.fd`: шрифт задаётся только по имени `\font`) | 5 … 35,83 (14) |

**CM-Super Sans** — `font: "CM-Super Sans"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperSans-Regular.otf` | `sfss` (`ecss` / `lass`) | `cmsd/m/n` [T1,TS1]; `cmss/m/n` | 5 … 35,83 (14) |
| `weight: 400, style: "oblique"` | `CMSuperSans-Slanted.otf` | `sfsi` (`ecsi` / `lasi`) | `cmsd/m/it` [T1,TS1]; `cmsd/m/sl` [T1,TS1]; `cmss/m/it`; `cmss/m/sl` | 5 … 35,83 (14) |
| `weight: 700` | `CMSuperSans-Bold.otf` | `sfsx` (`ecsx` / `lasx`) | `cmsd/bx/n` [T1,TS1]; `cmss/bx/n` | 5 … 35,83 (14) |
| `weight: 700, style: "oblique"` | `CMSuperSans-BoldSlanted.otf` | `sfso` (`ecso` / `laso`) | `cmsd/bx/it` [T1,TS1]; `cmsd/bx/sl` [T1,TS1]; `cmss/bx/it`; `cmss/bx/sl` | 5 … 35,83 (14) |
| `weight: 600, stretch: 75%` | `CMSuperSans-SemiboldCondensed.otf` | `sfssdc` (`ecssdc` / `lassdc`) | `ccr/sbc/n`; `cmsd/sbc/n` [T1,TS1]; `cmss/sbc/n` [T1,T2A,T2B,T2C,X2] | 10 |

**CM-Super Typewriter** — `font: "CM-Super Typewriter"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperTypewriter-Regular.otf` | `sftt` (`ectt` / `latt`) + капитель `sftc` | `cmtt/bx/n` [T1,T2A,T2B,T2C,X2]; `cmtt/m/n`; `cmtt/m/sc` (капитель) | 8 … 35,83 (11) |
| `weight: 400, style: "italic"` | `CMSuperTypewriter-Italic.otf` | `sfit` (`ecit` / `lait`) | `cmtt/bx/it` [T1,T2A,T2B,T2C,X2]; `cmtt/m/it` | 8 … 35,83 (11) |
| `weight: 400, style: "oblique"` | `CMSuperTypewriter-Slanted.otf` | `sfst` (`ecst` / `last`) | `cmtt/m/sl` | 8 … 35,83 (11) |

**CM-Super Typewriter Proportional** — `font: "CM-Super Typewriter Proportional"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperTypewriterProportional-Regular.otf` | `sfvt` (`ecvt` / `lavt`) | `cmvtt/m/n` | 8 … 35,83 (11) |
| `weight: 400, style: "italic"` | `CMSuperTypewriterProportional-Italic.otf` | `sfvi` (`ecvi` / `lavi`) | `cmvtt/m/it` | 8 … 35,83 (11) |

**CM-Super Fibonacci** — `font: "CM-Super Fibonacci"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperFibonacci-Regular.otf` | `sffb` (`ecfb` / `lafb`) | `cmfib/m/n` | 5 … 24,88 (12) |
| `weight: 400, style: "oblique"` | `CMSuperFibonacci-Slanted.otf` | `sffs` (`ecfs` / `lafs`) | `cmfib/m/sl` | 5 … 24,88 (12) |

**CM-Super Funny** — `font: "CM-Super Funny"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperFunny-Regular.otf` | `sfff` (`ecff` / `laff`) | `cmfr/m/n` | 9 … 35,83 (10) |
| `weight: 400, style: "italic"` | `CMSuperFunny-Italic.otf` | `sffi` (`ecfi` / `lafi`) | `cmfr/m/it` | 9 … 35,83 (10) |

**CM-Super Concrete** — `font: "CM-Super Concrete"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperConcrete-Regular.otf` | `sform` (`eorm` / `laorm`) + капитель `sfocc` | `ccr/m/n`; `ccr/m/sc` (капитель) | 5 … 10 (6) |
| `weight: 400, style: "oblique"` | `CMSuperConcrete-Slanted.otf` | `sfosl` (`eosl` / `laosl`) | `ccr/m/sl` | 5 … 10 (6) |
| `weight: 400, style: "italic"` | `CMSuperConcrete-Italic.otf` | `sfoti` (`eoti` / `laoti`) | `ccr/m/it` | 10 |

**CM-Super Bright** — `font: "CM-Super Bright"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperBright-Regular.otf` | `sfbmr` (`ebmr` / `labmr`) | `cmbr/m/n` | 8, 9, 10, 17,28 |
| `weight: 400, style: "oblique"` | `CMSuperBright-Slanted.otf` | `sfbmo` (`ebmo` / `labmo`) | `cmbr/m/it`; `cmbr/m/sl` | 8, 9, 10, 17,28 |
| `weight: 600` | `CMSuperBright-Semibold.otf` | `sfbsr` (`ebsr` / `labsr`) | `cmbr/b/n`; `cmbr/bx/n`; `cmbr/sb/n` | 8, 9, 10, 17,28 |
| `weight: 600, style: "oblique"` | `CMSuperBright-SemiboldSlanted.otf` | `sfbso` (`ebso` / `labso`) | `cmbr/sb/it`; `cmbr/sb/sl` | 8, 9, 10, 17,28 |
| `weight: 700` | `CMSuperBright-Bold.otf` | `sfbbx` (`ebbx` / `labbx`) | `cmbr/b/n`; `cmbr/bx/n` | 10 (ниже 9 pt — рисунки sfbsr) |

**CM-Super Bright Typewriter** — `font: "CM-Super Bright Typewriter"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 300` | `CMSuperBrightTypewriter-Light.otf` | `sfbtl` (`ebtl` / `labtl`) | `cmtl/m/n` | 10 |
| `weight: 300, style: "oblique"` | `CMSuperBrightTypewriter-LightSlanted.otf` | `sfbto` (`ebto` / `labto`) | `cmtl/m/it`; `cmtl/m/sl` | 10 |

**CM-Super Sans Quotation** — `font: "CM-Super Sans Quotation"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperSansQuotation-Regular.otf` | `sfsq` (`ecsq` / `lasq`) | — (нет в стандартных `.fd`: шрифт задаётся только по имени `\font`) | 8 |
| `weight: 400, style: "oblique"` | `CMSuperSansQuotation-Slanted.otf` | `sfqi` (`ecqi` / `laqi`) | — (нет в стандартных `.fd`: шрифт задаётся только по имени `\font`) | 8 |

**CM-Super SliTeX** — `font: "CM-Super SliTeX"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperSliTeX-Regular.otf` | `sflq` (`eclq` / `lalq`) | `lcmss/m/n` | 8 |
| `weight: 400, style: "oblique"` | `CMSuperSliTeX-Slanted.otf` | `sfli` (`ecli` / `lali`) | `lcmss/m/it`; `lcmss/m/sl` | 8 |
| `weight: 700` | `CMSuperSliTeX-Bold.otf` | `sflb` (`eclb` / `lalb`) | `lcmss/bx/n` | 8 |
| `weight: 700, style: "oblique"` | `CMSuperSliTeX-BoldSlanted.otf` | `sflo` (`eclo` / `lalo`) | `lcmss/bx/it`; `lcmss/bx/sl` | 8 |

**CM-Super SliTeX Typewriter** — `font: "CM-Super SliTeX Typewriter"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperSliTeXTypewriter-Regular.otf` | `sfltt` (`ecltt` / `laltt`) | `lcmtt/m/n` | 8 |
| `weight: 400, style: "italic"` | `CMSuperSliTeXTypewriter-Italic.otf` | `sfit10` (`ecit1000` / `lait1000`), масштабируется (`lcmtt/m/it`) | `lcmtt/m/it` | 10 |

**CM-Super SliTeX Invisible** — `font: "CM-Super SliTeX Invisible"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperSliTeXInvisible-Regular.otf` | `isflq` (`ieclq` / `ilalq`) | `lcmss/m/In` | 8 |
| `weight: 400, style: "oblique"` | `CMSuperSliTeXInvisible-Slanted.otf` | `isfli` (`iecli` / `ilali`) | `lcmss/m/Iit`; `lcmss/m/Isl` | 8 |
| `weight: 700` | `CMSuperSliTeXInvisible-Bold.otf` | `isflb` (`ieclb` / `ilalb`) | `lcmss/bx/In` | 8 |
| `weight: 700, style: "oblique"` | `CMSuperSliTeXInvisible-BoldSlanted.otf` | `isflo` (`ieclo` / `ilalo`) | `lcmss/bx/Iit`; `lcmss/bx/Isl` | 8 |

**CM-Super SliTeX Typewriter Invisible** — `font: "CM-Super SliTeX Typewriter Invisible"`

| Typst | Файл `fonts/auto/` | Type 1 (TFM T1 / T2A) | NFSS (кодировки) | Рисунки, pt |
|:---|:---|:---|:---|:---|
| `weight: 400` | `CMSuperSliTeXTypewriterInvisible-Regular.otf` | `isfltt` (`iecltt` / `ilaltt`) | `lcmtt/m/In` | 8 |

Капитель (`smcp`, `c2sc`) сделана как в LaTeX: строчные буквы заменяются буквами из отдельного шрифта капители (eccc, ecsc, ecxc, ecoc, ectc, eocc), прописные остаются обычными, цифры и знаки — как в основном шрифте. Включается `#smallcaps[…]` или `text(features: (smcp: 1))`. У Sans и курсива капители в LaTeX нет: `\textsc` в Sans берёт капитель Roman (`cmss/m/sc → cmr/m/sc`), помощник делает то же.

### Основное семейство «CM-Super» (Computer Modern Roman) в LaTeX и в Typst

| LaTeX (NFSS) | «Чистый» Typst | Помощник |
|---|---|---|
| `\rmfamily` (`cmr/m/n`) | `text(font: "CM-Super")` | `#rmfamily[…]` |
| `\itshape`, `\emph` (`cmr/m/it`) | `style: "italic"`, `_текст_` | `#itshape[…]`, `#textit[…]` |
| `\slshape` (`cmr/m/sl`) | `style: "oblique"` | `#slshape[…]`, `#textsl[…]` |
| `\scshape` (`cmr/m/sc`) | `smallcaps[…]` | `#scshape[…]`, `#textsc[…]` |
| `\bfseries` (`cmr/bx/n`) | `weight: 700`, `*текст*` | `#bfseries[…]`, `#textbf[…]` |
| `\bfseries\itshape` (`bx/it`) | `weight: 700, style: "italic"` | `#bfseries(itshape[…])` |
| `\bfseries\slshape` (`bx/sl`) | `weight: 700, style: "oblique"` | `#bfseries(slshape[…])` |
| `\bfseries\scshape` (`bx/sc`) | `weight: 700` + `smallcaps` | `#bfseries(scshape[…])` |
| `\fontseries{b}\selectfont` (`cmr/b/n`, полужирный cmb, не bx) | `weight: 600` | `#sbseries[…]` |
| `\fontshape{scsl}\selectfont` (`cmr/m/scsl`) | `style: "oblique"` + `smallcaps` | `#scslshape[…]` |
| `\fontshape{ui}\selectfont` («прямой курсив» cmu) | `font: "CM-Super Upright"` | `#ulshape[…]`, `#textulc[…]` |

### Соответствие остальных команд LaTeX ↔ Typst ↔ помощник

| LaTeX | «Чистый» Typst | Помощник `cm-super.typ` |
|---|---|---|
| `\textsf{x}`, `\sffamily` | `text(font: "CM-Super Sans")` | `#textsf[x]`, `#sffamily[…]` |
| `\texttt{x}`, `\ttfamily` | `` `x` ``, `text(font: "CM-Super Typewriter")` | `#texttt[x]`, `#ttfamily[…]`; `raw` — автоматически |
| `\fontfamily{cmvtt}` | `text(font: "CM-Super Typewriter Proportional")` | `#vttfamily[…]`, `#textvtt[…]` |
| `\fontfamily{cmdh}`, `cmfib`, `cmfr`, `ccr`, `cmbr`, `cmtl`, `lcmss`, `lcmtt` | `text(font: "CM-Super …")` | `#textfont("dunhill" \| "fibonacci" \| "funny" \| "concrete" \| "bright" \| "bright-tt" \| "slitex" \| "slitex-tt")[…]` |
| `\fontfamily{cmss}\fontseries{sbc}\selectfont` (полужирный узкий Sans) | `text(font: "CM-Super Sans", weight: 600, stretch: 75%)` | `#sbcseries[…]` |
| `\fontfamily{…}\fontseries{…}\fontshape{…}\selectfont` | — | `#nfss(family: "cmss", series: "bx", shape: "sl")[…]` — имена NFSS как в LaTeX |
| `\usepackage{ccfonts}` | — | `#show: ccfonts` |
| `\mdseries`, `\upshape`, `\normalfont` | `weight: 400`, `style: "normal"` | `#mdseries[…]`, `#upshape[…]`, `#normalfont[…]` |
| `\large … \Huge`, `\fontsize{a}{b}` | `text(size: tex-pt(…))` | `#large[…]`, `#fontsize(a, b)[…]` |
| `\selectlanguage{english}` | `#set text(lang: "en")` | `#show: selectlanguage.with("en")` |
| `\foreignlanguage{english}{x}` | `#text(lang: "en")[x]` | `#foreignlanguage("en")[x]` |
| `\oldstylenums{1234}` | `text(features: (onum: 1))[1234]` | — |
| `\frenchspacing` (babel russian включает его сам) | — | — (пробел после точки в Typst не растягивается) |

Серии NFSS в помощнике: `m` — обычная; `b` — полужирный у `cmr` (cmb) и ≡ `bx` у остальных; `sb` — полужирный у `cmbr`; `bx` — расширенный жирный; `sbc` — полужирный узкий Sans. Для сочетаний, которых в `.fd` нет, LaTeX подставляет другое начертание (с предупреждением), а Typst возьмёт ближайшее имеющееся. Справочник API — комментарии в начале `cm-super.typ`.

---

## 5. Язык и кодировка (T1 / T2A / T2B / T2C / X2 / TS1)

В pdfLaTeX кернинг, лигатуры и ширины зависят от кодировки шрифта (а она — от языка, babel). В Typst это реализовано **языком текста** (`lang`) через OpenType-языковые системы. Кириллические буквы всегда берут таблицы T2A (а недостающие — T2B, T2C, X2); `lang` решает, какие таблицы применяются к латинским буквам, цифрам и знакам препинания:

| `lang` | Таблицы метрик TFM (приоритет кодировок) |
|---|---|
| `"ru"`, `"uk"`, `"be"`, `"bg"`, `"sr"`, `"mk"`, `"kk"`, `"ky"`, `"tg"`, `"mn"`, `"tt"`, `"ba"`, `"ab"`, `"os"`, `"ce"`, `"cv"` | кириллический контекст: T2A → T1 → T2B → T2C → X2 → TS1 (латиница внутри русского абзаца тоже в T2A, как у babel/russian) |
| `"cu"` (церковнославянский) | X2 → T2A → T1 → T2B → T2C → TS1 |
| любой другой (`"en"`, `"de"`, `"fr"` …) | латинский контекст: T1 → TS1 → T2A → T2B → T2C → X2 |

Английская вставка в русском тексте: `#foreignlanguage("en")[…]` (как `\foreignlanguage{english}{…}`).

Покрытие Юникода: во всех 48 шрифтах одинаковый набор — 527 кодовых точек Юникода (Basic Latin — 95; Latin-1 Supplement — 96; Latin Extended-A — 63; Latin Extended-B — 2; Spacing Modifier Letters — 10; Cyrillic — 173; Latin Extended Additional — 1; General Punctuation — 43; Currency Symbols — 7; Letterlike Symbols — 9; лигатуры ﬀ ﬁ ﬂ ﬃ ﬄ — 5; прочее (стрелки, угловые и квадратные скобки, ␣, ♪ и т. п.) — 23). Cyrillic Extended-A/B и Glagolitic в CM-Super отсутствуют. Знаки TS1 (©, ®, ™, №, ‰, €, £ …) входят в тот же набор. Запасной шрифт для символов, которых нет в CM-Super (греческий и т. п.), — New Computer Modern (`fallback-fonts` в помощнике).

Запретить лигатуру (как `\textcompwordmark` в LaTeX или `"|` в babel) можно символом U+200C: `of\u{200c}fice` (или `#sym.zwnj`) даёт `f`+`fi` вместо `ffi`; кернинг вокруг него — по таблице TFM для «compound word mark».

---

## 6. Что проверено

Все числа получены на **итоговых** шрифтах из этого архива: настоящий pdfLaTeX (TeX Live 2023: pdfTeX 3.141592653-2.6-1.40.25) и Typst 0.15.1; в проверках 1–6 сравниваются положения начала каждого глифа в PDF (допуск — 0,0025 em, шум округления в PDF), в проверке 7 — сами контуры.

| № | Проверка | Объём | Результат |
|:-:|:---|:---|:---|
| 1 | **Метрики, кернинг, лигатуры, капитель по TFM**: каждый рисунок каждой гарнитуры во всех кодировках (T1, T2A, T2B, T2C, X2, TS1); LaTeX набирает строки из кодов символов шрифтом по TFM, Typst — те же строки по Юникоду статическим шрифтом | гарнитур: 48 (включая псевдоним `sflti`); рисунков: 354 (ещё 68 рисунков капители проверяются вместе с основными); строк: 150 792; положений глифов: 39 255 773 | несовпадений **0**, наибольшее смещение 0,00228 em |
| 2 | **Авто-шрифт = статические шрифты**: на каждом диапазоне размеров каждый слой переменного шрифта даёт те же глифы и позиции, что соответствующий статический (HarfBuzz по всем парам кернинга и лигатурам; затем настоящий Typst на реальном выводе PDF) | HarfBuzz: шрифтов 31, слоёв 339, проверок 13 014; Typst: пар строк 1 199 | расхождений **0** (HarfBuzz) и **0** (Typst) |
| 3 | **Границы между рисунками**: у каждой границы NFSS 25 размеров с шагом 0,0003 pt TeX (меньше кванта оси) и вся ось 4 … 40 pt с шагом 0,01 pt: выбор рисунка — без щелей и возвратов, на границе — меньший размер | HarfBuzz: границ 308, точек у границ 7 700, точек по оси 111 393; Typst: границ 308, точек 4 004 | плохих границ **0** (HarfBuzz) и **0** (Typst); до исправления диапазонов «щели» шириной в один квант оси были на 156 из 308 границ |
| 4 | **Выбор рисунка по размеру = NFSS**: для каждого `\DeclareFontShape` (T1, T2A, TS1; T2B, T2C, X2) и сетки размеров 4 … 44 pt с шагом 0,25 pt плюс окрестности границ настоящий LaTeX выбирает TFM, результат сравнивается с правилами шрифта | объявлений: 163 + 195; точек: 32 315 + 38 589 | неожиданных расхождений **0** (известные особенности — п. 8 README: `lcmtt/m/it`, `ccr/bx`, пакет `cmsd`) |
| 5 | **Сквозной тест «LaTeX и Typst»**: настоящий pdfLaTeX (NFSS + babel, `article` 10/11/12 pt) и Typst с `cm-super.typ` набирают одни и те же строки (53 сочетания семейства, серии и начертания × команды кегля и `\fontsize` × контексты ru/en, плюс строки со сменой стиля, языка и кегля внутри строки); сравниваются положения глифов и гарнитура каждого глифа | строк: 3 × 1 092 = 3 276 | совпало **3 220**; ещё 56 строк недоступны в LaTeX (нет объявления шрифта); наибольшее смещение 0,00121 em |
| 6 | **Межстрочный интервал**: расстояние между базовыми линиями по всем командам кегля `\tiny` … `\Huge`, классы 10/11/12 pt | 3 класса × 10 команд × 4 строки | расхождение не более 0,0009 bp |
| 7 | **Контуры = исходные Type 1**: у каждого глифа каждого слоя каждого шрифта (авто-размерного и статического; рисунки, капитель, двойники глифов) сравниваются команды и координаты всех точек с глифом исходного `.pfb` | шрифтов: 388; глифов: 473 091; точек: 32 698 011 | расхождений **0** (точка в точку; исключение — многоточие LaTeX: оно собрано из трёх точек, 837 шт.) |

Картинки-наложения (красный — pdfLaTeX, синий — Typst, чёрный — точное совпадение): `validation/overlay-styles.png` (стили и семейства) и `validation/overlay-sizes.png` (все команды кегля × Roman/Italic/Bold). Полный отчёт, методика и таблица по каждой гарнитуре — `validation/REPORT.md` (есть только в полном архиве).

---

## 7. Частые вопросы

* **Typst пишет «unknown font family».** Файлы `.otf` не загружены в проект или лежат вне его. На typst.app перетащите шрифты в панель файлов; в CLI укажите `--font-path`.
* **Шрифт «чуть крупнее», чем в LaTeX.** Кегль задан в Typst-pt (`12pt`), а не в TeX-pt. Используйте `tex-pt(12)` или `cm-super.with(size: 12)`.
* **Курсив/жирный выглядят как другое семейство.** Запрашивайте начертания из таблицы п. 4 (`weight: 700`, `style: "italic"` / `"oblique"`). `emph` и `strong` Typst делают именно это.
* **Капитель не работает на курсиве.** В LaTeX `\scshape` *заменяет* курсив прямой капителью и шрифта «курсивная капитель» нет; в помощнике `#textsc` тоже сбрасывает курсив. Наклонная капитель — `#scslshape[…]`.
* **Команда кегля «ломает» абзац.** Блочная команда (`#large[…]`) меняет интерлиньяж и поэтому начинает новый абзац; внутри строки пишите `#large(leading: false)[…]`.
* **Рисунок не тот, что я просил.** Авто-шрифт выбирает рисунок по размеру текста; чтобы зафиксировать, возьмите статический шрифт (`design()`).
* **Переносы и разбиение на строки отличаются от LaTeX.** Это алгоритм Typst, а не шрифт: ширины слов те же, но TeX и Typst по-разному переносят и растягивают пробелы (см. п. 8).

---

## 8. Ограничения (честно)

1. **Математика** — New Computer Modern Math, а не оригинальные CM (cmmi, cmsy, cmex).
2. **Курсивная коррекция (`\/`)** в Typst не эмулируется: LaTeX добавляет её автоматически после `\emph{…}` и `\textit{…}` (кроме места перед `.` и `,`), шрифт же не знает, что следует за ним в другом стиле. Следствие: пробел после курсивного слова может отличаться на доли пункта.
3. **Разбиение на строки, переносы и растяжение пробелов** — алгоритм Typst (свои паттерны переносов и свои параметры растяжения), поэтому конец строки в абзаце может не совпасть с TeX, даже при идентичных шрифтах. Ширины самих слов совпадают.
4. **Пробелы после точки.** `\nonfrenchspacing` (английский babel) растягивает пробел после предложения; в Typst этого нет. Babel russian включает `\frenchspacing`, поэтому на русском текст совпадает.
5. **Кернинг через границу стиля.** TeX кернит соседние буквы одного шрифта и через границу группы (`A{\color{red}V}`); Typst шейпит каждый фрагмент с отдельным стилем независимо.
6. **Размеры редких семейств.** У Fibonacci (T1: до 20,74 pt), Funny (от 9 pt), Concrete (рисунки 5–10 pt), SliTeX и Bright своя сетка размеров; pdfLaTeX для отсутствующих выдаёт `nullfont`, Typst масштабирует ближайший рисунок. Помощник «привязывает» размеры этих семейств к сетке NFSS (`fontsize()`, `textfont()`); при прямом `text(size: …)` привязки нет.
7. **Вложенность экзотических семейств.** Для Fibonacci, Funny, Concrete, SliTeX и узкого Sans помощник определяет список размеров по текущему шрифту: семейство должно быть *внутри* стиля, а кегль — *внутри* семейства (`#textfont("funny")[#large[…]]`), либо используйте `nfss(...)`. `design()` вызывайте внутри семейства (`#sffamily[#design(5)[…]]`).
8. **Пакеты, меняющие `.fd`.** `fix-cm` (T1/TS1 берут рисунки 5, 6, 7, 8, 9, 10, 12, 17,28 pt — для курсива и жирного набор короче — и масштабируют их на любой кегль) и `cmsd` (собственные рисунки Sans 5–7 pt в T1, жирный Sans ≥10 pt) выбирают рисунки иначе, чем стандартные `.fd`. Автоматически это не эмулируется; точное соответствие достигается статическими шрифтами и `design(…)` (п. 3). Для кириллицы (T2A) `fix-cm` ничего не меняет.
9. **Знаки TS1/T1 с разной шириной.** Для немногих знаков (например, в Fibonacci) ширина в T1 и TS1 различается; в Юникоде это один символ, берётся T1 (в кириллическом контексте — T2A/TS1 по приоритету из п. 5).
10. **Знаки, которых нет в LaTeX-кодировке T2A** (`‰ ‹ › ¿ ¡`): pdfLaTeX подставляет их из других шрифтов; в Typst берутся глифы CM-Super.
11. **Кодировки T2B, T2C, X2** доступны по Юникоду; церковнославянские таблицы (X2) включаются языком `"cu"`. Покрытие Юникода ограничено п. 5 (Cyrillic Extended-A/B и Glagolitic отсутствуют).
12. **Шум округления.** В PDF позиции глифов округляются: расхождение с pdfLaTeX ≤ 0,0023 em.

---

## 9. Лицензия

* **Шрифты** (`fonts/`) — производная работа от **CM-Super 0.3.4** (© 2001, 2002 Vladimir Volovich), контуры — Computer Modern (Donald E. Knuth). Лицензия — **GNU GPL v2 или новее с исключением для шрифтов**: *«As a special exception, permission is granted to include these font programs in a Postscript or PDF file that consists of a document that contains text to be displayed or printed using these fonts, regardless of the conditions or license applying to the document itself.»* То есть PDF, собранные с этими шрифтами, можно распространять на любых условиях (поле лицензии вшито в таблицу `name` каждого шрифта). Тексты — в `docs/`.
* **Помощник `cm-super.typ`, `main.typ`, `example.typ`** и скрипты `build/`, `validation/scripts/` — общественное достояние (CC0).

---

## 10. Структура и воспроизводимость

```
CM-Super-Typst/
├── README.md, VERSION.txt, cm-super.typ
├── main.typ, main.pdf, example.typ, example.pdf, example-static.typ, example-static.pdf
├── fonts/auto/*.otf                 # 48 переменных («авто-размер») шрифтов
├── fonts/static/<размер>/*.otf      # 340 статических шрифтов по рисункам
├── docs/                            # лицензии
├── validation/                      # REPORT.md, logs/, overlay-*.png, scripts/
└── build/                           # конвертер (Python + FontForge + fontTools)
```

Конвертация: контуры из `.pfb` (FontForge) → слои рисунков в одном шрифте (ось `opsz` 5…36 + `FeatureVariations`/`rvrn`), метрики, кернинг и лигатуры — из TFM (`cmsmetrics.py`), таблицы GSUB/GPOS — `assemble.py`; правила выбора рисунка — `cmsfams.py`. Подробности и команды — `build/README.txt`.
