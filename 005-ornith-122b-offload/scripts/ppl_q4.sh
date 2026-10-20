#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
while tmux has-session -t q3_base_after_depth 2>/dev/null; do sleep 5; done
M4=$(find /workspace/models/UD-Q4_K_XL -maxdepth 1 -name "*.gguf" | sort | head -1)
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu --format=csv -lms 500 > logs/vram_ppl_q4.csv 2> logs/vram_ppl_q4.err &
mon=$!
set +e
/usr/bin/time -v -o logs/ppl_q4.time /workspace/llama.cpp/build/bin/llama-perplexity -m "$M4" -f eval_neutral.txt -c 4096 --chunks 87 -ngl 99 --n-cpu-moe 38 -t 16 -fa on -lm none > logs/ppl_q4.log 2>&1
rc=$?
set -e
kill "$mon" 2>/dev/null || true
wait "$mon" 2>/dev/null || true
printf "%s\n" "$rc" > logs/ppl_q4.exit_code
