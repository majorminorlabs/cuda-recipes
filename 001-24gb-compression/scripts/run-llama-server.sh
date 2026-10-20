#!/usr/bin/env bash
set -euo pipefail
: "${LLAMA_CPP_DIR:?Set LLAMA_CPP_DIR}"
: "${MODEL_DIR:?Set MODEL_DIR}"
# Prefer the host-injected driver library over the image's CUDA forward-compat
# shim. NVIDIA does not support that shim for consumer GeForce GPUs.
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
MODEL=${1:?Pass nemotron or qwen}
case "$MODEL" in
  nemotron) MODEL_FILE="$MODEL_DIR/nemotron/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf" ;;
  qwen) MODEL_FILE="$MODEL_DIR/qwen/Qwen3.8-27B-Q4_K_M.gguf" ;;
  *) echo 'unknown model' >&2; exit 2 ;;
esac
exec "$LLAMA_CPP_DIR/build/bin/llama-server" \
  --model "$MODEL_FILE" --host 127.0.0.1 --port 8000 \
  --ctx-size 16384 --parallel 1 --batch-size 512 --ubatch-size 128 \
  --cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 \
  --flash-attn on --jinja --verbose
