# Ornith-1.5-122B runs on one 24GB RTX 3090. Here's what it costs in speed.

*With the MoE experts in system RAM, the Q4 quant decodes at roughly 12 to 22 tok/s and reads a 32K prompt at about 550 tok/s on a single 3090. Q3 is faster to talk to and slower to read. Leave llama.cpp's thread count on its default in a container and decode falls to 2.5 tok/s.*

CUDA Recipes 005 · 2026-10-21 · [Study repository](https://github.com/majorminorlabs/cuda-recipes/tree/main/005-ornith-122b-offload)

![How Ornith-1.5-122B runs on a 24GB RTX 3090: the CPU computes offloaded routed experts with their weights in system RAM; attention, the shared expert, and remaining routed experts run on the GPU. Activations cross PCIe. Only 8 of 256 routed experts are selected per token in each MoE layer. Schematic.](https://majorminor.xyz/social/research/cuda-recipes-005.png)

Ornith released Ornith-1.5-122B on October 20. It's a 125B-parameter mixture-of-experts model with an estimated 9 to 10B parameters active per token, and the model card says it serves on one 80GB GPU. Most people don't have one of those. Plenty of people have a 3090.

The model doesn't fit in 24GB at any quant worth using. The smallest Unsloth file is 40 GB. But only a small slice of the weights is touched for each token, which is the setup that made [CUDA Recipes 004](https://majorminor.xyz/research/cuda-recipes-004) work: keep attention and the shared expert on the GPU, park the routed experts in system RAM, and let llama.cpp's `--n-cpu-moe` decide how many layers of experts live where.

So we measured it on day one. One 3090, plain llama.cpp, two Unsloth quants, about three hours and $1.53.

## TL;DR

- **It runs, and quality holds.** Q4 perplexity was 5.7746, 0.21% above AtomicChat's BF16 reference of 5.7625. Q3 was 5.8312, 1.19% above. Both scored 18/20 on a fixed exact-match task set, and they missed the same two items.
- **Q4 decodes at 12 to 22 tok/s.** At 32K context, the median of three runs was 15.5 tok/s decode and 548 tok/s prefill. The same Q4 configuration landed anywhere from 12.2 to 21.7 tok/s across separate runs on this host, so read 15.5 as a point in a range.
- **Q3 is the faster talker.** At 32K, 26.3 tok/s decode and 311 tok/s prefill, and it stayed between 25 and 28 tok/s across runs. It reads prompts slower than Q4.
- **128K fits on the 3090.** One run at 128K context: 416 tok/s prefill and 21.2 tok/s decode, 22,562 MiB peak VRAM.
- **The thread trap is back.** The container showed llama.cpp 256 CPUs. It picked 128 threads and decoded at 2.5 tok/s. With `-t 16`, the same configuration decoded at 20.0 tok/s.

| Quant | Context | Prefill tok/s | Decode tok/s | Peak RAM |
| --- | ---: | ---: | ---: | ---: |
| Q4_K_XL | 32K | 548 | 15.5 | 55.1 GiB |
| Q4_K_XL | 128K | 416 (1 run) | 21.2 (1 run) | 58.4 GiB |
| Q3_K_XL | 32K | 311 | 26.3 | 38.6 GiB |

## Setup

A RunPod Secure Cloud pod (EU-CZ-1): one RTX 3090 24GB, 32 vCPUs of an AMD EPYC 7763, 125 GB RAM, $0.53/hr.

- **Model:** [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B), MIT license. 48 layers, 12 of them full attention and 36 linear attention, 256 routed experts with 8 active per token, one shared expert, one multi-token-prediction head.
- **Quants:** [unsloth/Ornith-1.5-122B-GGUF](https://huggingface.co/unsloth/Ornith-1.5-122B-GGUF) at revision `3842d00`. UD-Q4_K_XL (79.7 GB) and UD-Q3_K_XL (59.8 GB). All six shards matched their published SHA-256.
- **Runtime:** llama.cpp tag `b11757`, commit `13786fb`, built with CUDA for sm_86.
- **Quality reference:** AtomicChat's held-out `eval_neutral` set from [calib-corpora](https://huggingface.co/datasets/AtomicChat/calib-corpora) (revision `933ce48`, 87 chunks at 4,096 tokens) and their published BF16 perplexity on it.

The architecture matters for context. Only the 12 full-attention layers keep a KV cache, with 2 KV heads each. That works out to about 24 KB per token, or roughly 3 GiB at 128K, so we kept the cache at f16 throughout. This number is computed from the config, not measured separately.

## The recipe

Q4, for a 24GB card and 128 GB of system RAM:

```bash
llama-server -m Ornith-1.5-122B-UD-Q4_K_XL-00001-of-00003.gguf \
  -ngl 99 --n-cpu-moe 38 -c 32768 -fa on -t 16 --load-mode none
```

Q3, for a 24GB card and a smaller RAM budget:

```bash
llama-server -m Ornith-1.5-122B-UD-Q3_K_XL-00001-of-00003.gguf \
  -ngl 99 --n-cpu-moe 36 -c 32768 -fa on -t 16 --load-mode none
```

Three notes before you paste:

- **`--n-cpu-moe N`** keeps the routed experts of the first N layers in system RAM. Lower is faster until the card runs out of memory. On the 3090, Q4 ran out at 35 and Q3 at 32. For 128K context on Q4, use 40.
- **`-t`** is the one to get right. Set it to the CPU cores you actually have, not what the machine reports. More on that below.
- **`--load-mode none`** is what `--no-mmap` became in this build. It loads the weights into RAM instead of mapping the file, which keeps the memory numbers honest.

Ornith-1.5-122B is a reasoning model and thinks by default. For quick answers, pass `"chat_template_kwargs": {"enable_thinking": false}` in the request. Ornith's recommended sampling for coding is temperature 0.6, top-p 0.95, top-k 20.

## Result 1: it runs, and the answers hold up

The first question with any aggressive quant is whether it's still the same model.

![Perplexity with reported error bars: BF16 reference 5.7625, Q4 5.7746, Q3 5.8312. The horizontal axis shows a detail scale.](https://majorminor.xyz/research/cuda-recipes-005/charts/fig2-perplexity.png)

*AtomicChat's BF16 result is an external reference on the same held-out set. Whiskers show the reported ± error, not a new confidence-interval calculation.*

Q4 is inside the error bars of the reference. Q3 drifts a little, about what you'd expect from losing another bit per weight.

Both quants scored 18/20 on the task set: short prompts with exact answers covering arithmetic, string handling, and a few Python outputs. They missed the same two. One was reversing the string "lighthouse", which models of every size get wrong because of how text is tokenized. The other was answering "150 miles" when the expected answer was "150", which is a formatting miss rather than a wrong answer. We scored it as a miss anyway.

This is a sanity check, not a benchmark. It tells you the quant isn't broken. For how Unsloth's and other quants compare in detail, AtomicChat has published KL divergence and top-1 agreement across a dozen files on the [AtomicChat/Ornith-1.5-122B-GGUF](https://huggingface.co/AtomicChat/Ornith-1.5-122B-GGUF) card.

## Result 2: speed on a 3090

Here's the Q4 offload sweep at empty context, 32 threads, median of three runs:

| `--n-cpu-moe` | Prefill tok/s | Decode tok/s |
| ---: | ---: | ---: |
| 49 (all experts on CPU) | 618 | 11.9 |
| 45 | 762 | 16.8 |
| 41 | 779 | 19.6 |
| **38** | 257 | **21.7** |
| 35 | out of memory | out of memory |

Every layer of experts moved onto the GPU buys decode speed, and the card fills up at 38. That's the setting we used.

The 257 tok/s prefill at 38 is not a typo, and it isn't a property of that setting. It's one of three runs in this study where prefill came in at roughly a third of its neighbors with identical settings. The other two were the first pass at 49 (219 tok/s, against 618 on the rerun) and the 30-thread row of the thread sweep. We logged them and didn't chase them mid-run. The 32K prefill of 548 tok/s comes from a separate sweep at the same settings.

Decode had the same problem in a milder form. The Q4 configuration we recommend, 38 layers on CPU at 16 threads, decoded at 20.0 tok/s in the thread sweep and 12.2 tok/s in the depth sweep an hour later. Same pod, same command, same empty context.

That's why the headline is a range. On this host, Q4 decoded at 12 to 22 tok/s, and the 32K median of 15.5 sits inside that. It also explains the apparent speed increase with context depth:

![Decode and prefill at each context depth, with unconnected measurements and repetition min–max whiskers. Q4 varies substantially across runs; the 128K point is one run at a different offload setting.](https://majorminor.xyz/research/cuda-recipes-005/charts/fig3-speed-vs-context.png)

*Points are separate measurements, with medians and min–max over three repetitions. The 128K diamond is one Q4 run with 40 CPU MoE layers instead of 38. Q3 uses 36.*

Q4 shouldn't get faster as context grows, and it didn't really. The run-to-run swing on this host was bigger than the cost of the context. The hybrid architecture is part of why that's possible: with only 12 attention layers holding a cache, going from empty to 128K costs little, so host noise dominates.

Q3 behaved the way you'd expect. It slowed slightly with depth and stayed within a narrow band. If you want one number to plan around, Q3's are the steadier ones.

## Result 3: the thread count trap, again

[CUDA Recipes 004](https://majorminor.xyz/research/cuda-recipes-004) found this on a different model. It happened again, and it was worse.

Inside the container, `nproc` reported 256 CPUs: the host's two EPYC 7763s with SMT. Our pod was allocated 32. With no `-t` flag, llama.cpp chose 128 threads.

![Q4 decode by thread count: 17.6 tok/s at 8 threads, 20.0 at 16, 16.9 at 24, 18.4 at 30, 15.9 at 32, and 2.5 at the default 128.](https://majorminor.xyz/research/cuda-recipes-005/charts/fig4-thread-trap.png)

*Q4, 38 CPU MoE layers, empty context. Bars show medians; whiskers show min–max over three repetitions.*

The default was much slower than any explicit setting we tried. Anyone trying this on a cloud pod and getting single digits should check this first.

Prefill barely cares between 8 and 32 threads: around 758–772 tok/s, apart from the 30-thread outlier at 255. The default reached 447. Decode peaked at 16. We'd treat 16 vs 32 as within the noise and the default as the real cliff. The complete thread sweep is in [RESULTS.md](https://github.com/majorminorlabs/cuda-recipes/blob/main/005-ornith-122b-offload/RESULTS.md#q4-thread-sweep).

To find your real core count inside a container:

```bash
cat /sys/fs/cgroup/cpu.max
```

Divide the first number by the second. On this pod it was 31.13.

## Result 4: Q3 for chat, Q4 for long prompts

At 32K context, Q3 decoded about 1.7x faster than Q4 (26.3 vs 15.5 tok/s) and read prompts about 1.8x slower (311 vs 548 tok/s).

Decode makes sense: Q3 is a smaller file, so less data moves per token. The slower prefill is the surprise, because Q3 also had more experts resident on the GPU at its best setting. Our guess is the denser compression formats in the Q3 file cost more compute to unpack while reading a prompt. We didn't verify that, so treat it as a guess.

The practical version:

- **Chatting, short prompts:** Q3. Replies come faster and quality is within about 1% of BF16 perplexity.
- **Pasting in long documents or a codebase:** Q4. A 32K prompt takes about a minute at Q4's rate and closer to two at Q3's.

On RAM, Q3 peaked at 38.6 GiB during its benchmarks and Q4 at 55.1 GiB. Q3 should leave room on a 64 GB desktop. We didn't verify that on a 64 GB machine, and Q3 peaked at 55.8 GiB during the perplexity run, which used memory-mapped loading. Use `--load-mode none` if RAM is tight.

## Result 5: 128K fits

At 128K context, Q4 ran out of GPU memory with 38 layers on CPU and completed at 40. One run: 416 tok/s prefill, 21.2 tok/s decode, 22,562 MiB peak VRAM, 58.4 GiB peak system RAM.

That's a 122B model holding a 128K context on a single consumer card. It's one repetition, so take the speed as approximate. It fits.

## What about MTP?

The model ships a multi-token-prediction head, and llama.cpp can use it to draft tokens ahead with `--spec-type draft-mtp`. We tried it.

It only loaded at 42 layers on CPU, because the drafting state needs its own GPU memory. In that configuration, 30 of 144 drafted tokens were accepted (20.8%), and decode on the task set was 10.9 tok/s against 17.9 for the base run at 38.

That isn't a clean comparison, since the two runs used different offload settings. What we can say is that a 21% acceptance rate is too low for drafting to pay for itself. With experts on the CPU, we'd leave it off for now.

## What this doesn't tell you

- **Your CPU and RAM decide your decode speed.** With experts in system RAM, every token reads them from memory. This pod's EPYC measured 48,773 MiB/s on `sysbench memory` (1 MiB blocks, writes, 32 threads). We haven't run the same test on a desktop, so we can't say whether yours will be faster or slower. Run `sysbench memory --memory-block-size=1M --memory-total-size=64G --threads=<your cores> run` and compare.
- **This was a cloud pod, and it was noisy.** Same-settings runs varied by up to about 1.8x on decode and 3x on prefill. 004 warned about shared cloud CPUs. Secure Cloud didn't fix it.
- **The 64 GB recommendation is unverified.** It's based on peak memory on a 125 GB pod.
- **128K was one run.**
- **Quality is a sanity check.** Perplexity on one held-out set plus 20 exact-match prompts, thinking off. No agentic or coding benchmarks.
- **One crash.** The Q3 sweep at 32 layers on CPU ran out of GPU memory and aborted with a core dump. No number in this post comes from that run.
- **No 5090 yet.** 32GB should allow fewer layers on CPU and more speed. That's the next run.

## Cost

| Item | Value |
| --- | ---: |
| Pod time | 2 h 53 min |
| Rate | $0.53/hr |
| **Total** | **$1.53** |

That covers downloading both quants, building llama.cpp, and every benchmark in this post.

## Data and reproducibility

Everything is in the [study repository](https://github.com/majorminorlabs/cuda-recipes/tree/main/005-ornith-122b-offload):

- `RESULTS.md`: every sweep, with min and max for each median
- `logs/`: raw llama-bench JSONL, server logs, perplexity logs, VRAM samples, and timing for every command
- `receipts/`: SHA-256 of every shard, the llama.cpp commit, host details, RAM bandwidth, start and end times, and the cost calculation
- `tasks/tasks.jsonl` and `scripts/score.py`: the task set and scorer

Pinned artifacts:

| Artifact | Pin |
| --- | --- |
| Model | `ornith-ai/Ornith-1.5-122B` |
| Quants | `unsloth/Ornith-1.5-122B-GGUF` @ `3842d003341507c216295c6f28dfcd30349925c6` |
| Q4_K_XL shard 1 | `7159d31a…ff359` |
| Q3_K_XL shard 1 | `d8a23c48…74fe5` |
| llama.cpp | `b11757` @ `13786fbb3a1aaf4ff445c0b92d9f21cbe0af6d42` |
| Eval set | `AtomicChat/calib-corpora` @ `933ce4826d0fe764a5cd6674bc9e0af5f5e985b1` |

If you run this on your own 3090 or 5090, send us your numbers along with your CPU and RAM. The decode figure depends more on that than on the GPU, and a few home desktops would tell us more than another cloud pod.

## Credits

Thanks to Ornith for releasing the model under MIT, to Unsloth for the GGUF quants, which were up within hours of launch, and to the llama.cpp contributors for day-one `qwen35moe` support. Thanks to AtomicChat for the BF16 reference perplexity, the public eval set, the tested build tip (b11736) and the MTP flag.
