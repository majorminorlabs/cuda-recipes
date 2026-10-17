# Context Ceiling on 24GB

Update: whether these models can use long context is tested in [CUDA Recipes 003](https://majorminor.xyz/research/cuda-recipes-003).

*CUDA Recipes 002 · MAJOR//MINOR* · **Complete**

CUDA Recipes 002 measures context fit and synthetic fill speed for Nemotron 3.5 Bolt 74B-A9B (native 2-bit GGUF) and Qwen3.8 27B Q4_K_M on one RTX 3090 24GB. Nemotron loaded fully at its 262,144-token native maximum; Qwen's largest full-GPU load was 221,184 tokens. At 131K fill, Nemotron decoded at 52.2 tok/s and processed prompts at 671.5 tok/s; Qwen measured 23.3 decode and 449.8 prompt tok/s. At empty context Qwen processed prompts faster (1,236.9 tok/s mean versus Nemotron 821.9), so prompt throughput crossed over with deeper fill.

## The recipe

Tested on an RTX 3090 24GB (headless, nothing else on the GPU).

**Build llama.cpp at the tested commit**
```sh
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
git checkout 620d2225cc436ab0b001e3200e590e3b286ef9ab
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86
cmake --build build --config Release -j
```

**Download the exact files**
```sh
huggingface-cli download nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF \
  NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf \
  --revision e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246 --local-dir models
huggingface-cli download Abiray/Qwen3.8-27B-Q4_K_M-GGUF \
  Qwen3.8-27B-Q4_K_M.gguf \
  --revision f7a1cda580fe828415151042bf9f3dc5bb8b0d76 --local-dir models
```

**Nemotron Bolt at its full 256K context** (peaked at 22,366 MiB)
```sh
./build/bin/llama-server -m models/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf \
  --ctx-size 262144 --parallel 1 -b 512 -ub 128 \
  --cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 --flash-attn on --jinja
```

**Qwen3.8 27B Q4_K_M at 192K** (peaked at 22,908 MiB)
```sh
./build/bin/llama-server -m models/Qwen3.8-27B-Q4_K_M.gguf \
  --ctx-size 196608 --parallel 1 -b 512 -ub 128 \
  --cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 --flash-attn on --jinja
```

Qwen's ceiling was 221,184 tokens, but that left only 782 MiB free on a headless card. If your 3090 also drives a display, 196,608 is the safer setting. If you're on a newer card than a 3090, change `CMAKE_CUDA_ARCHITECTURES` (e.g. 89 for 40-series, 120 for 50-series).

![Peak VRAM by context](CHARTS/fig1-peak-vram-context.svg)

## Results and reproduction

See [RESULTS.md](RESULTS.md), [KEY_FINDINGS.md](KEY_FINDINGS.md), [METHODOLOGY.md](METHODOLOGY.md), and [LIMITATIONS.md](LIMITATIONS.md). The CSVs are validated by `python3 validate.py`; derive headline figures with `python3 scripts/derived_stats.py` and regenerate plots with `python3 scripts/make_charts.py`.

The measured run used 0.867 GPU-hour. At the advertised $0.50/hour RTX 3090 rate, the cost is an **estimated** $0.43, not an invoice amount.

## Scope

Fit + speed only; no long-context quality or retrieval tests. llama-bench used synthetic fill. There was one run per depth above zero. Driver 610.57.04 differs from 001's 580.126.20, and speed was measured with llama-bench rather than 001's task harness, so 001 and 002 speeds are not the same measurement. The first 16K Nemotron anchor attempt was excluded after a log-decoding crash in our runner; the runner was fixed, and this was not a model failure.
