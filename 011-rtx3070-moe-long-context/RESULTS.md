# RTX 3070 long-context MoE results

## Qwen / Edge0 long-context speed and fit

| Engine / cap | Context / input tokens | Prefill tok/s | Decode tok/s (100 timed tokens) | TTFT | Peak RAM | Peak VRAM | Cap result |
|---|---:|---:|---:|---:|---:|---:|---|
| Edge0 / 8 GiB | 64K / attempted | — | — | — | 8.19 GiB job peak | — | No successful run; observed peak exceeded 8 GiB |
| Edge0 / 16 GiB | 64K / 64,290 | 532.57 | 20.74 | 120.717 s | 8.78 GiB | 7.29 GiB dedicated Vulkan | Held |
| Edge0 / 8 GiB | 128K / attempted | — | — | — | 8.01 GiB job peak | — | No successful run; exceeded configured cap slightly |
| Edge0 / 16 GiB | 128K / attempted | — | — | — | 7.92 GiB job peak | — | Cap held; context failed |
| Magnitude / 8 GiB | 64K / 64,288 | 202.60 | 3.27 | 317.316 s | 8.00 GiB cgroup peak (8 GiB limit) | 7,495 MiB | Held; no OOM/kill event |
| Magnitude / 8 GiB | 128K / 126,905 | 208.31 | 2.83 | 609.209 s | 8.00 GiB cgroup peak (8 GiB limit) | 7,495 MiB | Held; timed 100-token request succeeded |
| Magnitude / 16 GiB | 64K / 64,288 | 543.37 | 2.80 | 118.313 s | 14.75 GiB sampled Docker peak | 7,816 MiB | Held; cgroup peak 15.57 GiB, no OOM/kill |
| Magnitude / 16 GiB | 128K / 126,905 | 705.94 | 3.09 | 179.767 s | 15.08 GiB sampled Docker peak | 7,816 MiB | Held; cgroup peak 15.57 GiB, no OOM/kill |
| llama.cpp / uncapped | 64K / approximately 64.3K | 414.1 | 14.9 | approximately 155 s | 20.11 GiB cgroup peak | 4,193 MiB | No Docker cap; below ~23 GiB WSL ceiling; no OOM |
| llama.cpp / uncapped | 128K / 126,895 | 388.7 | 8.0 | approximately 326 s | 20.06 GiB cgroup peak | 5,537 MiB | No Docker cap; below ~23 GiB WSL ceiling; no OOM |

TTFT is prompt-phase time; llama.cpp TTFT is estimated from rounded prompt throughput. Magnitude prompt cache reuse is possible between warmup and timed requests. Magnitude 8 GiB had a failed 128K warmup followed by a successful timed request. Edge0's 8 GiB failures slightly exceeded the configured Job Object cap. GPU figures are samples or a Vulkan ledger, not interchangeable physical peaks.

## Earlier empty / 8K / 32K results (reused, not rerun)

| Cap | Run | Input tokens | Prefill tok/s | Decode tok/s | Peak RAM | Cap held |
|---|---|---:|---:|---:|---:|---|
| 8 GiB | empty | 26 | 25.21 | 21.18 | 5.620 GiB | Yes |
| 8 GiB | 8K | 8,023 | 283.90 | 20.46 | 6.504 GiB | Yes |
| 8 GiB | 32K | 32,023 | 670.47 | 20.15 | 7.588 GiB | Yes |
| 16 GiB | empty | 26 | 25.03 | 20.87 | 5.638 GiB | Yes (also under 8 GiB) |
| 16 GiB | 8K | 8,023 | 701.22 | 20.46 | 6.584 GiB | Yes |
| 16 GiB | 32K | 32,023 | 674.54 | 20.22 | 7.524 GiB | Yes |
| Uncapped | empty | 26 | 25.34 | 21.19 | n/a | n/a |

| Cap | Prefill tok/s (empty / 8K / 32K) | Decode tok/s (empty / 8K / 32K) | Peak RAM / VRAM | Cap held |
|---|---|---|---|---|
| 8 GiB | 1.33 / 179.22 / 417.09 | 3.75 / 3.07 / 2.39 | Docker stats about 7.09 / 8 GiB | Yes |
| 16 GiB | 1.42 / 482.95 / 1,209.97 | 5.28 / 8.41 / 3.74 | Docker stats 14.57 / 16 GiB; GPU sample 7,555 MiB | Yes |

| Metric | empty / 8K / 32K |
|---|---|
| Prefill tok/s | 65.66 / 312.71 / 301.62 |
| Decode tok/s | 15.91 / 16.96 / 15.28 |
| Peak cgroup RAM | 20.00 GiB prefill; 20.73 GiB decode |

Magnitude's earlier filler prompts shared prefixes; these prompt rates are not cold-prefill measurements. llama.cpp used synthetic token counts for these earlier benchmarks and CPU MoE offload without a Docker cap.

## Additional models

| Model / engine | Context / input tokens | Prefill tok/s | Decode tok/s | TTFT | Peak RAM | Peak VRAM | Cap result |
|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3.6-35B-A3B Q4_K_M (r4) / llama.cpp CUDA | 64K / ~64.3K | 414.1 | 14.9 | ~155 s | 20.11 GiB cgroup | 4,193 MiB | no Docker cap; WSL ceiling |
| Qwen3.6-35B-A3B Q4_K_M (r4) / llama.cpp CUDA | 128K / 126,895 | 388.7 | 8.0 | ~326 s | 20.06 GiB cgroup | 5,537 MiB | no Docker cap; WSL ceiling |
| Qwen3.6-35B-A3B Q4_K_M (r4) / Magnitude 0.3.4 | 64K / 64,288 | 202.60 | 3.27 | 317.316 s | 8.00 GiB cgroup | 7,495 MiB | 8 GiB applied; held |
| Qwen3.6-35B-A3B Q4_K_M (r4) / Magnitude 0.3.4 | 128K / 126,905 | 208.31 | 2.83 | 609.209 s | 8.00 GiB cgroup | 7,495 MiB | 8 GiB applied; held |
| Qwen3.6-35B-A3B Q4_K_M (r4) / Magnitude 0.3.4 | 64K / 64,288 | 543.37 | 2.80 | 118.313 s | 14.75 GiB sampled Docker (15.57 GiB cgroup) | 7,816 MiB | 16 GiB applied; held |
| Qwen3.6-35B-A3B Q4_K_M (r4) / Magnitude 0.3.4 | 128K / 126,905 | 705.94 | 3.09 | 179.767 s | 15.08 GiB sampled Docker (15.57 GiB cgroup) | 7,816 MiB | 16 GiB applied; held |
| Raon-1 mini Q4_K_M / llama.cpp r4 image | 64K / — | n/a | n/a | n/a | n/a | n/a | uncapped; architecture load failed |
| Raon-1 mini Q4_K_M / llama.cpp KRAFTON branch | 64K / 64,283 | 333.0 | 5.7 | ~193 s | 19.54 GiB cgroup | 3,962 MiB | no Docker cap; WSL ceiling |
| Raon-1 mini Q4_K_M / llama.cpp KRAFTON branch | 128K / 126,900 | 282.3 | 5.0 | ~449.5 s | 19.53 GiB cgroup | 4,528 MiB | no Docker cap; WSL ceiling |
| Raon-1 mini Q4_K_M / Magnitude 0.3.4, 8 GiB | 64K / — | n/a | n/a | n/a | n/a | n/a | cap configured/reported; model unsupported, inference cap unverified |
| Raon-1 mini Q4_K_M / Magnitude 0.3.4, 8 GiB | 128K / — | n/a | n/a | n/a | n/a | n/a | cap configured/reported; model unsupported, inference cap unverified |
| Raon-1 mini Q4_K_M / Magnitude 0.3.4, 16 GiB | 64K / — | n/a | n/a | n/a | n/a | n/a | cap configured/reported; model unsupported, inference cap unverified |
| Raon-1 mini Q4_K_M / Magnitude 0.3.4, 16 GiB | 128K / — | n/a | n/a | n/a | n/a | n/a | cap configured/reported; model unsupported, inference cap unverified |
| Qwen3.8-Flash-Next IQ4_NL / llama.cpp r4 image | 64K / 64,159 | n/a | n/a | n/a | 22.77 GiB cgroup peak | 7,484 MiB | no Docker cap; still running at 60m48s, stopped; no output |
| Qwen3.8-Flash-Next IQ4_NL / llama.cpp r4 image | 128K / 126,457 | n/a | n/a | n/a | n/a | n/a | not attempted; 64K run did not complete within 1 hour |
| Qwen3.8-Flash-Next IQ4_NL / Magnitude 0.3.4, 8 GiB | 64K / — | n/a | n/a | n/a | n/a | n/a | 8 GiB applied/reported; file unreadable before inference |
| Qwen3.8-Flash-Next IQ4_NL / Magnitude 0.3.4, 8 GiB | 128K / — | n/a | n/a | n/a | n/a | n/a | 8 GiB applied/reported; file unreadable before inference |
| Qwen3.8-Flash-Next IQ4_NL / Magnitude 0.3.4, 16 GiB | 64K / — | n/a | n/a | n/a | n/a | n/a | 16 GiB applied/reported; file unreadable before inference |
| Qwen3.8-Flash-Next IQ4_NL / Magnitude 0.3.4, 16 GiB | 128K / — | n/a | n/a | n/a | n/a | n/a | 16 GiB applied/reported; file unreadable before inference |

Flash Next 64K was explicitly stopped at 60m48s with no output and OOMKilled=false. Exit 137 followed that stop and is not evidence of OOM. Its 128K and quality runs were not attempted. Magnitude load failures occurred before inference, so configured caps do not establish inference cap holding.

## Fixed 60-item quality set

| Model / path | Coding /15 | Math /20 | Instruction /23 | Retrieval /2 | Total /60 | Formatting-only misses |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B Q4_K_M, r4 llama.cpp | 8 | 12 | 15 | 2 | **37** | r4 reference |
| Raon-1 mini Q4_K_M, KRAFTON llama.cpp branch | 4 | 12 | 18 | 2 | **36** | 0 |
| Edge0-35B-A3B-preview, r4 reference only | 2 | 8 | 5 | 1 | **16** | r4 reference |
| Qwen3.8-Flash-Next, r4 llama.cpp image | n/a | n/a | n/a | n/a | n/a | not run: 64K benchmark timed out after 60m48s without output |

This is one substitute 60-item set, not the separate 120-trial suite. Same prompt text, order and scorer were used. Edge0 ran at 65,536 server context after 131,072 allocation failure, so its 128K retrieval failure is a capacity rejection. Raon retrieval prompts were 51,301 and 100,951 tokens with its tokenizer. Quality was not tested in Magnitude.

## Later stock Raon load probe

Upstream llama.cpp 1.1.0-dev, build 12767, commit a8ad690ca, failed to load the official Raon Q4_K_M file: expected 736 tensors, got 731. No speed or quality measurements exist for this pairing. The working Raon path remains the separately identified KRAFTON branch.
