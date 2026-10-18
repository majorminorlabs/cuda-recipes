---
title: "Nemotron 3.5 Bolt 24GB decodes 2x faster than Qwen3.8 27B. It didn't finish tasks any faster."
slug: cuda-recipes-001
series: CUDA Recipes 001 (MAJOR//MINOR 24GB Compression Study)
date: 2026-10-XX
status: DRAFT (not published)
summary: "On an RTX 3090 and RTX 5090, NVIDIA's Nemotron 3.5 Bolt 24GB generated tokens about 2x faster than Qwen3.8 27B Q4_K_M but wrote about 1.5x more per task, so median time to a finished task was a tie. Qwen passed more strict tasks on both GPUs, and almost all of that gap was tool calling."
meta_description: "On an RTX 3090 and RTX 5090, NVIDIA's Nemotron 3.5 Bolt 24GB generated tokens about 2x faster than Qwen3.8 27B Q4_K_M but wrote about 1.5x more per task, so median time to a finished task was a tie. Qwen passed more strict tasks on both GPUs, and almost all of that gap was tool calling."
og_description: "On an RTX 3090 and RTX 5090, NVIDIA's Nemotron 3.5 Bolt 24GB generated tokens about 2x faster than Qwen3.8 27B Q4_K_M but wrote about 1.5x more per task, so median time to a finished task was a tie. Qwen passed more strict tasks on both GPUs, and almost all of that gap was tool calling."
og_image: https://majorminor.xyz/research/cuda-recipes-001/social/cuda-recipes-001-og-share.png
twitter_image: https://majorminor.xyz/research/cuda-recipes-001/social/cuda-recipes-001-x-share.png
reddit_image: https://majorminor.xyz/research/cuda-recipes-001/social/cuda-recipes-001-reddit-share.png
---

# Nemotron 3.5 Bolt 24GB decodes 2x faster than Qwen3.8 27B. It didn't finish tasks any faster.

NVIDIA's launch chart for Nemotron 3.5 Bolt 24GB sells speed. It sits far to the right of Qwen3.8 27B on tokens per second and a bit lower on intelligence. A 2-bit MoE with 9B active parameters should decode faster than a dense 27B at Q4, and it did, about 2x on both cards we tried.

What we wanted to know was whether that speed gets work done faster, and what you give up for it. So we ran both models on an RTX 3090 and an RTX 5090: same 40 tasks, same seeds, same llama.cpp build, every layer on the GPU, 16K context. 480 scored trials.

Mostly, the speed didn't turn into faster tasks. Bolt wrote about 1.5x more tokens per task, so median time to a finished task came out even. The two models were level on single-turn work, but Qwen won tool calling by a wide margin, and local agents are exactly what Bolt is being pitched for.

Update: CUDA Recipes 001 ran at 16K context. Context scaling on the same card and files is covered in [CUDA Recipes 002](/research/cuda-recipes-002).

## TL;DR

- **2x the tok/s, same time to done.** Bolt decoded at 85.2 vs 41.5 tok/s on the 3090 (148.3 vs 72.5 on the 5090), but generated ~1.5x more tokens per trial. Median trial time: 5.68 s vs 5.37 s on the 3090, 3.44 s vs 3.47 s on the 5090.
- **The quality gap is tool calling.** Pooled across both GPUs, single-turn tasks were even (Bolt 108/156, Qwen 105/156). Tool-calling tasks: Qwen 68/84, Bolt 38/84. 19 of Bolt's tool-calling failures were truncations at the harness's 512-token per-turn cap with thinking on.
- **Qwen passed more strict tasks overall.** 3090: 89/120 (74.2%) vs 75/120 (62.5%). 5090: 84/120 (70.0%) vs 71/120 (59.2%).
- **It does fit on 24GB, at 16K.** All 89 layers on the 3090, 21,339 MiB peak VRAM. Longer contexts weren't tested here; NVIDIA says the model targets 128K under 24GB, and that's the next run.
- **Same shape as NVIDIA's chart.** NVIDIA's launch chart places Qwen3.8 27B Q4 above Bolt on intelligence (GDPval v2) and Bolt well ahead on speed. Our results land in the same direction on a different benchmark and different GPUs.
- **The 5090 was faster, and that's about all we can say about it.** Decode ran about 1.75x faster than the 3090 for both models. Strict success was 3.75 points lower on the 5090, with a 95% interval of −8.75 to +0.83 points. That includes zero, and the two GPUs ran on different nodes with different drivers, so we don't read anything into it.
- **Both scored runs together cost about $0.95** in estimated GPU rental.

All data, charts, and scripts are downloadable at the bottom.

## The recipe

Tested on an RTX 3090 24GB and RTX 5090 32GB, one model at a time, at 16K context.

**Build llama.cpp at the tested commit**

Set `LLAMA_CPP_DIR` to your llama.cpp checkout, `LLAMA_CPP_REV` to `620d2225cc436ab0b001e3200e590e3b286ef9ab`, `CUDA_ARCHITECTURE` to `86` for the 3090 or `120` for the 5090, `CUDA_TOOLKIT_ROOT` to your CUDA 12.8 installation, and `CUDACXX` to its `bin/nvcc`. These are the build commands from the study runner:

```sh
git -C "$LLAMA_CPP_DIR" checkout --detach "$LLAMA_CPP_REV"
rm -rf "$LLAMA_CPP_DIR/build"
cmake -S "$LLAMA_CPP_DIR" -B "$LLAMA_CPP_DIR/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_COMPILER="$CUDACXX" \
  -DCUDAToolkit_ROOT="$CUDA_TOOLKIT_ROOT" \
  -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCHITECTURE" \
  -DGGML_CUDA=ON -DGGML_NATIVE=ON \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON
cmake --build "$LLAMA_CPP_DIR/build" --parallel "$(nproc)" --target llama-server llama-cli
```

**Download the exact files**

Set `MODEL_DIR` to the directory where you want the weights. The download commands below are copied from the study runner:

```sh
mkdir -p "$MODEL_DIR"
python3 -m venv "$MODEL_DIR/hf-venv"
"$MODEL_DIR/hf-venv/bin/pip" install --disable-pip-version-check huggingface_hub
HF="$MODEL_DIR/hf-venv/bin/hf"
mkdir -p "$MODEL_DIR/nemotron" "$MODEL_DIR/qwen"
"$HF" download nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF \
  NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf \
  --revision e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246 --local-dir "$MODEL_DIR/nemotron"
"$HF" download Abiray/Qwen3.8-27B-Q4_K_M-GGUF \
  Qwen3.8-27B-Q4_K_M.gguf \
  --revision f7a1cda580fe828415151042bf9f3dc5bb8b0d76 --local-dir "$MODEL_DIR/qwen"
```

**Serve either model at 16K**

Set `MODEL_FILE` to `$MODEL_DIR/nemotron/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf` or `$MODEL_DIR/qwen/Qwen3.8-27B-Q4_K_M.gguf`. The same command served both files; all flags below are copied from the study runner and checked against the scored server logs.

```sh
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$LLAMA_CPP_DIR/build/bin/llama-server" \
  --model "$MODEL_FILE" --host 127.0.0.1 --port 8000 \
  --ctx-size 16384 --parallel 1 --batch-size 512 --ubatch-size 128 \
  --cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 \
  --flash-attn on --jinja --verbose
```

Nemotron peaked at 21,339 MiB on the 3090 and 21,865 MiB on the 5090; Qwen peaked at 16,481 and 16,514 MiB. Decode was about twice as fast for Nemotron, but median time to a finished task was a tie.

For another NVIDIA GPU, set `CUDA_ARCHITECTURE` for that device and remeasure memory headroom before raising context or adding parallel slots.

## Why we ran this

The 24GB card is the most common "serious" local setup, and it sits right on the line where you start trading things off. More parameters, or more bits per parameter? More tokens per second, or more tasks done right?

NVIDIA's Nemotron 3.5 Bolt 74B-A9B 24GB GGUF is interesting because it isn't a community squeeze of a model that was never meant to go that low. NVIDIA built and labels it as a 24GB deployment artifact. That made it a fair thing to put next to a mid-size model at the quant most of us actually run.

### What NVIDIA says, and what we tested

Per its model card, Bolt was compressed from Nemotron 3.5 Super VL 120B-A12B. NVIDIA cut it to 74B total and about 9B active parameters, then quantized the experts to roughly 2 bits with quantization-aware distillation. NVIDIA's [launch post for Bolt](https://x.com/NVIDIARTXSpark/status/2110813633697694003) pitches it as putting "powerful local agents within reach" and says it's optimized for RTX Spark. It includes an "Intelligence vs Speed (Small Models <24GB)" chart that plots GDPval v2 against AIPerf SPEED-Bench tokens per second. On that chart, Qwen3.8 27B Q4 sits higher on intelligence and lower on speed, and Bolt sits further right with a lower score.

Our results point the same way. That's consistency and nothing more: GDPval and our strict task suite measure different things, we don't know the exact hardware behind NVIDIA's chart, and we haven't reproduced their numbers. What we can add is the stuff a tokens-per-second axis can't show: how much each model writes per task, how long a task actually takes to finish, and which kinds of tasks the gap comes from. Agent-style tool calling turned out to be most of it.

Two scope notes. We tested **Bolt only**, so none of this tells you anything about the full Super VL model. And we tested **text only**: Bolt's card lists a vision encoder, but we sent no images and loaded no vision projector.

This isn't a quantization study, though, and we want to be clear about that up front. The two models differ in family, training, architecture, and who made the GGUF. We're comparing two specific files you can download today, on a specific task suite. We aren't isolating what 2-bit does to a model.

## The two models

| | Nemotron 3.5 Bolt 74B-A9B 24GB | Qwen3.8 27B |
|---|---|---|
| Architecture (per model cards) | Mamba-2 / Transformer hybrid, LatentMoE | Dense hybrid: Gated DeltaNet linear attention + gated full attention every 4th block, 64 layers |
| Total params | 74B | 27B |
| Active params per token | ~9B (per the A9B name and NVIDIA's card) | 27B (dense) |
| GGUF | Official NVIDIA, "native 2-bit" | Q4_K_M, third-party conversion (Abiray, llama.cpp b10430) |
| How it was quantized | Per NVIDIA's card: experts at IQ2_XXS (2.0625 bits/element) with quantization-aware distillation; Mamba layers NVFP4; embedding/output Q8_0 | Standard llama.cpp Q4_K_M |
| File size | 22.02 GB (20.51 GiB) | 16.81 GB (15.66 GiB) |
| Rough bits/weight (file bytes ÷ nominal params) | ~2.38 | ~4.98 |
| Layers on GPU in this study | 89/89 | 66/66 (as llama.cpp counts them) |
| License | NVIDIA OpenMDW-1.1 | Apache 2.0 |

That "~9B active" row matters for everything below. Nemotron is a 74B mixture-of-experts model that only uses about 9B parameters per token, and those weights are about 2 bits each. Qwen is dense, so all 27B are used every token, at about 5 bits each. Per token, Nemotron moves a lot less weight data through memory. The decode speed difference lines up with that, though we didn't profile it.

One hardware note for 3090 owners. NVIDIA's model card lists Ada Lovelace and Blackwell as supported. The 3090 is Ampere. It loaded and ran fine on the llama.cpp commit we used, with every layer on the GPU. We didn't check numerical parity against a supported GPU, and Ampere has no native FP4 hardware for the NVFP4 Mamba layers, so treat 3090 support as "worked here" rather than "supported."

## Setup

**Hardware.** One RunPod RTX 3090 (24GB, driver 580.126.20) and one RunPod RTX 5090 (32GB, driver 570.195.03), run one after the other.

**Runtime.** llama.cpp commit `620d2225` (v0.7.0), CUDA 12.8.93, built for sm_86 on the 3090 and sm_120a on the 5090. Server flags:

```
--ctx-size 16384 --parallel 1 --batch-size 512 --ubatch-size 128
--cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 --flash-attn on --jinja
```

Every layer on CUDA, no CPU layer offload. (llama.cpp reports a few hundred MiB of `CPU_Mapped` buffer for each model. That's the memory-mapped GGUF file, and no layers ran on the CPU.)

**Sampling.** Thinking enabled for both. Temperature 1.0 and top_p 0.95 for both. top_k 40 for Nemotron, 20 for Qwen, each following its maker's recommendation. Each task repetition has a fixed seed, and both models get the same seed.

**Generation limits.** 2,048 tokens for single-turn tasks. For tool tasks, 512 tokens per turn and at most 6 tool turns. Keep that 512 in mind.

**Tasks.** 40 frozen tasks across five categories: coding (12), terminal/system commands (8), tool use (8), structured data (6), multi-step tool workflows (6). Each model ran each task 3 times per GPU. That's 120 trials per model per GPU, 240 per GPU, 480 total.

**Scoring.** Deterministic, binary, strict, with no model-as-judge. Every task has a reference solution that passes its scorer and a negative control that fails it.

- Coding: the model returns a Python `solve` function as JSON, which is checked against an AST allowlist and then run on fixed test cases.
- Terminal: the command has to match a hand-validated allowlist of accepted forms.
- Structured data: exact JSON value equality.
- Tool use and multi-step: typed tool schemas against simulated tools. The ordered call trace and the final JSON both have to match exactly.

"Strict" really does mean strict. A good answer that breaks the contract fails. There's more on what that means below, and it's worth reading before you lean on any single number.

## Result 1: it fits, with room to spare at 16K

| GPU | Model | Peak VRAM (MiB) | Card VRAM (MiB) |
|---|---|---:|---:|
| RTX 3090 | Nemotron | 21,339 | 24,576 |
| RTX 3090 | Qwen | 16,481 | 24,576 |
| RTX 5090 | Nemotron | 21,865 | 32,607 |
| RTX 5090 | Qwen | 16,514 | 32,607 |

That leaves roughly 3.2 GiB of headroom for Nemotron on the 3090 at 16K context with a Q8_0 KV cache. We didn't test longer contexts. NVIDIA's card says the model is designed for under 24GB at 128K context with its own recipe, which we didn't use.

Peak container RAM was about 47 GiB for both models on both GPUs (46.87 to 47.55 GiB). That's a cgroup counter, and those normally include page cache from reading and mapping the GGUF. Treat it as an upper bound on what the container touched, not a minimum system RAM requirement. We didn't test a low-RAM host.

## Result 2: twice the tokens per second, about the same time per task

![Decode rate, tokens generated, and full-trial latency by model and GPU](charts/fig2-speed-decomposition.svg)

| GPU | Model | Decode tok/s | Prompt tok/s | Tokens generated / trial (mean) | Trial latency mean / median / p95 (s) |
|---|---|---:|---:|---:|---:|
| RTX 3090 | Nemotron | 85.2 | 833.2 | 471 | 6.65 / 5.68 / 14.74 |
| RTX 3090 | Qwen | 41.5 | 963.4 | 314 | 8.58 / 5.37 / 24.61 |
| RTX 5090 | Nemotron | 148.3 | 1053.0 | 486 | 4.19 / 3.44 / 11.26 |
| RTX 5090 | Qwen | 72.5 | 1246.7 | 318 | 5.18 / 3.47 / 13.78 |

Throughput figures are means of per-trial rates. Latency is the whole trial, including prompt processing, generation, and any tool turns.

Nemotron's decode advantage is real and very consistent: 2.05x on both cards. Prompt processing went the other way, and Qwen was about 15 to 18% faster there.

What you feel as a user is time to a finished answer, and Nemotron spent a lot of its speed on writing more. It averaged about 1.5x Qwen's generated tokens per trial (median 366 vs 191 on the 3090). The result:

- **Median** trial time was basically a wash: 5.68 s vs 5.37 s on the 3090, 3.44 s vs 3.47 s on the 5090.
- **Mean** and **p95** favored Nemotron, because Qwen had a longer slow tail (p95 24.61 s vs 14.74 s on the 3090).

So "2x faster" is true for decode and not true for getting a typical task done in this setup. If your workloads are long generations with similar output lengths, the decode number matters more. For short agent turns, verbosity eats most of it.

## Result 3: Qwen passed more strict tasks, on both GPUs

![Strict success by model and GPU with 95% task-cluster bootstrap intervals](charts/fig1-strict-success.svg)

| GPU | Model | Passed | Rate | 95% CI (task-cluster bootstrap) |
|---|---|---:|---:|---:|
| RTX 3090 | Nemotron | 75/120 | 62.5% | 49.2 to 75.0% |
| RTX 3090 | Qwen | 89/120 | 74.2% | 61.7 to 85.0% |
| RTX 5090 | Nemotron | 71/120 | 59.2% | 45.8 to 72.5% |
| RTX 5090 | Qwen | 84/120 | 70.0% | 56.7 to 82.5% |

The intervals resample whole tasks, not individual trials, because three runs of the same task aren't independent. With only 40 tasks they're wide, and the per-model intervals overlap.

So we also ran a paired comparison, resampling tasks and comparing both models on the same tasks (10,000 resamples). This one is our own editorial calculation and isn't in the original analysis package. The script is in the download.

| | Qwen minus Nemotron | 95% CI | Tasks where Qwen did better / Nemotron did better / tied |
|---|---:|---:|---:|
| RTX 3090 | +11.7 pts | +0.8 to +23.3 | 12 / 4 / 24 |
| RTX 5090 | +10.8 pts | 0.0 to +21.7 | 13 / 3 / 24 |

The direction is consistent, the size is similar on both cards, and the lower bound sits right at zero. We'd call that a real pattern on this suite and stop short of calling it a settled difference. It also depends heavily on a handful of tasks, which is the next section.

## Where the gap comes from: tool calling

![Strict success by task category, model, and GPU](charts/fig3-category-success.svg)

| Category (tasks) | Nemotron 3090 | Nemotron 5090 | Qwen 3090 | Qwen 5090 |
|---|---:|---:|---:|---:|
| Coding (12) | 22/36 | 20/36 | 23/36 | 20/36 |
| Terminal/system (8) | 20/24 | 18/24 | 17/24 | 17/24 |
| Tool use (8) | 11/24 | 13/24 | 24/24 | 22/24 |
| Structured data (6) | 15/18 | 13/18 | 14/18 | 14/18 |
| Multi-step (6) | 7/18 | 7/18 | 11/18 | 11/18 |

If you split the suite by whether the model has to call tools, the picture gets very clear:

| Pooled across both GPUs | Nemotron | Qwen |
|---|---:|---:|
| Single-turn tasks (coding, terminal, structured data) | 108/156 (69.2%) | 105/156 (67.3%) |
| Tool-calling tasks (tool use, multi-step) | 38/84 (45.2%) | 68/84 (81.0%) |

On single-turn work the 74B was level with Qwen, slightly ahead if anything, and it led on terminal commands on both cards. The whole overall gap comes from tool calling.

Then look at *how* Nemotron failed:

![Failure classes pooled across both GPUs](charts/fig4-failure-classes.svg)

Pooled across both GPUs, Nemotron had 20 truncated outputs and 9 invalid-JSON failures. Qwen had 2 and 0. Of Nemotron's 46 tool-calling failures, 19 were truncations (its 20th truncation was a structured-data task). Tool tasks are where the harness allows only 512 tokens per turn, with thinking on. Nemotron also writes about 1.5x more tokens per trial in general.

Our read, which we haven't tested: a meaningful share of Nemotron's tool-calling deficit may be the model running out of per-turn budget while reasoning, before it emits a valid call. That's a harness setting interacting with a model's verbosity, which is a different thing from the model not knowing how to use tools. Both matter if you're running it with similar limits. Raising the per-turn cap is the obvious follow-up, and we didn't run it here. Not every failure was a truncation either. Nemotron also had 11 wrong action sequences or final answers, and it went 0/6 on TO04 (a single read-only calendar `list` call) mostly through invalid JSON.

## RTX 3090 vs RTX 5090

Same files, seeds, settings, and tasks on both cards.

**Speed.** The 5090 decoded about 1.74x faster for Nemotron and 1.75x for Qwen. Median trial latency dropped from about 5.4 to 5.7 s to about 3.4 to 3.5 s.

**Strict success.** 164/240 (68.3%) on the 3090 and 155/240 (64.6%) on the 5090. That's a difference of −3.75 points, with a 95% task-cluster CI of −8.75 to +0.83. By model: Nemotron −3.33 points (CI −10.0 to +3.33), Qwen −4.17 points (CI −10.0 to +0.83). All of these include zero.

**Agreement.** Paired trials (same model, task, repetition, seed) reached the same pass/fail outcome on 207/240 (86.25%). 21 passed only on the 3090 and 12 passed only on the 5090. Cohen's κ was 0.651 for Nemotron and 0.731 for Qwen.

Don't take this as "the 3090 gives better answers." The cards had different CUDA targets, different drivers, and different provider nodes. Same seeds don't guarantee the same tokens across different GPU execution paths, and there was one session per GPU. The flips we looked at were contract issues. For example, Qwen on the 5090 once wrote a Python conditional expression that the restricted-AST scorer rejects, and once made extra out-of-order tool calls before returning the same final JSON that passed on the 3090. None were runtime failures or offload. All 33 are listed in the data.

## Cost

| GPU | Allocated GPU-hours | Quoted rate | Estimated cost |
|---|---:|---:|---:|
| RTX 3090 | 0.720 | $0.50/h | $0.36 |
| RTX 5090 | 0.498 | $1.19/h | $0.59 |
| **Total** | **1.218** | | **$0.95** |

These are uptime × quoted rate estimates. The provider hadn't posted a billing row for the 5090 pod at verification time, so the totals aren't invoiced charges, and they exclude any non-GPU charges.

## What this benchmark is, and what it isn't

Please read this section before quoting any number above.

**The tasks are small and the contracts are tight.** These are short, well-specified tasks: write a function that dedupes a list, give the `ss` command for listening sockets, call `add(17, 25)` and return `{"done": true}`. They test whether a model can do a simple job *and* follow the exact output contract. They don't measure general intelligence or long-horizon agent work.

**The coding scorer runs on a restricted Python subset.** For safety, candidate code is checked against an AST allowlist before it runs. No attribute access (so `out.append(x)` fails), no conditional expressions, no `while`, no lambdas, no imports. The only callable builtins are `sum`, `max`, `min`, `sorted`, `set`, `len`, and `range`. The coding prompts don't spell those limits out. So the coding category partly measures whether a model happens to write code inside an unstated subset, and that's a big part of why both models sit around 55 to 64% there.

**Five tasks were never passed by either model, on either GPU:** three coding tasks (dedupe preserving order, merge two sorted lists, flatten one level), one structured-data task (the mean of [2, 4, 9] as bare JSON), and one multi-step workflow. Most of those are trivial for any modern model. That's a strong hint that the contract, rather than the capability, is what's being measured on those tasks. The public package doesn't include raw responses, so we can't show you exactly what was written.

**Tool use is simulated.** Deterministic fixture tools with exact expected call traces. Extra calls, out-of-order calls, or a slightly different final JSON all fail. Real tool use is more forgiving in some ways and much harder in others.

**Other things to keep in mind:**

- 40 tasks × 3 repetitions is small. Intervals are wide.
- On both GPUs, Qwen's 120 trials ran first, then Nemotron's, so the model wasn't reloaded mid-run. Order and thermal effects aren't ruled out.
- Thinking was on for both, with each model's default effort. Different reasoning settings could change both speed and success.
- We used plain decoding. NVIDIA's recipes for Nemotron use DFlash speculative decoding with a separate drafter, which we didn't test, so NVIDIA's intended setup may be faster than what we measured.
- 16K context only.
- One GGUF per model. The Qwen file is a third-party conversion. We verified its SHA-256 and that its embedded chat template exactly matches Qwen's upstream template. Its Hugging Face page also showed an inconsistent automated scanner message, which is noted in the manifest.

## So what does this mean if you run models locally?

Scoped to these files, this runtime, and tasks like these:

1. **A 74B-class model really does fit on a single 24GB card now, fully on GPU, at 16K.**
2. **Don't buy the decode number by itself.** Nemotron's 2x tok/s mostly went into writing longer responses. Measure time to a finished task on your own workload.
3. **If your workload is single-turn (code snippets, commands, JSON transforms), the two were even here.** Nemotron was slightly ahead and clearly better on terminal commands.
4. **If you run agents or tool calling with tight per-turn token limits, Qwen3.8 27B Q4_K_M was much more reliable here.** That's worth knowing, since local agents are exactly what Bolt is being pitched for. If you want to try Nemotron for agent work, give it more per-turn headroom and check whether that closes the gap. We haven't, yet.
5. **Moving from a 3090 to a 5090 made both models about 1.75x faster at decode,** with no clear change in task success.

## Data and reproducibility

**Download:** `nemotron-qwen-24gb-study-data.zip` [LINK], which contains:

- `paired-runs.csv`: all 480 trials with pass/fail, failure class, latency, tokens, prompt/decode rates, VRAM, RAM
- per-GPU canonical runs and results, `task-comparisons.csv`, `outcome-disagreements.csv` (all 33 flips)
- `tasks.json` (prompts, references, negative controls), `scoring.json`, `schedule.json` (every seed)
- model, runtime, and hardware manifests, plus `validate.py` (checks counts, seed parity, totals)
- the chart and derived-stat scripts used in this article

**Pinned artifacts:**

- Nemotron GGUF: `nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF` @ `e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246`, SHA-256 `91d63363e782c8a3d5f4be42816eba8e0d42dd2530bd07a7d0d2dc440599af75`
- Qwen GGUF: `Abiray/Qwen3.8-27B-Q4_K_M-GGUF` @ `f7a1cda580fe828415151042bf9f3dc5bb8b0d76`, SHA-256 `6a96cc760fc65cc6b9ea7f1922e3ff8b2a48c09f209456f23bbae9ef7032c867` (upstream `Qwen/Qwen3.8-27B` @ `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`)
- llama.cpp `620d2225cc436ab0b001e3200e590e3b286ef9ab`
- Python 3.12.3, PyTorch 2.9.1+cu128, CUDA 12.8.93

If you rerun this on your own card, we'd love to see the numbers, especially on a 4090 or with a bigger per-turn token cap.

## Sources

- [NVIDIA RTX Spark launch post for Nemotron 3.5 Bolt 24GB, with the Intelligence vs Speed chart](https://x.com/NVIDIARTXSpark/status/2110813633697694003)
- [NVIDIA Nemotron 3.5 Bolt 74B-A9B 24GB GGUF (pinned revision)](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF/tree/e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246)
- [Qwen3.8-27B upstream (pinned revision)](https://huggingface.co/Qwen/Qwen3.8-27B/tree/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0)
- [Qwen3.8-27B Q4_K_M GGUF conversion (pinned revision)](https://huggingface.co/Abiray/Qwen3.8-27B-Q4_K_M-GGUF/tree/f7a1cda580fe828415151042bf9f3dc5bb8b0d76)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [NVIDIA CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html)
