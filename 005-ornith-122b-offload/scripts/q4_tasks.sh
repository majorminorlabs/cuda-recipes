#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
M4=$(find /workspace/models/UD-Q4_K_XL -maxdepth 1 -name '*.gguf' | sort | head -1)
start_server() {
  local label=$1 port=$2; shift 2
  tmux new-session -d -s "srv_${label}" "/usr/bin/time -v -o /workspace/005/logs/server_${label}.time /workspace/llama.cpp/build/bin/llama-server -m '$M4' -ngl 99 --n-cpu-moe 38 -c 32768 -fa on -t 16 --load-mode none --port $port $* > /workspace/005/logs/server_${label}.log 2>&1"
}
wait_ready() {
  local port=$1 max=${2:-3600}
  for i in $(seq 1 "$max"); do
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${port}/health" 2>/dev/null || true)
    [ "$code" = 200 ] && return 0
    sleep 0.5
  done
  return 1
}
start_server q4_base 8080
if ! wait_ready 8080; then
  echo 'Q4 base server did not become healthy' > logs/q4_base_server_failed.txt
  tmux kill-session -t srv_q4_base 2>/dev/null || true
  exit 1
fi
python3 scripts/score.py --label q4_base --url http://localhost:8080 > logs/score_q4_base.log 2>&1
tmux kill-session -t srv_q4_base 2>/dev/null || true
start_server q4_mtp 8081 --spec-type draft-mtp
if ! wait_ready 8081 1200; then
  echo 'draft-mtp flag rejected or server failed during startup; MTP scoring skipped.' > logs/mtp_skipped.txt
  tmux kill-session -t srv_q4_mtp 2>/dev/null || true
  exit 0
fi
python3 scripts/score.py --label q4_mtp --url http://localhost:8081 > logs/score_q4_mtp.log 2>&1
tmux kill-session -t srv_q4_mtp 2>/dev/null || true
