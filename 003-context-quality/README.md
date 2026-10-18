# Long-Context Retrieval Quality on 24GB

*CUDA Recipes 003 · MAJOR//MINOR* · **Complete**

This study measures whether three local language models retrieve planted facts from prose at roughly 8K, 64K and 128K tokens on one RTX 3090 24GB. It also measures multi-fact retrieval, aggregation, multi-hop questions, prefill time and answer time.

## Headline

At 128K, single-fact retrieval remained 73–93% across the models, while four-fact retrieval fell to 0–27%. Multi-hop accuracy was 0/15 for Qwen3.6 and Nemotron and 2/15 for Qwen3.8. See [RESULTS.md](RESULTS.md) and the charts under [CHARTS](CHARTS/).

## Recipe and reproducibility

- Pinned llama.cpp revision: `620d2225cc436ab0b001e3200e590e3b286ef9ab`, CUDA sm_86.
- RTX 3090 24GB; 131,072 context; Q8_0 KV cache; all layers on GPU.
- Three frozen documents and 180 frozen questions; 15 questions per task type and length.
- Primary arm uses thinking off and a 256-token output limit. The separate exploratory Qwen3.6 run used thinking on and a 2,048-token cap.
- Run `python3 -m unittest discover -s tests -v`, `python3 scripts/derived_stats.py`, `python3 scripts/make_charts.py`, and `python3 validate.py` from this directory.

See [METHODOLOGY.md](METHODOLOGY.md), [SOURCES.md](SOURCES.md), [DATA/SCHEMA.md](DATA/SCHEMA.md), the manifests, and [SHA256SUMS](SHA256SUMS) for exact details. Raw inference responses remain in `_internal/` and are intentionally excluded from public outputs.

## Code arm

Phase 0 frozen; GPU run pending. The code arm uses the pinned Django BSD-3-Clause snapshot at `d430084791a61b31cecec132bce3dca19194f7f2`. It adds control, 64K and 128K code haystacks with 180 questions. Its estimated inference time is 0.575 GPU-hours (0.775 including allowance); target is 0.7 hours and hard stop is 0.9 hours. See `DATA/code/documents/manifest.json` and `DATA/code/questions.jsonl`.
