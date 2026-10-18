# CUDA Recipes 004: Bolt on a Small Card

**Status:** data collection complete; Host C is the main speed result; package prepared for review.

## Question

How does NVIDIA Nemotron 3.5 Bolt 74B-A9B perform when only 8, 12, or 16GB of a 24GB RTX 3090 is available and MoE experts are placed in host RAM? Which contexts fit, and what is the speed cost?

Study 002 showed the full model fits its native 256K context on a 24GB RTX 3090. This study caps available VRAM and uses llama.cpp's `--n-cpu-moe` setting for expert offload.

## Setup

| | |
|---|---|
| GPU | RTX 3090 24GB; RunPod for calibration/PPL/cloud repetitions and a full-machine Vast desktop-class host for the main speed table |
| Main speed host | Intel Core i5-11600K, 6C/12T, 11.52-vCPU quota (96%), 64,125 MiB RAM, PCIe Gen4 x16; Host C snapshot is in `DATA/hosts.json` |
| Model | Nemotron 3.5 Bolt 74B-A9B, 2-bit 24GB GGUF; SHA256 is in `DATA/hosts.json` |
| Engine | llama.cpp commit `620d2225cc436ab0b001e3200e590e3b286ef9ab` |
| Offload | Chosen `--n-cpu-moe` per budget, selected against budget minus 500 MiB |
| KV cache | q8_0 K/V; flash attention on |
| Context | Load tests at 32K/128K/256K; bench at depths 0/32K/64K/118K |
| Perplexity | Wikitext-2 test, 2K context, 8 chunks; CPU expert path enabled for offloaded budgets |

## Results

See [RESULTS.md](RESULTS.md), [KEY_FINDINGS.md](KEY_FINDINGS.md), and [LIMITATIONS.md](LIMITATIONS.md). Host snapshots are in `DATA/hosts.json`; detailed field definitions are in [DATA/SCHEMA.md](DATA/SCHEMA.md).

![Host C decode by fill depth](CHARTS/decode-vs-depth.png)

![Host C and cloud Host A thread sweeps](CHARTS/thread-sweep.png)

![PPL by budget](CHARTS/ppl-by-budget.png)

![12GB cloud versus desktop spread](CHARTS/cloud-vs-desktop-12gb.png)

## Validation

Run `python3 validate.py` from this folder. `SHA256SUMS` covers the public package artifacts. Models, Wikitext-2 input data, and raw run logs are retained under `_internal/` and are not part of the public data package.

## Scope

The capped 8/12/16GB conditions are not measurements on physical small cards. This study measures fit and performance, not long-context answer quality.
