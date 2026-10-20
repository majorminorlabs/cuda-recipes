#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
T=$(cat /workspace/005/receipts/T.txt)
export CUDA_HOME=/usr/local/cuda-12.8
export PATH="$CUDA_HOME/bin:$PATH"
export CUDACXX="$CUDA_HOME/bin/nvcc"
if [ ! -d /workspace/llama.cpp/.git ]; then git clone https://github.com/ggml-org/llama.cpp /workspace/llama.cpp; fi
cd /workspace/llama.cpp
git fetch --tags
tag=$(git tag --sort=-v:refname | awk '/^b[0-9]+$/ {print; exit}')
num=${tag#b}
if [ -z "$tag" ] || [ "$num" -lt 11736 ]; then
  echo "STOP: newest llama.cpp tag is '$tag', below b11736" | tee /workspace/005/receipts/build_stop.txt
  exit 2
fi
git checkout "$tag"
printf '%s %s\n' "$tag" "$(git rev-parse HEAD)" > /workspace/005/receipts/llama_commit.txt
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_BUILD_TYPE=Release
cmake --build build -j "$T" --target llama-server llama-bench llama-perplexity
./build/bin/llama-bench --help > /workspace/005/logs/bench_help.txt 2>&1
./build/bin/llama-server --help > /workspace/005/logs/server_help.txt 2>&1
for flag in -ncmoe -d -fa -mmp; do grep -q -- "$flag" /workspace/005/logs/bench_help.txt || { echo "Missing bench flag $flag" | tee /workspace/005/receipts/build_stop.txt; exit 3; }; done
grep -q -- '--n-cpu-moe' /workspace/005/logs/server_help.txt || { echo 'Missing --n-cpu-moe' | tee /workspace/005/receipts/build_stop.txt; exit 3; }
grep -q -- '--spec-type' /workspace/005/logs/server_help.txt || { echo 'Missing --spec-type' | tee /workspace/005/receipts/build_stop.txt; exit 3; }
