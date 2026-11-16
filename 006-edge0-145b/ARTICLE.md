# Edge0-145B on one RTX 3090: 48.6 tok/s, if you bring the RAM

*Edge0-145B Q3_K reached 48.6 tok/s on one RTX 3090. The engine peaked at 43.4 GiB RSS and timed trials peaked at 87.4 GiB cgroup RAM.*

CUDA Recipes 006 · 2026-11-16 · [Site article](https://majorminor.xyz/research/cuda-recipes-006)

Edge0 publishes speed numbers for its 145B model on a 5090 D and a 4090, both 24GB cards. Lots of people have a 3090 instead, and Edge0's published table doesn't include one. So I ran Edge0's own stack on a 3090, stock, with the defaults its wrapper picks.

Short answer: it works and it's fast. A month ago, in [CUDA Recipes 005](https://majorminor.xyz/research/cuda-recipes-005), a 122B MoE on llama.cpp decoded at 15.5 tok/s on the same kind of card. That isn't a fair comparison (different model, engine, prompt length and machine), but it gives you a sense of the scale.

![Edge0-145B Q3_K on one RTX 3090. Median chat decode 48.6 tok/s, peak VRAM 23,929 MiB, and peak timed-trial cgroup RAM 87.4 GiB.](https://majorminor.xyz/social/research/cuda-recipes-006.png)

## TL;DR

- **Decode is 48.6 tok/s for chat and 52.8 tok/s on an agent prompt.** Median of three runs each, concurrency one, speculative decoding on (the wrapper's default).
- **Prefill is 1,195.5 tok/s at 4K and 1,481.2 tok/s at 16K.**
- **The 3090 runs at 47% to 70% of Edge0's published 4090 numbers**, depending on the workload. Prompts and machines differ, so read that as a ballpark.
- **VRAM is full.** Peak 23,929 MiB of 24,576 MiB.
- **Plan for more RAM than the model card suggests.** The engine process peaked at 43.4 GiB resident. Edge0's own residency figure is 31.28 GiB, measured on a 5090 D with a different setup. I didn't test a smaller RAM cap, so I can't tell you the minimum.
- **The agent run is a speed number only.** All three agent runs emitted a tool call. One of the three was valid.

| Workload | Run 1 | Run 2 | Run 3 | Median tok/s |
| --- | ---: | ---: | ---: | ---: |
| 4K prefill | 1,119.8 | 1,195.5 | 1,207.6 | **1,195.5** |
| 16K prefill | 1,467.6 | 1,485.6 | 1,481.2 | **1,481.2** |
| Chat decode | 46.6 | 49.6 | 48.6 | **48.6** |
| Agent decode | 52.8 | 55.9 | 50.7 | **52.8** |

## What Edge0-145B is

Edge0-145B is a latent mixture-of-experts model derived from Qwen3.8-Flash-Next. It has 145B total parameters and 48 layers. Each layer selects 10 of 512 routed experts per token and also runs a shared expert. The experts read a compressed 1,792-dimension input instead of the full 2,560, which is the "latent" part. It also carries a per-layer n-gram embedding (PLE) table and one MTP layer for speculative decoding.

It runs on edge0-strata, a fork of Niko1221's [Strata](https://github.com/Niko1221/Strata) that schedules CPU, GPU and PCIe work for these models. `edge0-infer serve` starts it for you. It isn't a llama.cpp model, so none of the `--n-cpu-moe` tuning from 004 and 005 applies. The engine decides what lives where.

The Q3_K snapshot is 106 GB on disk across 94 files. The single biggest file is the 51 GB FP8 PLE table, which the engine reads directly from disk rather than loading into VRAM.

Weights are open under the Edge0 Community Model License 1.0, which includes Qwen's license notice. It's open weights, so check the license before you use it commercially.

## Setup

One RTX 3090 24GB, an AMD EPYC 7H12 with a 31.13-CPU quota, a 116.4 GiB RAM limit and 160 GB of storage.

- **Engine:** Edge0 `v0.2.0` at `3203c39`, Strata built Release with CUDA for sm_86. Its llama.cpp dependency is pinned to `3cf0325`.
- **Model:** [Edge0/Edge0-145B-q3k](https://huggingface.co/Edge0/Edge0-145B-q3k/tree/a19f88cc07d78047c273cdb88f3250f36c143999) at revision `a19f88c`. All 13 upstream LFS SHA-256 hashes matched.
- **Runtime:** CUDA 13.0 toolkit, driver 595.91.07, PyTorch 2.9.1+cu130.

The launch command is the stock one:

```bash
edge0-infer serve --model /workspace/models/Edge0-145B-q3k --device cuda:0
```

The wrapper resolved that to direct PLE I/O, automatic expert cache and prefill, speculative decoding with 4 draft tokens, a 131,072-token max context and an int8 KV cache. I didn't change any of it.

## How I measured

Edge0's own `edge0-infer bench` rejects this model at v0.2.0, so a small script sends streaming requests to the local OpenAI-compatible endpoint and records the engine's `timings` object. Prefill is the engine's `prompt_per_second`, and decode is `predicted_per_second`. I didn't recompute either.

- Four fixed request files: a 4K prompt and a 16K prompt (`max_tokens=1`), an 88-token chat prompt asking for an 800-word explanation, and a 594-token agent prompt with tools. Decode runs used `max_tokens=512`.
- Each timed run started a fresh server, so no prompt cache carried over. The engine reported zero cached tokens on every run.
- `temperature=0`, `top_p=1`, `top_k=20`, reasoning on with `reasoning_budget_tokens=128`.
- GPU memory was sampled every 5 seconds, and the engine's RSS every second, read from the actual `strata` process rather than the Python wrapper.

The reasoning budget matters. My first smoke request had no budget, and the model spent all 512 tokens thinking without producing a visible answer. A 128-token budget fixed that. Both smoke requests are excluded from the timed results.

## Result 1: speed

Chat decode was 48.6 tok/s, and the three runs sat between 46.6 and 49.6. The agent prompt decoded a bit faster at 52.8 tok/s on this workload.

Prefill went up with prompt length, from 1,195.5 tok/s at 4K to 1,481.2 tok/s at 16K. Edge0's own table shows the same pattern.

The server took 25 seconds to come up in most runs (median 25.5 s). The slowest start was 94 s, and the very first, cold one was 51 s. That time isn't included in any rate.

![Three-trial RTX 3090 medians and min–max ranges for 4K and 16K prefill and chat and agent decode. Edge0’s independently reported RTX 4090 figures are marked separately.](https://majorminor.xyz/research/cuda-recipes-006/charts/throughput.png)

## Result 2: against Edge0's published numbers

[Edge0's release documentation](https://github.com/Edge0-AI/Edge0/blob/v0.2.0/docs/models/edge0-145b.md#speed-measured-one-card) reports one-card numbers for the Q3_K build. Here are the 4090's next to the 3090's:

| Workload | Edge0's 4090 | This 3090 | 3090 as % of 4090 |
| --- | ---: | ---: | ---: |
| 4K prefill | 2,042.0 | 1,195.5 | 59% |
| 16K prefill | 3,179.4 | 1,481.2 | 47% |
| Chat decode | 69.9 | 48.6 | 70% |
| Agent decode | 91.7 | 52.8 | 58% |

The 4090 figures are Edge0's claims. I didn't reproduce them. I used an 800-word writing prompt for chat and a single synthetic tool-call prompt for the agent run. I couldn't verify Edge0's exact request settings or host configuration for the published figures.

## Result 3: memory

| What | Peak |
| --- | ---: |
| GPU memory (timed runs) | 23,929 MiB of 24,576 MiB |
| Strata engine RSS (`VmHWM`) | 43.4 GiB |
| Pod cgroup usage, timed runs | 87.4 GiB |
| Pod cgroup usage, setup | 116.4 GiB (at the limit, no OOM kill) |

![Peak engine RSS was 43.4 GiB, pod cgroup RAM reached 87.4 GiB in timed trials and 116.4 GiB in setup, and the GPU used 23,929 of 24,576 MiB.](https://majorminor.xyz/research/cuda-recipes-006/charts/memory.png)

The engine's resident memory peaked at 43.4 GiB. I didn't measure the minimum host RAM required to run this configuration.

The cgroup numbers are much bigger because they count page cache too, and with a 51 GB PLE table read from disk plus a 106 GB download, a lot of that RAM was probably file cache. The 116.4 GiB setup peak hit right at the limit. `memory.events` recorded zero OOMs and zero OOM kills, which is consistent with the kernel reclaiming cache rather than the engine needing that much.

Edge0's model page says the 145B Q3_K holds as 23.14 GiB VRAM plus 31.28 GiB RAM with residency on, on a 5090 D. It lists a minimum of 16 GiB VRAM and 20 GiB RAM, at much lower speeds. My 43.4 GiB is with the wrapper's automatic defaults on a machine with plenty of RAM, so the engine may simply have taken what was available. I planned a 32 GiB cap test and didn't get to it. The pod had a 116.4 GiB cgroup limit.

## Result 4: the agent run

All three agent runs ended with a tool call, but only one of the three was valid:

- Run 1 called the right tool with its arguments wrapped wrong.
- Run 2 made a valid `submit_patch` call.
- Run 3 called `read_file`, which wasn't in the tool list.

This was at `temperature=0`, with the same prompt every time, and the three runs generated 265, 391 and 180 tokens. I didn't isolate what caused the variation. The 52.8 tok/s is generation speed only. This doesn't score whether the model is a good agent.

## What this doesn't tell you

- **Quality.** I didn't run any quality benchmark. Edge0 publishes its own scores, and I didn't check them.
- **The real RAM floor.** No capped-RAM run. See Result 3.
- **Your disk.** The workspace was a network-backed FUSE mount, and the drive type underneath wasn't visible. With the PLE table read from disk, local NVMe could behave differently, and I don't know in which direction for a warm cache.
- **Long context.** The largest prompt was 16K. The server allows 131K.
- **Other engines.** I planned a llama.cpp run of Qwen3.8-27B on the same prompts as a baseline, plus a Hermes tool-call test. Neither ran.
- **One machine, one session.** Three runs per workload.

## Cost

| Run | Time and rate | Cost |
| --- | --- | ---: |
| RTX 3090, compute host | 3 h 9 min at a quoted $0.50/hr | $1.0930 GPU + $0.0963 disk |
| **Total billed** | compute host billing API | **$1.1893** |

That covers the build, the 106 GB download, smoke runs, timed trials, and evidence transfer while the pod was allocated. See the [cost record](https://github.com/majorminorlabs/cuda-recipes/blob/main/006-edge0-145b/cost.md) for the billing breakdown.

## Data and reproducibility

The [study repository](https://github.com/majorminorlabs/cuda-recipes/tree/main/006-edge0-145b) has:

- `results/edge0-145b-3090.md`: trial results, settings, and recorded errors
- `results/prompts/`: the four request files, their hashes, and source provenance
- `scripts/`: the trial recorder
- `receipts/`: per-trial timing and token records, memory summaries, and the tool-call review

Raw SSE streams, server logs, telemetry and receipts are in my local archive, and checksums for all of it are recorded. The model weights aren't redistributed.

| Artifact | Pin |
| --- | --- |
| Model | `Edge0/Edge0-145B-q3k` @ `a19f88cc07d78047c273cdb88f3250f36c143999` |
| Edge0 | `v0.2.0` @ `3203c39809586d6629280706dde6b9c59809ad29` |
| llama.cpp (via Strata) | `3cf03257f219afbe7334045ff7c6a06ac68c627d` |

I design the tests, AI agents run them and draft the write-ups, and I check the numbers against the raw logs.

If you run this on a 3090, send me your numbers along with your RAM size and disk. A capped-RAM run is the one I most want to see.

## Credits

Thanks to Edge0 for the weights and the serving stack, and to Niko1221 and the Strata contributors for the engine it's built on.
