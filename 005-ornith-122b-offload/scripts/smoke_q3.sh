#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
T=$(cat receipts/T.txt)
M3=$(find /workspace/models/UD-Q3_K_XL -maxdepth 1 -name '*.gguf' | sort | head -1)
BIN=/workspace/llama.cpp/build/bin/llama-server
start=$(date +%s.%N)
tmux new-session -d -s smoke_q3 "/usr/bin/time -v -o /workspace/005/logs/smoke_q3.time $BIN -m '$M3' -ngl 99 --n-cpu-moe 49 -c 8192 -fa on -t $T --load-mode none --port 8080 > /workspace/005/logs/smoke_q3.log 2>&1"
ready=0
for i in $(seq 1 3600); do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 http://localhost:8080/health 2>/dev/null || true)
  if [ "$code" = 200 ]; then ready=1; break; fi
  sleep 0.5
done
end=$(date +%s.%N)
python3 - "$start" "$end" <<'PY' > logs/load_time_q3.txt
import sys
print(f'{float(sys.argv[2])-float(sys.argv[1]):.3f} seconds to HTTP 200 from /health')
PY
if [ "$ready" != 1 ]; then echo 'STOP: Q3 server failed to become healthy' >> receipts/stop_reason.txt; exit 10; fi
cat > logs/smoke_q3_request.json <<'JSON'
{"model":"local","messages":[{"role":"user","content":"What is 17*23? Answer with the number only."}],"chat_template_kwargs":{"enable_thinking":false},"temperature":0}
JSON
pass=0
for attempt in 1 2; do
  curl -sS --max-time 300 http://localhost:8080/v1/chat/completions -H 'Content-Type: application/json' --data-binary @logs/smoke_q3_request.json > "logs/smoke_q3_response_${attempt}.json" || true
  content=$(jq -r '.choices[0].message.content // empty' "logs/smoke_q3_response_${attempt}.json" 2>/dev/null || true)
  printf 'attempt=%s content=%s\n' "$attempt" "$content" >> logs/smoke_q3_result.txt
  if [ "$content" = 391 ]; then pass=1; break; fi
done
tmux kill-session -t smoke_q3 2>/dev/null || true
if [ "$pass" != 1 ]; then echo 'STOP: Q3 smoke test failed twice' >> receipts/stop_reason.txt; exit 11; fi
