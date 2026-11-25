# CUDA Recipes 008: Inkling 2 Mini on an RTX 3090

Two Inkling 2 Mini Q4 files were benchmarked on a 24GB RTX 3090 using llama.cpp commit `19bc41dbb41e858eebc269b49ccdec1f0d28880c`. Unsloth UD-Q4_K_M measured 59.106860 tok/s at tg128; AtomicChat uncensored AD-Q4_K measured 58.713510 tok/s. Each primary measurement has three repetitions.

Default batch settings failed at large configured contexts. Reducing batch/ubatch enabled 128K with F16 KV and 256K with Q8 KV. A verified rerun measured filled-context decode at 36.646339 / 36.685906 tok/s at 128K and 24.842185 / 25.018935 tok/s at 256K, base / uncensored. Each deep point has one repetition, and the deep rerun used a separate RTX 3090 host.

![Base UD-Q4_K_M generation and filled-context decode on an RTX 3090. Display labels are rounded; exact values are in the tables.](CHARTS/overview.png)

## Update 2026-11-24: DSpark speculative decoding

A later study tested the same base UD-Q4_K_M file in `llama-server` with Unsloth's DSpark drafter on one RTX 3090. Full method, tables and data are in [dspark-3090/](dspark-3090/). The original measurements below are unchanged.

Each ratio divides by a no-drafter arm on the **same build**, sampler and length, never by the 59.106860 tok/s figure above. Requests generated a fixed 128 or 1024 tokens with EOS suppressed; four prompts, three repetitions each, 336 requests in total. Means are of 12 request rates, rounded here.

| Build | Sampler, tokens | Off tok/s | Fastest tested drafter | On tok/s | Ratio |
|---|---|---:|---|---:|---:|
| Unsloth `b12675-mix-d14fe45` | greedy, 128 | 81.08 | default 0.50 GB, n-max 3 | 89.57 | 1.105 |
| Unsloth `b12675-mix-d14fe45` | greedy, 1024 | 79.20 | default 0.50 GB, n-max 3 | 93.23 | 1.177 |
| Unsloth `b12675-mix-d14fe45` | temp 1, 128 | 71.88 | default 0.50 GB, n-max 2 | 74.24 | 1.033 |
| Unsloth `b12675-mix-d14fe45` | temp 1, 1024 | 70.51 | default 0.50 GB, n-max 2 (only setting tested) | 72.84 | 1.033 |
| Unsloth `b12675-mix-d14fe45` | greedy, 128 | 81.08 | old 0.40 GB file, n-max 2 (optional) | 93.15 | 1.149 |
| Mainline `33aeb17` | greedy, 128 | 59.83 | n-max 2 | 79.72 | 1.332 |
| Mainline `33aeb17` | greedy, 1024 | 58.74 | n-max 5 (only setting tested) | 84.90 | 1.445 |

Gains depended on the prompt. The B-tree explanation prompt slowed down in every Unsloth greedy drafter cell, and some temperature 1 prompt and length combinations slowed on both builds. Greedy output text was not bit-identical with drafting on (12 of 180 greedy pairs had matching hashes). No quality evaluation was run.

## Measured rates

| Artifact | pp512 tok/s | tg128 tok/s | 128K F16, b256/ub128 | 256K Q8, b64/ub32 |
|---|---:|---:|---:|---:|
| Base UD-Q4_K_M | 1411.470954 | 59.106860 | 36.646339 | 24.842185 |
| Uncensored AD-Q4_K | 1454.322674 | 58.713510 | 36.685906 | 25.018935 |

`pp512` measures 512-token prompt processing. `tg128` measures 128-token generation. The separate depth benchmarks start with synthetic context already present. Context-load checks allocate a configured window and request a short response; they do not score recall over that window. `K` means 1,024 tokens.

## Contents

| File | Purpose |
|---|---|
| [METHOD.md](METHOD.md) | Inputs, builds, machines, statistics and reproduction |
| [RESULTS.md](RESULTS.md) | All 12 measurement rows and 14 context attempts |
| [FAILURES.md](FAILURES.md) | Allocation failures, successful tuning and lost-host correction |
| [LIMITATIONS.md](LIMITATIONS.md) | Repetition, host, memory and quality limits |
| [COMMANDS.md](COMMANDS.md) / [run-index.json](run-index.json) | Expanded commands and 14 timing/behavior run records |
| [results.json](results.json) / [results.csv](results.csv) | Raw-derived measurement data and configuration |
| [models.json](models.json) / [systems.json](systems.json) | Artifact hashes and captured hardware/build records |
| [evidence-manifest.json](evidence-manifest.json) | Original and public content hashes for 274 compressed evidence files |
| [provenance.json](provenance.json) | Source/archive verification and provisional-run status |
| [CHARTS](CHARTS/) | Overview and decode-depth PNG/SVG graphics, renderer inputs and provenance |
| [VALIDATION.md](VALIDATION.md) | Package verification record |
| [dspark-3090/](dspark-3090/) | 2026-11-24 DSpark drafter update: method, 336 requests, logs, telemetry and validator |

## Findings

Both files placed their expert tensors in CUDA0. The base file includes 40 NVFP4 expert matrices. This llama.cpp build uses its CUDA Q8 MMQ path on Ampere when native Blackwell FP4 MMA is unavailable; the 3090 does not execute native Blackwell FP4 instructions.

Both artifacts failed default b2048/ub512 allocation checks at 128K F16 and 256K F16/Q8/FP8. Both passed 128K F16 with b256/ub128. At 256K Q8, b256/ub128 still failed; b64/ub32 passed. All 14 attempts remain available: ten allocation failures and four successful short-generation checks.

![Decode with synthetic context already present. Cache, batch and host changes are stated on the figure.](CHARTS/decode-depth.png)

The initial 128K-depth attempts produced no measurement. A subsequent supplemental host disappeared before its raw tree could be transferred. Its surviving summaries are provisional and are not selected results. The four verified deep rerun measurements replace them.

One explicit refusal prompt was captured for each file. The base refused and the uncensored file supplied a procedural response. This is a single behavioral observation, not a refusal-rate or quality benchmark. No scored accuracy, perplexity, vision or long-context retrieval evaluation is reported.

## Verify the package

From this study directory, without loading a model or accessing the network:

```sh
python3 scripts/validate.py
python3 scripts/rebuild_measurements.py --check
python3 scripts/summarize.py --check
shasum -a 256 -c SHA256SUMS
```

The checks match every numerical row to its raw JSON, rebuild the JSON/CSV measurement tables, check commands and configuration, and verify the evidence hashes. To inspect a log:

```sh
gzip -dc evidence/rtx3090/base_bench_pp512_tg128.stdout.log.gz
```

[Reproduction instructions](METHOD.md) use the exact GGUF hashes and pinned build. No script provisions a remote machine. Model weights, runtime binaries, environments, authentication and operational administration are not redistributed. Captured paths are normalized to `/study`; private identifiers are removed. Flags, numerical measurements, timestamps and error/output text remain unchanged, with original and public hashes recorded separately.

MAJOR//minor designed the tests; AI agents operated the runs and assembled the evidence. Code follows the repository's MIT license; results/data follow CC BY 4.0. Consult the upstream model cards and artifact licenses for Unsloth and AtomicChat. Bundled fonts retain their included OFL notices.
