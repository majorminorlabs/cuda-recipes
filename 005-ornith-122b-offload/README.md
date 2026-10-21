# Ornith-1.5-122B on one RTX 3090

**TL;DR:** At 32K context, Q4_K_XL reached 548.03 tok/s prefill and 15.4985 tok/s decode. Q3_K_XL reached 311.307 tok/s prefill and 26.2562 tok/s decode. Both base quant runs scored 18/20. PPL was 5.7746 for Q4 and 5.8312 for Q3, against the AtomicChat BF16 reference of 5.7625.

Rented 1x RTX 3090 24GB + 32 vCPU AMD EPYC 7763, 125 GB RAM on RunPod Secure Cloud (EU-CZ-1) at $0.53/hr. Total $1.53 over 2.88 hours.

## Reader recipe card

| GPU and host RAM | Quant | CPU MoE layers | Threads | Context | Measured 32K decode |
| --- | --- | ---: | ---: | ---: | ---: |
| 24 GB GPU + 64 GB RAM | Q3_K_XL | 36 | 16 | 32K | 26.2562 tok/s |
| 24 GB GPU + 128 GB RAM | Q4_K_XL | 38 | 16 | 32K | 15.4985 tok/s |

The Q3 PPL run peaked at 55.82 GiB process RSS. This recipe was not verified on a 64 GB host; the benchmark pod had 125 GB allocated.

## Setup

- Ornith model: `ornith-ai/Ornith-1.5-122B`, MIT license.
- Unsloth GGUF quants: revision `3842d003341507c216295c6f28dfcd30349925c6`; all six shard SHA256 checks passed.
- llama.cpp: tag `b11757`, commit `13786fbb3a1aaf4ff445c0b92d9f21cbe0af6d42`.
- AtomicChat eval set revision: `933ce4826d0fe764a5cd6674bc9e0af5f5e985b1`.

| GGUF shard | SHA256 |
| --- | --- |
| Q3_K_XL-00001-of-00003 | `d8a23c487741fdac7026e10013fa8e320502cf01048a2333b2db8ba2a9f74fe5` |
| Q3_K_XL-00002-of-00003 | `95f76e67ffc49e2b0b4a4dfe5c42269b4b275ecf9e3696f599f3eeac92180323` |
| Q3_K_XL-00003-of-00003 | `1c4b52bbb1d45a21b5b7927429a5c80f264c688f2d14ed50ba0b6da0260d4028` |
| Q4_K_XL-00001-of-00003 | `7159d31a6a6ce5528500b490880383844c3c9b21fcdaad94e66c9e65233ff359` |
| Q4_K_XL-00002-of-00003 | `e66952128394bb4c75554c7e10a12a8b63dd1c7f049d876a02885a946e30c1c3` |
| Q4_K_XL-00003-of-00003 | `21325ec18a9e3210eeffada0fc327a25a79171918f1d04f8f0a06b61866ac9ba` |

## Copy-paste serving commands

Use the first GGUF shard as `M4` or `M3`. `--load-mode none` is the b11757 server equivalent used for the recipe's non-mmap load; this build does not accept `--no-mmap`.

**24 GB GPU + 64 GB RAM, Q3:**

```bash
M3=/workspace/models/UD-Q3_K_XL/Ornith-1.5-122B-UD-Q3_K_XL-00001-of-00003.gguf
/workspace/llama.cpp/build/bin/llama-server -m "$M3" -ngl 99 --n-cpu-moe 36 -c 32768 -fa on -t 16 --load-mode none --port 18082
```

**24 GB GPU + 128 GB RAM, Q4:**

```bash
M4=/workspace/models/UD-Q4_K_XL/Ornith-1.5-122B-UD-Q4_K_XL-00001-of-00003.gguf
/workspace/llama.cpp/build/bin/llama-server -m "$M4" -ngl 99 --n-cpu-moe 38 -c 32768 -fa on -t 16 --load-mode none --port 8080
```

For Q4 perplexity, use the same offload and thread settings with `llama-perplexity -m "$M4" -f eval_neutral.txt -c 4096 --chunks 87 -ngl 99 --n-cpu-moe 38 -t 16 -fa on`. The successful invocation used the default model-loading mode. Adding `-lm none` caused a CUDA allocation failure.

## Results

| Quant | 32K prefill | 32K decode | PPL | Tasks |
| --- | ---: | ---: | ---: | ---: |
| Q4_K_XL | 548.03 tok/s | 15.4985 tok/s | 5.7746 ± 0.03590 | 18/20 |
| Q3_K_XL | 311.307 tok/s | 26.2562 tok/s | 5.8312 ± 0.03628 | 18/20 |

Full sweeps, repetitions, resource peaks, task failures, and MTP counts are in [RESULTS.md](RESULTS.md).

The [illustrated article](https://majorminor.xyz/research/cuda-recipes-005) explains CPU expert offload and charts quality, context behavior, and the thread-count cliff. [Download the main PNG](https://majorminor.xyz/social/research/cuda-recipes-005.png).

## Caveats

- Step 8's Q3 offload sweep, repeating step 4 at `ncmoe=32`, crashed `llama-bench` during CUDA workspace allocation at 15:27:59 CDT; no published performance or resource measurement uses that run.
- Shared-host throughput varies. Q4 `ncmoe=49` prefill was 218.96 ± 1.73 tok/s in the first-pass table and 599.070–620.820 tok/s in the JSONL rerun (median 617.903); settings match and the cause was not investigated. Details are in `logs/notes.md`.
- The container reported `nproc=256`, while the cgroup quota was 31.13 CPU-equivalents and the RunPod allocation was 32 vCPU. With no explicit thread flag, llama.cpp selected 128 threads. In the measured thread runs, default prefill/decode were 446.692/2.5153 tok/s; explicit 32-thread prefill/decode were 763.216/15.8854 tok/s.
- Q4 at 128K was a single repetition after the B=38 setting OOMed; B=40 completed. The Q4 sweep also OOMed at `ncmoe=35`.
- MTP worked at `ncmoe=42`, but drafted 144 tokens and accepted 30; its task-run median decode was 10.859 tok/s.
- Quality evidence is PPL comparison plus the 20-item exact-match task set. The EPYC host measured 48,773.25 MiB/s memory bandwidth; consumer desktop RAM may be slower.

## Credits

Ornith for the `ornith-ai/Ornith-1.5-122B` model under MIT. Unsloth for the GGUF quants and repository revision above. llama.cpp for inference, tag, and commit above. AtomicChat for the BF16 reference PPL, `calib-corpora` eval set (`ornith-1.5-moe` recipe), tested llama.cpp build tip b11736, and `--spec-type draft-mtp` flag.
