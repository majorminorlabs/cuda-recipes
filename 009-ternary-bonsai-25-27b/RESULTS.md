# Results

## Frozen task suite

| Model and arm | Strict success | Coding | Terminal/system | Tool use | Structured data | Multi-step | Mean latency (s) | Median (s) | p95 linear (s) | Mean prompt tok/s | Mean decode tok/s | Peak VRAM (MiB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8 27B Q4_K_M (001, reused) | 89/120 | 23/36 | 17/24 | 24/24 | 14/18 | 11/18 | 8.57526173790296 | 5.372757792472839 | 24.605969512462604 | 963.3555294300377 | 41.48433297875077 | 16481 |
| Bonsai PTQ1 plain | 81/120 | 22/36 | 16/24 | 21/24 | 13/18 | 9/18 | 5.554141666491827 | 3.632115602493286 | 18.515960907936087 | 1041.138952142074 | 91.5935723425421 | 6803 |
| Bonsai PTQ1 MTP quality arm | 79/120 | 21/36 | 15/24 | 21/24 | 13/18 | 9/18 | 4.181418077150981 | 2.792686104774475 | 12.946645081043238 | 996.2050251390168 | 147.92285683543938 | 7611 |

The suite's decode rates use Q8_0 KV and are not the F16 `llama-bench` speed rows below.

## Fresh `llama-bench` speed

| Build | Model | pp512 (tok/s) | tg128 (tok/s) | Peak VRAM sampled (MiB) |
|---|---|---:|---:|---:|
| Prism | Qwen Q4_K_M | 1450.894043 | 45.972666 | 16118 |
| Prism | Bonsai PTQ1 plain | 1555.076856 | 94.536232 | 6490 |
| Prism | Bonsai PTQ1 MTP-head file, drafting off | 1551.010481 | 94.025183 | 6490 |
| Stock | Qwen Q4_K_M | 1538.036981 | 43.753292 | 16120 |
| Stock | Bonsai Q2_0 | 1591.263528 | 69.583099 | 8018 |

## Fixed-prompt MTP server comparison

| Drafting | Generation tok/s | Prompt tok/s | Generated tokens | Prompt tokens | Draft tokens | Accepted drafts | Peak VRAM (MiB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Off | 92.92596269119396 | 181.05846969006166 | 384 | 193 | n/a | n/a | 6558 |
| On, p_min 0.1 | 115.28064754265156 | 159.00202748181158 | 379 | 193 | 506 | 206 | 7330 |

The CUDA default p_min 0.1 and p_min 0 both engaged drafts in the cutoff check. Their measured generation rates were 117.2032037603983 and 112.16887245718495 tok/s respectively; p_min 0.1 was used for the quality MTP arm.

## Filled-context decode

| Model | Depth | KV | Batch/ubatch | Decode tok/s | Peak VRAM sampled (MiB) | Outcome |
|---|---:|---|---:|---:|---:|---|
| Bonsai PTQ1 plain | 32768 | F16 | 2048/512 | 76.433302 | 8546 | completed |
| Bonsai PTQ1 plain | 131072 | F16 | 256/128 | 48.640977 | 14298 | completed |
| Bonsai PTQ1 plain | 262144 | Q8_0 | 64/32 | 18.878428 | 14979 | completed |
| Bonsai MTP-head file, drafting off | 32768 | F16 | 2048/512 | 76.288086 | 8546 | completed |
| Bonsai MTP-head file, drafting off | 131072 | F16 | 256/128 | 48.770155 | 14298 | completed |
| Bonsai MTP-head file, drafting off | 262144 | Q8_0 | 64/32 | 18.779666 | 14979 | completed |
| Bonsai Q2_0 | 32768 | F16 | 2048/512 | 59.017119 | 10086 | completed |
| Bonsai Q2_0 | 131072 | F16 | 256/128 | 41.193981 | 15850 | completed |
| Bonsai Q2_0 | 262144 | Q8_0 | 64/32 | 17.918661 | 17537 | completed |
| Qwen Q4_K_M | 32768 | F16 | 2048/512 | 39.2678 | 18186 | completed |
| Qwen Q4_K_M | 131072 | F16 | 256/128 | 30.511771 | 23950 | completed |
| Qwen Q4_K_M | 262144 | Q8_0 | 64/32 | — | — | allocation failure |

The 001 suite's 41.48433297875077 tok/s Qwen decode rate is not used as the fresh speed comparator.
