#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
while tmux has-session -t ppl_q4_retry 2>/dev/null; do sleep 10; done
rc=$(cat logs/ppl_q4_retry.exit_code 2>/dev/null || echo 99)
ppl=$(python3 - <<PY
import re
s=open("logs/ppl_q4_retry.log", errors="replace").read()
patterns=[r"Final estimate:\s*PPL\s*=\s*([0-9]+(?:\.[0-9]+)?)",r"perplexity\s*=\s*([0-9]+(?:\.[0-9]+)?)"]
for p in patterns:
 m=list(re.finditer(p,s,re.I))
 if m: print(m[-1].group(1)); break
PY
)
if [ "$rc" != 0 ] || [ -z "$ppl" ]; then echo "Q4 PPL failed or could not be parsed; Q3 PPL not run automatically. rc=$rc value=$ppl" > logs/ppl_q3_skipped.txt; exit 0; fi
if python3 - "$ppl" <<PY
import sys
raise SystemExit(0 if float(sys.argv[1]) > 11.525 else 1)
PY
then echo "Q4 PPL $ppl exceeds 2x reference; Q3 PPL stopped by runbook rule." > logs/ppl_q3_skipped.txt; exit 0; fi
M3=$(find /workspace/models/UD-Q3_K_XL -maxdepth 1 -name "*.gguf" | sort | head -1)
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu --format=csv -lms 500 > logs/vram_ppl_q3.csv 2> logs/vram_ppl_q3.err &
mon=$!
set +e
/usr/bin/time -v -o logs/ppl_q3.time /workspace/llama.cpp/build/bin/llama-perplexity -m "$M3" -f eval_neutral.txt -c 4096 --chunks 87 -ngl 99 --n-cpu-moe 36 -t 16 -fa on > logs/ppl_q3.log 2>&1
rc=$?
set -e
kill "$mon" 2>/dev/null || true
wait "$mon" 2>/dev/null || true
printf "%s\n" "$rc" > logs/ppl_q3.exit_code
