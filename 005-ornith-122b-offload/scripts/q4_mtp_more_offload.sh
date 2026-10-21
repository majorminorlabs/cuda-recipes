#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
M4=$(find /workspace/models/UD-Q4_K_XL -maxdepth 1 -name '*.gguf' | sort | head -1)
for B in 42 44 46 49; do
  session="srv_mtp_B${B}"
  log="logs/server_q4_mtp_B${B}.log"
  tmux new-session -d -s "$session" "/usr/bin/time -v -o /workspace/005/logs/server_q4_mtp_B${B}.time /workspace/llama.cpp/build/bin/llama-server -m '$M4' -ngl 99 --n-cpu-moe $B -c 32768 -fa on -t 16 --load-mode none --spec-type draft-mtp --port 18081 > /workspace/005/$log 2>&1"
  ready=0
  for i in $(seq 1 2400); do
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 http://localhost:18081/health 2>/dev/null || true)
    if [ "$code" = 200 ]; then ready=1; break; fi
    if grep -q 'exiting due to model loading error\|exiting due to HTTP server error' "/workspace/005/$log" 2>/dev/null; then break; fi
    if ! tmux has-session -t "$session" 2>/dev/null; then break; fi
    sleep 0.5
  done
  if [ "$ready" = 1 ]; then
    printf 'MTP succeeded at ncmoe=%s, port=18081.\n' "$B" > logs/mtp_succeeded.txt
    python3 scripts/score.py --label q4_mtp --url http://localhost:18081 > "logs/score_q4_mtp_B${B}.log" 2>&1
    tmux kill-session -t "$session" 2>/dev/null || true
    exit 0
  fi
  printf 'ncmoe=%s failed to load at context 32768.\n' "$B" >> logs/mtp_offload_attempts.txt
  tmux kill-session -t "$session" 2>/dev/null || true
done
echo 'MTP unavailable: context failed to load at tested ncmoe 38, 40, 42, 44, 46, and 49 due to CUDA memory allocation.' > logs/mtp_unavailable.txt
