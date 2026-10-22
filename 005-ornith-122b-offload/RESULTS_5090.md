# CUDA Recipes 005: Ornith-1.5-122B on RTX 5090

## Summary

- Recommended Q4: `ncmoe=33`, `-t 14`, 32K context. Median prefill **562.714 (559.434–564.104) tok/s**, decode **30.416 (29.764–30.564) tok/s**.
- Recommended Q3: `ncmoe=27`, `-t 14`, 32K context. Median prefill **888.585 (883.382–892.345) tok/s**, decode **30.241 (29.114–30.695) tok/s**.
- Q4 and Q3 shards matched all six hashes in the 3090 run receipt. llama.cpp tag `b11757`, commit `13786fbb3a1aaf4ff445c0b92d9f21cbe0af6d42`, built for CUDA architecture 120.
- Peak RSS values below come from `/usr/bin/time -v`; peak VRAM is the maximum `memory.used` sampled every 500 ms. Throughput cells show median (min–max) over the recorded reps. The CUDA and RAM OOM types are reported separately.

## Smoke tests

| Quant | ncmoe | Result | Load to health-ready | Peak RSS | Peak VRAM |
| --- | ---: | --- | ---: | ---: | ---: |
| Q4_K_XL | 33 | 391 | 60.561 s | 45.80 GiB | 30036 MiB |
| Q3_K_XL | 36 | 391 | 42.704 s | 36.19 GiB | 20652 MiB |

Both smoke responses matched the expected answer `391`.

## Offload sweeps

### Q4_K_XL

| ncmoe | Prefill tok/s | Decode tok/s | Peak VRAM | Peak RSS | Outcome |
| ---: | ---: | ---: | ---: | ---: | --- |
| 35 | 593.694 (591.392–595.295) | 28.730 (27.202–29.310) | 26350 MiB | 48.32 GiB | none |
| 33 | 613.914 (611.256–615.679) | 32.610 (32.530–33.866) | 29128 MiB | 45.61 GiB | none |
| 31 | — | — | 31272 MiB | 42.14 GiB | CUDA OOM |
| 29 | — | — | — | — | Not run: stopped after CUDA OOM at ncmoe=31 |
| 27 | — | — | — | — | Not run: stopped after CUDA OOM at ncmoe=31 |
| 25 | — | — | — | — | Not run: stopped after CUDA OOM at ncmoe=31 |

### Q3_K_XL

| ncmoe | Prefill tok/s | Decode tok/s | Peak VRAM | Peak RSS | Outcome |
| ---: | ---: | ---: | ---: | ---: | --- |
| 36 | 770.929 (765.058–774.673) | 26.151 (25.831–27.345) | 19824 MiB | 36.01 GiB | none |
| 33 | 820.216 (815.676–822.464) | 28.024 (26.985–29.303) | 23262 MiB | 32.64 GiB | none |
| 31 | 865.608 (859.581–867.330) | 29.028 (28.872–29.454) | 25698 MiB | 30.25 GiB | none |
| 29 | 921.779 (918.623–923.966) | 30.080 (29.728–30.760) | 28144 MiB | 27.86 GiB | none |
| 27 | 989.172 (983.340–989.913) | 32.582 (31.145–33.226) | 30634 MiB | 25.42 GiB | none |
| 25 | — | — | 508 MiB | 0.42 GiB | CUDA OOM |
| 23 | — | — | — | — | Not run: stopped after CUDA OOM at ncmoe=25 |

## Q4 thread sweep

The no-`-t` row reports the `n_threads` value emitted by llama.cpp.

| Requested threads | llama.cpp threads | Prefill tok/s | Decode tok/s | Peak VRAM | Peak RSS | Outcome |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4 | 4 | 614.309 (611.280–616.000) | 14.926 (14.774–15.091) | 29128 MiB | 45.60 GiB | none |
| 8 | 8 | 612.815 (609.950–613.734) | 20.132 (19.753–20.481) | 29128 MiB | 45.60 GiB | none |
| 14 | 14 | 609.661 (605.309–612.287) | 29.691 (29.466–30.883) | 29128 MiB | 45.60 GiB | none |
| default | 64 | 609.259 (603.047–611.338) | 6.632 (5.743–6.806) | 29128 MiB | 45.60 GiB | none |

## Context depth

### Q4_K_XL at B4=33, TB=14

| Depth | Prefill tok/s | Decode tok/s | Peak VRAM | Peak RSS | Outcome |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 606.480 (603.200–612.249) | 28.679 (27.492–28.979) | 29128 MiB | 45.60 GiB | none |
| 32,768 | 562.714 (559.434–564.104) | 30.416 (29.764–30.564) | 30276 MiB | 46.54 GiB | none |
| 65,536 | 538.899 (534.166–539.513) | 25.991 (25.198–26.727) | 31076 MiB | 47.32 GiB | none |
| 131,072 | — | — | 28110 MiB | 45.23 GiB | CUDA OOM (B4=33 initial attempt) |
| 131,072 | 482.598 (482.598–482.598) | 28.192 (28.192–28.192) | 29898 MiB | 51.61 GiB | none (retry at ncmoe=35) |

### Q3_K_XL at B3=27, TB=14

| Depth | Prefill tok/s | Decode tok/s | Peak VRAM | Peak RSS | Outcome |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 987.079 (980.006–990.562) | 31.421 (31.408–32.035) | 30634 MiB | 25.42 GiB | none |
| 32,768 | 888.585 (883.382–892.345) | 30.241 (29.114–30.695) | 31721 MiB | 26.36 GiB | none |
| 65,536 | — | — | 29738 MiB | 25.02 GiB | CUDA OOM |

## Q4 32K variance

| Invocation | llama-bench test_time | Prefill tok/s | Decode tok/s | Peak VRAM | Peak RSS |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 (depth sweep) | 2026-10-22T01:58:29Z | 562.714 (559.434–564.104) | 30.416 (29.764–30.564) | 30276 MiB | 46.54 GiB |
| 2 | 2026-10-22T02:21:19Z | 564.035 (559.881–564.753) | 29.691 (28.446–31.897) | 30276 MiB | 46.54 GiB |
| 3 | 2026-10-22T02:33:54Z | 562.799 (559.225–563.999) | 28.166 (24.507–29.513) | 30276 MiB | 46.54 GiB |

## Task sanity scores

| Label | Score | Median task decode tok/s |
| --- | ---: | ---: |
| 5090_q4 | 18/20 | 25.071 |
| 5090_q3 | 18/20 | 24.943 |

## Head-to-head at 32K

| Quant | GPU | ncmoe | Threads | Prefill tok/s | Decode tok/s | Peak RSS |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Q4_K_XL | RTX 3090 | 38 | 16 | 548.030 | 15.4985 | 55.13 GiB |
| Q4_K_XL | RTX 5090 | 33 | 14 | 562.714 (559.434–564.104) | 30.416 (29.764–30.564) | 46.54 GiB |
| Q3_K_XL | RTX 3090 | 36 | 16 | 311.307 | 26.2562 | 38.55 GiB |
| Q3_K_XL | RTX 5090 | 27 | 14 | 888.585 (883.382–892.345) | 30.241 (29.114–30.695) | 26.36 GiB |

## 64 GB-class RAM result and OOMs

Verified on a 60 GB-class RAM pod with a **57.74 GiB cgroup RAM limit** (memory.max=61999996928 bytes): Q4 at ncmoe=33 peaked at **50.40 GiB** in the 32K server task run; Q3 at ncmoe=27 peaked at **30.23 GiB**. The supporting 32K benchmark process peaks were Q4 46.54 GiB and Q3 26.36 GiB.

- Q4 RAM OOM kills: none recorded.
- Q4 CUDA OOM: offload sweep `ncmoe=31`; 128K at `ncmoe=33` failed CUDA allocation and the retry at `ncmoe=35` completed.
- Q3 RAM OOM kills: none recorded.
- Q3 CUDA OOM: offload sweep `ncmoe=25` (so `23` was not run); depth 65,536 at `ncmoe=27`.

## Run notes

- The first Q4 smoke attempts exited before llama-server started because GNU `/usr/bin/time` was missing in the container. After installing the `time` package, the measured smoke passed with `391`; no inference was performed during the prelaunch failures.
- Q4 at `ncmoe=33`, `-t 14`, depth 0 showed throughput spread across the offload, thread, and depth invocations; the raw measurements are retained and the cause was not investigated.
- Initial build configuration needed the explicit CUDA 12.8 `nvcc` path; the pinned build completed. The initial Hugging Face CLI install was retried with the container's externally-managed Python override.

## Recipe card: 32 GB GPU + 64 GB RAM class

| Quant | Exact serving command | Measured server peak RSS |
| --- | --- | ---: |
| Q4_K_XL | `/workspace/llama.cpp/build/bin/llama-server -m /workspace/models/UD-Q4_K_XL/Ornith-1.5-122B-UD-Q4_K_XL-00001-of-00003.gguf -ngl 99 --n-cpu-moe 33 -c 32768 -fa on -t 14 --load-mode none --port 18084` | 50.40 GiB |
| Q3_K_XL | `/workspace/llama.cpp/build/bin/llama-server -m /workspace/models/UD-Q3_K_XL/Ornith-1.5-122B-UD-Q3_K_XL-00001-of-00003.gguf -ngl 99 --n-cpu-moe 27 -c 32768 -fa on -t 14 --load-mode none --port 18085` | 30.23 GiB |

## Hardware and cost

Rented 1x RTX 5090 32GB + 16 vCPU (Intel(R) Xeon(R) Gold 6530), 62 GB RAM on RunPod Secure Cloud (US) at $1.22/hr. RunPod displayed total rate: $1.22/hr ($1.19/hr compute + $0.028/hr container storage, rounded as displayed).

The user-provided Details screenshot showed 43m38s uptime at 9:14 PM local, which is 02:14 UTC on 2026-10-22. The data pull ended at 02:50:28Z. Using the minute-resolution screenshot clock, estimated pod uptime at pull was approximately 1.34 hours (about 1.33–1.35 hours), for an estimated total of approximately $1.64 (about $1.63–$1.65 at the displayed rate).

This is an estimate because the screenshot clock has only minute precision and no exact RunPod creation/billing timestamp was available. The local measurement window from receipts/5090/start_time.txt to end_time.txt was 1h17m14s (1.29 hours); it excludes the pod uptime already accumulated when the screenshot was captured.

RunPod reported 16 vCPU; `cpu.max` constrained this container to 13.6 CPU-equivalents, so `T=14` was used. The measured cgroup RAM limit was 57.74 GiB (memory.max=61999996928 bytes).

Raw per-command logs and receipts are in `logs/5090/` and `receipts/5090/`.
