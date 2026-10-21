#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
label=$1
shift
T=$(cat receipts/T.txt)
export CUDA_HOME=/usr/local/cuda-12.8
export PATH="$CUDA_HOME/bin:$PATH"
mkdir -p logs
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu --format=csv -lms 500 > "logs/vram_${label}.csv" 2> "logs/vram_${label}.err" &
mon=$!
set +e
/usr/bin/time -v -o "logs/${label}.time" /workspace/llama.cpp/build/bin/llama-bench "$@" -o jsonl > "logs/${label}.jsonl" 2> "logs/${label}.stderr"
status=$?
kill "$mon" 2>/dev/null
wait "$mon" 2>/dev/null
set -e
printf '%s\n' "$status" > "logs/${label}.exit_code"
exit "$status"
