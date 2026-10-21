# CUDA Recipes 005 results

## Summary

- Q4_K_XL best offload setting: `ncmoe=38`; Q4 thread sweep winner: `-t 16`. At depth 32K, median prefill was **548.03 tok/s** and median decode **15.4985 tok/s**.
- Q3_K_XL best tested offload setting: `ncmoe=36`, reusing `-t 16`. At depth 32K, median prefill was **311.307 tok/s** and median decode **26.2562 tok/s**.
- Each base task set scored **18/20**. Q4 MTP reached **18/20** at `ncmoe=42`; 30 of 144 draft tokens were accepted.
- PPL: Q4 **5.7746 ± 0.03590**, Q3 **5.8312 ± 0.03628**; AtomicChat BF16 reference **5.7625 ± 0.0358**. Q4 is 0.21% above reference; Q3 is 1.19% above.
- The Q4 32K measurement completed without a stop-rule failure.

## Throughput and memory

Rates are medians of the three recorded repetitions; ranges show min–max of those repetitions. Peak GPU memory is the largest sampled `memory.used` from the associated `vram_*.csv`; peak RAM is `/usr/bin/time -v` maximum RSS, converted to GiB. Q4 sweep/depth resource measurements cover the whole command, so the aggregate value is repeated for its rows. Smoke load time is the time to the first HTTP 200 from `/health`.

| Quant | ncmoe | -t | Depth | Prefill tok/s | Decode tok/s | Peak VRAM | Peak RAM | Load time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q4_K_XL | 49 | 32 | 0 | 617.903 (599.070–620.820) | 11.8796 (10.9892–12.8478) | 21,704 MiB* | 66.93 GiB* | 82.701 s |
| Q4_K_XL | 45 | 32 | 0 | 762.094 (755.004–763.480) | 16.8237 (16.3206–17.0044) | 21,704 MiB* | 66.93 GiB* | 82.701 s |
| Q4_K_XL | 41 | 32 | 0 | 779.363 (772.165–779.790) | 19.6394 (19.4849–19.8170) | 21,704 MiB* | 66.93 GiB* | 82.701 s |
| Q4_K_XL | **38** | 32 | 0 | 256.977 (256.647–258.339) | **21.6680 (21.0255–22.0377)** | 21,704 MiB* | 66.93 GiB* | 82.701 s |
| Q4_K_XL | 35 | 32 | 0 | OOM | OOM | — | — | — |
| Q4_K_XL | 38 | 16 | 0 | 455.235 (449.328–496.195) | 12.2471 (11.1148–12.4113) | 23,903 MiB† | 55.13 GiB† | 82.701 s |
| Q4_K_XL | 38 | 16 | 32K | 548.030 (547.493–550.564) | 15.4985 (15.3608–15.8124) | 23,903 MiB† | 55.13 GiB† | 82.701 s |
| Q4_K_XL | 38 | 16 | 64K | 567.675 (565.439–571.572) | 21.4526 (21.0915–21.5083) | 23,903 MiB† | 55.13 GiB† | 82.701 s |
| Q4_K_XL | 40‡ | 16 | 128K | 416.454 (single rep) | 21.2082 (single rep) | 22,562 MiB | 58.38 GiB | 82.701 s |
| Q3_K_XL | 49 | 16 | 0 | 283.915 (280.720–286.284) | 22.2045 (21.6679–22.7510) | 5,788 MiB | 49.35 GiB | 59.406 s |
| Q3_K_XL | 44 | 16 | 0 | 301.595 (298.023–304.099) | 23.4987 (23.3069–24.8590) | 10,670 MiB | 44.57 GiB | 59.406 s |
| Q3_K_XL | 40 | 16 | 0 | 318.248 (315.961–320.046) | 24.0917 (23.7170–24.8481) | 14,870 MiB | 40.45 GiB | 59.406 s |
| Q3_K_XL | **36** | 16 | 0 | 353.110 (350.159–353.647) | **26.8012 (25.7943–28.5356)** | 19,526 MiB | 35.90 GiB | 59.406 s |
| Q3_K_XL | 32 | 16 | 0 | OOM | OOM | — | — | — |
| Q3_K_XL | 36 | 16 | 0 | 353.329 (351.442–355.149) | 28.2118 (27.5079–28.9094) | 21,396 MiB§ | 38.55 GiB§ | 59.406 s |
| Q3_K_XL | 36 | 16 | 32K | 311.307 (311.031–311.817) | 26.2562 (26.0275–26.5084) | 21,396 MiB§ | 38.55 GiB§ | 59.406 s |
| Q3_K_XL | 36 | 16 | 64K | 293.737 (293.710–294.580) | 25.2679 (25.0101–26.2180) | 21,396 MiB§ | 38.55 GiB§ | 59.406 s |

`*` Aggregate for the Q4 offload sweep. `†` Aggregate for the Q4 0/32K/64K depth sweep. `‡` The 128K run at B=38 OOMed allocating a 1,130 MiB CUDA buffer; the prescribed B+2 retry at 40 completed, single repetition. `§` Aggregate for the Q3 depth sweep. The Q3 `ncmoe=32` run crashed during the step 8 offload sweep and is excluded from resource figures.

Throughput source logs: Q4 offload `logs/sweep_ncmoe_q4.jsonl`; Q4 depth `logs/depth_q4.jsonl`; 128K `logs/depth128k_q4_B40.jsonl`; Q3 offload `logs/sweep_ncmoe_q3_<ncmoe>.jsonl`; Q3 depth `logs/depth_q3.jsonl`. Resource sources use the corresponding `vram_*.csv` and `.time` files. Thread rows come from `logs/sweep_threads_q4.jsonl` and `logs/threads_default_q4.jsonl`.

The first-pass Q4 ncmoe=49 prefill value was **218.96 ± 1.73 tok/s**; the JSONL rerun recorded **599.070, 620.820, 617.903 tok/s** (median 617.903). Both sources record 32 threads, batch 2048/512, flash attention on, and non-mmap loading; the cause was not investigated. The full settings comparison is in `logs/notes.md`.

## Q4 thread sweep

| Threads | Prefill median (min–max) tok/s | Decode median (min–max) tok/s | Peak VRAM | Peak RAM |
| ---: | ---: | ---: | ---: | ---: |
| 8 | 771.512 (762.126–774.332) | 17.5979 (16.9254–19.3305) | 21,694 MiB* | 52.52 GiB* |
| **16 (TB)** | 762.433 (758.262–762.899) | **20.0165 (18.0469–22.1832)** | 21,694 MiB* | 52.52 GiB* |
| 24 | 757.786 (751.267–769.140) | 16.9203 (16.1668–17.9620) | 21,694 MiB* | 52.52 GiB* |
| 30 | 254.825 (254.514–256.209) | 18.4435 (18.3184–18.8967) | 21,694 MiB* | 52.52 GiB* |
| 32 | 763.216 (760.007–764.552) | 15.8854 (15.6665–16.3629) | 21,694 MiB* | 52.52 GiB* |
| Default (`n_threads=128`) | 446.692 (420.786–471.782) | 2.5153 (2.3478–2.7828) | 21,694 MiB† | 52.48 GiB† |

`*` Combined thread sweep. `†` Default-thread run. The container reported `nproc=256`; cgroup quota was 31.13 CPU-equivalents and T was set to the allocated 32. With no explicit `-t`, llama.cpp selected 128 threads. The default row is retained as the requested visible-CPU trap.

## Tasks, MTP, and quality

| Run | Configuration | Score | Median decode tok/s | Drafted | Accepted |
| --- | --- | ---: | ---: | ---: | ---: |
| Q4 base | ncmoe=38, t=16 | 18/20 | 17.9192 | — | — |
| Q4 MTP | ncmoe=42, t=16 | 18/20 | 10.8593 | 144 | 30 |
| Q3 base | ncmoe=36, t=16 | 18/20 | 19.0751 | — | — |

Q4 missed t06: expected `esuohthgil`, got `ethguohgil`; and t20: expected `150`, got `150 miles`. Q3 missed t06: expected `esuohthgil`, got `etuoohlhgil`; and t20: expected `150`, got `150 miles`. MTP was accepted by the server; ncmoe=38 and 40 attempts OOMed at the 32K context, and ncmoe=42 succeeded on port 18081.

| Quant | PPL | AtomicChat reference | Difference from reference |
| --- | ---: | ---: | ---: |
| Q4_K_XL | 5.7746 ± 0.03590 | 5.7625 ± 0.0358 | +0.21% |
| Q3_K_XL | 5.8312 ± 0.03628 | 5.7625 ± 0.0358 | +1.19% |

PPL used dataset revision `933ce4826d0fe764a5cd6674bc9e0af5f5e985b1`. The Q4 `-lm none` attempt OOMed at load; omitting that extra flag and using the command's default load mode completed all 87 chunks.

## Hardware and setup

Rented 1x RTX 3090 24GB + 32 vCPU AMD EPYC 7763, 125 GB RAM on RunPod Secure Cloud (EU-CZ-1) at $0.53/hr. Total $1.53 over 2.88 hours. `sysbench memory` measured **48,773.25 MiB/s** (1 MiB blocks, 64 GiB writes, 32 threads).

- llama.cpp: tag `b11757`, commit `13786fbb3a1aaf4ff445c0b92d9f21cbe0af6d42`.
- Unsloth GGUF revision: `3842d003341507c216295c6f28dfcd30349925c6`.
- Ornith model: `ornith-ai/Ornith-1.5-122B`, MIT license.
- AtomicChat supplied the BF16 reference PPL, the `calib-corpora` eval set (`ornith-1.5-moe` recipe), tested llama.cpp build tip b11736, and `--spec-type draft-mtp` flag.
- The six downloaded shards matched the expected SHA256 hashes; see `receipts/hash_check.txt`, `receipts/expected_sha256.txt`, and `receipts/actual_sha256.txt`.
- Full raw measurements and receipts are in `logs/` and `receipts/`.
