#!/usr/bin/env bash
set -euo pipefail
: "${MODEL_DIR:?Set MODEL_DIR outside the public repository}"
mkdir -p "$MODEL_DIR"
python3 -m venv "$MODEL_DIR/hf-venv"
"$MODEL_DIR/hf-venv/bin/pip" install --disable-pip-version-check huggingface_hub
HF="$MODEL_DIR/hf-venv/bin/hf"
mkdir -p "$MODEL_DIR/nemotron" "$MODEL_DIR/qwen"
"$HF" download nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF \
  NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf \
  --revision e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246 --local-dir "$MODEL_DIR/nemotron"
"$HF" download Abiray/Qwen3.8-27B-Q4_K_M-GGUF \
  Qwen3.8-27B-Q4_K_M.gguf \
  --revision f7a1cda580fe828415151042bf9f3dc5bb8b0d76 --local-dir "$MODEL_DIR/qwen"
printf '%s  %s\n' \
  91d63363e782c8a3d5f4be42816eba8e0d42dd2530bd07a7d0d2dc440599af75 "$MODEL_DIR/nemotron/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf" \
  6a96cc760fc65cc6b9ea7f1922e3ff8b2a48c09f209456f23bbae9ef7032c867 "$MODEL_DIR/qwen/Qwen3.8-27B-Q4_K_M.gguf" | sha256sum --check
