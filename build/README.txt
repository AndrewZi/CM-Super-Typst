Сборка шрифтов CM-Super для Typst (воспроизводимость)
=====================================================

Что здесь: Python-скрипты, которыми Type 1 шрифты CM-Super 0.3.4 превращены в OpenType для Typst, и данные, которые им нужны.
Для работы с готовыми шрифтами это НЕ нужно: см. ../README.md. Здесь — чтобы можно было проверить, как всё сделано, и пересобрать.

Требования
  * Python 3.10+; fontTools (4.x), numpy;
  * FontForge с Python-расширением (команда `fontforge -lang=py -script …`): читает .pfb и склеивает слои рисунков;
  * TeX Live с пакетами cm-super (файлы .pfb и .enc), ec и lh (TFM кодировок T1, T2A, T2B, T2C, X2, TS1), языковые таблицы LaTeX (kpsewhich);
  * для проверок (validation/): pdflatex, Typst CLI 0.15.x, uharfbuzz, PyMuPDF, pdfminer.six, Pillow.
  * Скрипты печатают по-русски: в консоли без UTF-8 (например, Windows) задайте `PYTHONUTF8=1` (set PYTHONUTF8=1) перед запуском.

Каталоги
  lib/       — сборка: paths.py (пути; переменные окружения CMS_DATA, CMS_PFB, CMS_ENC, CMS_OUT), cmsfams.py (гарнитуры, рисунки, правила выбора
               рисунка по размеру как в NFSS), cmsmetrics.py (метрики, кернинг, лигатуры из TFM), assemble.py (таблицы OpenType: cmap, GSUB, GPOS,
               ось opsz, FeatureVariations), build.py (сборка одного шрифта), jobs.py и run_all.py (все шрифты), ffmaster.py (этап FontForge),
               ff_pfbinfo.py (сводка по .pfb), tfmcache.py, unitab.py, stats_all.py.
  scripts/   — tfmlib.py (чтение TFM и .enc), unimap.py (Юникод ↔ имена глифов по таблицам LaTeX).
  data/      — designs.json (какие TFM относятся к какому рисунку .pfb), enc/ (cm-super-*.enc), tfm_needed.txt (список нужных TFM), gen_tfm.sh.

Порядок
  1. TFM:       bash data/gen_tfm.sh            # кладёт нужные .tfm в data/tfm (из TeX Live; недостающие собирает mktextfm)
  2. .pfb:      export CMS_PFB=/путь/к/fonts/type1/public/cm-super   (если не /usr/share/texmf/fonts/type1/public/cm-super)
  3. сводка:    fontforge -lang=py -script lib/ff_pfbinfo.py            # data/pfbinfo.json
  4. кэш TFM:   python3 lib/tfmcache.py                                 # data/tfm_all.pkl
  5. сборка:    python3 lib/run_all.py all 2                            # все шрифты, 2 процесса → out/auto (48 шт.), out/static/<размер>/ (340 шт.)
                python3 lib/run_all.py var 2                            # только авто-шрифты
  6. проверки:  см. ../validation/scripts/README.txt

Как устроен авто-шрифт: для каждой гарнитуры контуры всех рисунков (.pfb, FontForge) собираются в один CFF-шрифт, глифы рисунков получают суффиксы
«.dTOK» (TOK — токен размера, например .d0500), глифы капители — «.cc»; ось `opsz` 5 … 36 (по умолчанию 12) и FeatureVariations (`rvrn`) подменяют
глифы рисунка по кеглю; границы — середины между соседними размерами списка NFSS (assemble.opsz_cut: целые значения 14-битной оси, без щелей).
Языковые системы GSUB/GPOS: латинская (T1), кириллическая (T2A; языки RUS UKR BEL BGR SRB MKD KAZ KIR TAJ MNG TAT BSH CHU ABK OSS CHE) и
церковнославянская (X2, язык CSL). Заметка: HarfBuzz сопоставляет `lang: "sah"` (якутский) языковой системе YAK, а не SAH, поэтому латиница в якутском тексте
идёт в латинском контексте; кириллические буквы всегда в кириллическом.

Повторяемость: сборка детерминирована, кроме меток времени в таблице head. Проверено: пакетные скрипты (build/lib) собирают шрифты, таблицы которых
(кроме head) совпадают с поставляемыми байт в байт.
