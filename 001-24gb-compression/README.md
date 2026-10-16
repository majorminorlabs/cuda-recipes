# 24GB Compression Study

*CUDA Recipes 001 · MAJOR//MINOR*

## Question

On a single 24GB RTX 3090, how does NVIDIA's native 2-bit Nemotron 3.5 Bolt 74B-A9B GGUF compare with Qwen3.8 27B Q4_K_M? The same frozen suite was also run on an RTX 5090.

## Headline

Nemotron fit fully on the 3090 at 16K context and decoded about 2.05× faster, but Qwen passed more strict tasks on both GPUs. Across the two cards, the single-turn scores were close; the strict tool-calling gap favored Qwen. See [KEY_FINDINGS.md](KEY_FINDINGS.md) and [LIMITATIONS.md](LIMITATIONS.md) before interpreting the scores.

## Setup

- RTX 3090 (24GB, driver 580.126.20) and RTX 5090 (32GB, driver 570.195.03), one provider node each.
- llama.cpp commit `620d2225cc436ab0b001e3200e590e3b286ef9ab`, CUDA 12.8.93, Python 3.12.3, PyTorch 2.9.1+cu128.
- 16,384 context, Q8_0 key/value cache, one parallel slot, batch 512, ubatch 128, flash attention, Jinja templates, all layers on CUDA.
- Thinking on; temperature 1.0, top_p 0.95; top_k 40 for Nemotron and 20 for Qwen. Single-turn limit 2,048 tokens; tool-turn limit 512 tokens and six turns.
- Forty frozen tasks × three repetitions × two models × two GPUs = 480 scored trials. Both models received the same seed per task repetition.

The exact configuration, schedule, model and hardware manifests are in [DATA/](DATA/). [METHODOLOGY.md](METHODOLOGY.md) explains the design and scoring.

## Pinned artifacts

| Artifact | Revision | SHA-256 |
|---|---|---|
| [NVIDIA Nemotron 3.5 Bolt 74B-A9B 24GB GGUF](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF) | `e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246` | `91d63363e782c8a3d5f4be42816eba8e0d42dd2530bd07a7d0d2dc440599af75` |
| [Qwen3.8 27B Q4_K_M GGUF](https://huggingface.co/Abiray/Qwen3.8-27B-Q4_K_M-GGUF) | `f7a1cda580fe828415151042bf9f3dc5bb8b0d76` | `6a96cc760fc65cc6b9ea7f1922e3ff8b2a48c09f209456f23bbae9ef7032c867` |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | `620d2225cc436ab0b001e3200e590e3b286ef9ab` | Source revision |

## Results

| GPU | Model | Strict success | Decode tok/s | Peak VRAM (MiB) | Median trial time (s) |
|---|---|---:|---:|---:|---:|
| RTX 3090 | Nemotron | 75/120 (62.5%) | 85.2 | 21,339 | 5.68 |
| RTX 3090 | Qwen | 89/120 (74.2%) | 41.5 | 16,481 | 5.37 |
| RTX 5090 | Nemotron | 71/120 (59.2%) | 148.3 | 21,865 | 3.44 |
| RTX 5090 | Qwen | 84/120 (70.0%) | 72.5 | 16,514 | 3.47 |

Pooled single-turn strict success: Nemotron 108/156, Qwen 105/156. Pooled tool-calling strict success: Nemotron 38/84, Qwen 68/84. Throughput is the mean of per-trial decode rates. Trial time includes prompt processing, generation, and tool turns. See [RESULTS.md](RESULTS.md) and [CHARTS/](CHARTS/) for category scores, uncertainty intervals, latency and failure classes.

## Reproduce and inspect

From this study folder, with Python 3.12 or newer:

```sh
python3 validate.py
python3 scripts/derived_stats.py
python3 -m scorer.validate
python3 scripts/make_charts.py  # requires matplotlib
shasum -a 256 -c SHA256SUMS
```

`validate.py` checks trial and seed parity, totals and disagreements. `scripts/derived_stats.py` recomputes article statistics. `scorer/validate.py` is the frozen deterministic scoring logic; `scorer/tools.py` supplies simulated fixture tools, and `DATA/tasks.json` contains the frozen prompts, references, negative controls and expected calls. The scorer's positive, negative and malformed-response checks run with `python3 -m scorer.validate`.

To rerun inference, download the pinned GGUFs, build the pinned llama.cpp commit for your CUDA architecture, launch one model at a time with the flags in [METHODOLOGY.md](METHODOLOGY.md), and run the task/seed schedule in `DATA/schedule.json` through its OpenAI-compatible chat-completions API. Keep generated responses and any checkpoint database private. The original checkpointed inference runner is not part of this data release, so a fresh hardware run requires a client that implements the documented request, tool-turn, telemetry and scoring protocol. The commands above reproduce the published analysis from the released trial data.

## Limitations

This is a comparison of two specific GGUF files, not an isolated quantization experiment. The 40 tasks have strict contracts; coding uses an unstated restricted AST subset; simulated tool calls require exact traces; and the 512-token tool-turn cap may disadvantage verbose reasoning. The GPUs ran on different provider nodes with different drivers, and each model was run in a block. The public package omits raw responses. Read [LIMITATIONS.md](LIMITATIONS.md) for the full scope.

## Files

- `DATA/`: sanitized trial data, task suite, schedule, configurations and manifests.
- `CHARTS/`: figures 1–4 as SVG and PNG.
- `scripts/`: derived-stat and chart regeneration scripts.
- `scorer/`: frozen scoring logic and simulated fixture tools.
- `METHODOLOGY.md`, `RESULTS.md`, `KEY_FINDINGS.md`, `LIMITATIONS.md`, `SOURCES.md`: study notes for readers.
- `SHA256SUMS`: hashes of the released study files.

Model and runtime licenses are summarized in the repository's [NOTICE.md](../NOTICE.md). The [article](https://majorminor.xyz/research/cuda-recipes-001) presents the study in full.
