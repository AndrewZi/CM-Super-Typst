#!/bin/bash
# gen_tfm.sh — положить в data/tfm все TFM из tfm_needed.txt: взять из TeX Live (kpsewhich), недостающие собрать METAFONT-ом (mktextfm).
cd "$(dirname "$0")"
mkdir -p tfm
: > tfm_not_found.txt
while read -r n; do
  [ -s "tfm/$n.tfm" ] && continue
  p=$(kpsewhich "$n.tfm" 2>/dev/null)
  if [ -z "$p" ]; then mktextfm "$n" >/dev/null 2>&1; p=$(kpsewhich "$n.tfm" 2>/dev/null); fi
  if [ -n "$p" ]; then cp "$p" "tfm/$n.tfm"; else echo "$n" >> tfm_not_found.txt; fi
done < tfm_needed.txt
echo "готово: $(ls tfm | wc -l) файлов TFM, не найдено: $(wc -l < tfm_not_found.txt)"
