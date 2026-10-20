#!/usr/bin/env bash
set -euo pipefail
: "${LLAMA_CPP_DIR:?Set LLAMA_CPP_DIR outside the public repository}"
: "${LLAMA_CPP_REV:=620d2225cc436ab0b001e3200e590e3b286ef9ab}"
if [[ -z "${CUDA_TOOLKIT_ROOT:-}" ]]; then
  if [[ -x /usr/local/cuda-12.8/bin/nvcc ]]; then CUDA_TOOLKIT_ROOT=/usr/local/cuda-12.8
  else CUDA_TOOLKIT_ROOT=/usr/local/cuda
  fi
fi
: "${CUDACXX:=$CUDA_TOOLKIT_ROOT/bin/nvcc}"
export CUDACXX
if [[ -d "$LLAMA_CPP_DIR/.git" ]]; then
  git -C "$LLAMA_CPP_DIR" fetch --depth 1 origin "$LLAMA_CPP_REV"
else
  git clone --filter=blob:none --no-checkout https://github.com/ggml-org/llama.cpp.git "$LLAMA_CPP_DIR"
fi
git -C "$LLAMA_CPP_DIR" checkout --detach "$LLAMA_CPP_REV"
rm -rf "$LLAMA_CPP_DIR/build"
cmake -S "$LLAMA_CPP_DIR" -B "$LLAMA_CPP_DIR/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_COMPILER="$CUDACXX" \
  -DCUDAToolkit_ROOT="$CUDA_TOOLKIT_ROOT" \
  -DCMAKE_CUDA_ARCHITECTURES=120 \
  -DGGML_CUDA=ON -DGGML_NATIVE=ON \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON
cmake --build "$LLAMA_CPP_DIR/build" --parallel "$(nproc)" --target llama-server llama-cli
"$LLAMA_CPP_DIR/build/bin/llama-server" --version
"$LLAMA_CPP_DIR/build/bin/llama-server" --help > "$LLAMA_CPP_DIR/server-help.txt"
