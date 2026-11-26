# CUDA Recipes

I run reproducible inference tests on NVIDIA CUDA GPUs and publish the write-ups in [CUDA Recipes](https://majorminor.xyz/research/cuda-recipes).

Each folder is one study: the frozen task suite, validation scripts, sanitized trial results, environment records, charts, and a summary of findings.

| Study | Question | Headline |
|---|---|---|
| [010-qwen3.8-27b-lora](010-qwen3.8-27b-lora/) | Does applying a coding-agent LoRA improve Qwen3.8-27B on an RTX 3090? | Fresh paired run: 87/120 vs 82/120 strict passes; mean decode 15.4% lower. Adapter resident in both arms. |
| [011-rtx3070-moe-long-context](011-rtx3070-moe-long-context/) | Which MoE paths complete 64K/128K on an RTX 3070 8GB? | Uncapped Qwen llama.cpp decoded at 14.9/8.0 tok/s; strict quality was Qwen 37/60, Raon KRAFTON 36/60, Edge0 16/60. Runtime, model and RAM limits differ. |
| [008-inkling2-mini](008-inkling2-mini/) | How does Inkling 2 Mini run on a 24GB RTX 3090? | About 59 tok/s, with verified filled-context decode near 36.7 tok/s at 128K and 25 tok/s at 256K. 2026-11-24 update: the [DSpark drafter](008-inkling2-mini/dspark-3090/) raised fixed-length greedy decode 1.10x on Unsloth's build with the default 0.50 GB drafter file and 1.33x on mainline llama.cpp at 128 tokens, each against its own no-drafter arm; some prompts slowed. |
| [009-ternary-bonsai-25-27b](009-ternary-bonsai-25-27b/) | How does ternary Bonsai 2.5 27B compare with Qwen3.8 27B on one RTX 3090? | Bonsai PTQ1_0 plain reached 94.536232 tok/s in tg128 and scored 81/120 strict tasks; MTP scored 79/120, against the reused Qwen baseline at 89/120. |
| [006-edge0-145b](006-edge0-145b/) | How fast does Edge0-145B Q3_K run on one RTX 3090? | 48.6 tok/s median chat decode, 23,929 MiB peak VRAM, and 87.4 GiB peak host RAM in timed trials. |
| [004-small-card-offload](004-small-card-offload/) | How does Bolt run with 8–16GB of VRAM when experts are offloaded to CPU RAM? | Fits 128K at capped 8/12/16GB; offloaded decode is CPU-bound and host-load-sensitive. |
| [001-24gb-compression](001-24gb-compression/) | Does a native 2-bit 74B mixture-of-experts model outperform a 27B Q4_K_M model on one 24GB card? | Nemotron decoded about 2x faster but wrote about 1.5x more tokens per task, so median time to a finished task was a tie. Qwen passed more strict tasks on both GPUs, and the gap was concentrated in tool calling. |
| [002-context-ceiling](002-context-ceiling/) | How much context fits on a 24GB RTX 3090, and what does it cost in speed? | pending |
| [003-context-quality](003-context-quality/) | Long context on a 3090: code holds up, prose falls apart, and none of them can count. | Across Moby-Dick and Django, all three models found a single fact in 128K most of the time; four-fact retrieval and code tracing held up better in code, while counting was weak in both arms. |

## How these are run

Each study records pinned model artifacts, runtime and hardware manifests, frozen tasks and seeds, deterministic scoring, and trial-level results. Each study's README explains its setup and verification commands.

## License

Code: MIT. Results and data: CC BY 4.0. Model and runtime license notices are in [NOTICE.md](NOTICE.md).

Tier 1 evidence added after the tagged release (2026-10-20): [source, protocols, historical audits and small run records](supplements/tier1-20261020/README.md).

Plans, handoffs and drafts live in a local _private/ folder that is never published.

Before committing, enable the publication checks with `git config core.hooksPath .githooks`. See [CONTRIBUTING.md](CONTRIBUTING.md).
