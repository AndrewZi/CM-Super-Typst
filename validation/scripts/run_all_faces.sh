#!/bin/bash
# запуск tfmtest.py по всем гарнитурам, 2 процесса
cd "$(dirname "$0")"
python3 -I -c "
import sys; sys.path.insert(0,'../lib')
import cmsfams as F
print('\n'.join(sorted(F.FACE)))" > faces.txt
cat faces.txt | xargs -P 2 -I{} sh -c 'python3 -W ignore tfmtest.py {} > logs/{}.log 2>&1; echo "{} exit=$?" >> logs/_summary.txt'
echo ALLDONE >> logs/_summary.txt
