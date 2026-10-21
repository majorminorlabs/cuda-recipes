#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
M4=$(find /workspace/models/UD-Q4_K_XL -maxdepth 1 -name '*.gguf' | sort | head -1)
tmux new-session -d -s srv_q4_mtp_retry "/usr/bin/time -v -o /workspace/005/logs/server_q4_mtp_retry.time /workspace/llama.cpp/build/bin/llama-server -m '$M4' -ngl 99 --n-cpu-moe 38 -c 32768 -fa on -t 16 --load-mode none --spec-type draft-mtp --port 18081 > /workspace/005/logs/server_q4_mtp_retry.log 2>&1"
ready=0
for i in $(seq 1 3600); do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 http://localhost:18081/health 2>/dev/null || true)
  if [ "$code" = 200 ]; then ready=1; break; fi
  if ! tmux has-session -t srv_q4_mtp_retry 2>/dev/null; then break; fi
  sleep 0.5
done
if [ "$ready" != 1 ]; then
  echo 'MTP server failed startup on alternate port; see server_q4_mtp_retry.log' > logs/mtp_retry_failed.txt
  tmux kill-session -t srv_q4_mtp_retry 2>/dev/null || true
  exit 1
fi
python3 scripts/score.py --label q4_mtp --url http://localhost:18081 > logs/score_q4_mtp_retry.log 2>&1
tmux kill-session -t srv_q4_mtp_retry 2>/dev/null || true
