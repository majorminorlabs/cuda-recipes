#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
M3=$(find /workspace/models/UD-Q3_K_XL -maxdepth 1 -name "*.gguf" | sort | head -1)
while tmux has-session -t q3_depth 2>/dev/null; do sleep 5; done
/usr/bin/time -v -o logs/server_q3_base.time /workspace/llama.cpp/build/bin/llama-server -m "$M3" -ngl 99 --n-cpu-moe 36 -c 32768 -fa on -t 16 --load-mode none --port 18082 > logs/server_q3_base.log 2>&1 &
spid=$!
echo "$spid" > receipts/server_q3_base.pid
ready=0
for i in $(seq 1 7200); do
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:18082/health 2>/dev/null || true)
  if [ "$code" = 200 ]; then ready=1; break; fi
  if ! kill -0 "$spid" 2>/dev/null; then break; fi
  sleep 0.5
done
if [ "$ready" != 1 ]; then echo "Q3 base server failed to become healthy" > logs/q3_base_server_failed.txt; exit 1; fi
python3 scripts/score.py --label q3_base --url http://localhost:18082 > logs/score_q3_base.log 2>&1
kill "$spid" 2>/dev/null || true
wait "$spid" 2>/dev/null || true
