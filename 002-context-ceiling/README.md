# Context Ceiling on 24GB

*CUDA Recipes 002 · MAJOR//MINOR* · **Complete**

CUDA Recipes 002 measures context fit and synthetic fill speed for Nemotron 3.5 Bolt 74B-A9B (native 2-bit GGUF) and Qwen3.8 27B Q4_K_M on one RTX 3090 24GB. Nemotron loaded fully at its 262,144-token native maximum; Qwen's largest full-GPU load was 221,184 tokens. At 131K fill, Nemotron decoded at 52.2 tok/s and processed prompts at 671.5 tok/s; Qwen measured 23.3 decode and 449.8 prompt tok/s. At empty context Qwen processed prompts faster (1,236.9 tok/s mean versus Nemotron 821.9), so prompt throughput crossed over with deeper fill.

![Peak VRAM by context](CHARTS/fig1-peak-vram-context.svg)

## Results and reproduction

See [RESULTS.md](RESULTS.md), [KEY_FINDINGS.md](KEY_FINDINGS.md), [METHODOLOGY.md](METHODOLOGY.md), and [LIMITATIONS.md](LIMITATIONS.md). The CSVs are validated by `python3 validate.py`; derive headline figures with `python3 scripts/derived_stats.py` and regenerate plots with `python3 scripts/make_charts.py`.

The measured run used 0.867 GPU-hour. At the advertised $0.50/hour RTX 3090 rate, the cost is an **estimated** $0.43, not an invoice amount.

## Scope

Fit + speed only; no long-context quality or retrieval tests. llama-bench used synthetic fill. There was one run per depth above zero. Driver 610.57.04 differs from 001's 580.126.20, and speed was measured with llama-bench rather than 001's task harness, so 001 and 002 speeds are not the same measurement. The first 16K Nemotron anchor attempt was excluded after a log-decoding crash in our runner; the runner was fixed, and this was not a model failure.
