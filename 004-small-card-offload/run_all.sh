#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
finish_run() {
  local run_status=$? sync_status stop_status
  trap - EXIT
  set +e
  if [[ -n "${POD_SYNC_CMD:-}" ]]; then
    bash -c "$POD_SYNC_CMD" _ "$ROOT/DATA/" "$ROOT/_internal/raw/"
    sync_status=$?
  else
    printf 'POD_SYNC_CMD is unset; cannot sync run outputs\n' >&2
    sync_status=1
  fi
  if [[ -n "${POD_STOP_CMD:-}" ]]; then
    bash -c "$POD_STOP_CMD"
    stop_status=$?
  else
    printf 'POD_STOP_CMD is unset; cannot stop pod\n' >&2
    stop_status=1
  fi
  if (( run_status == 0 && sync_status != 0 )); then run_status=$sync_status; fi
  if (( run_status == 0 && stop_status != 0 )); then run_status=$stop_status; fi
  exit "$run_status"
}
trap finish_run EXIT

: "${POD_CREATED_EPOCH:?Set this to the actual pod creation Unix timestamp}"
: "${POD_STOP_CMD:?Set the provider command that hard-stops this pod}"
: "${POD_SYNC_CMD:?Set the transfer command; it receives DATA/ and _internal/raw/ paths as \$1 and \$2}"
: "${MODEL_FILE:?Set MODEL_FILE to the pinned Bolt GGUF}"
: "${WIKITEXT_FILE:?Set WIKITEXT_FILE to the Wikitext-2 test file}"
mkdir -p "$ROOT/_internal/raw"

# Start the creation-time hard stop before any capture or GPU work.
nohup python3 "$ROOT/scripts/phase0.py" watchdog \
  >"$ROOT/_internal/raw/watchdog.log" 2>&1 </dev/null &
echo "Watchdog started (pid $!) from POD_CREATED_EPOCH=$POD_CREATED_EPOCH"

python3 "$ROOT/scripts/phase0.py" host
python3 "$ROOT/scripts/phase0.py" calibrate
python3 "$ROOT/scripts/phase0.py" load
if python3 "$ROOT/scripts/run_ppl.py" >"$ROOT/_internal/raw/run-ppl.log" 2>&1; then
  cat "$ROOT/_internal/raw/run-ppl.log"
else
  ppl_status=$?
  printf 'run_ppl.py failed (exit %s); continuing to bench. See _internal/raw/run-ppl.log\n' "$ppl_status" >&2
  cat "$ROOT/_internal/raw/run-ppl.log" >&2
fi
python3 "$ROOT/scripts/phase0.py" bench
