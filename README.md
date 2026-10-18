# CUDA Recipes

Reproducible inference tests on NVIDIA CUDA GPUs, by MAJOR//MINOR.

Each folder is one study: the frozen task suite, validation scripts, sanitized trial results, environment records, charts, and a summary of findings.

| Study | Question | Headline |
|---|---|---|
| [004-small-card-offload](004-small-card-offload/) | How does Bolt run with 8–16GB of VRAM when experts are offloaded to CPU RAM? | Fits 128K at capped 8/12/16GB; offloaded decode is CPU-bound and host-load-sensitive. |
| [001-24gb-compression](001-24gb-compression/) | Does a native 2-bit 74B mixture-of-experts model outperform a 27B Q4_K_M model on one 24GB card? | Nemotron decoded about 2x faster but wrote about 1.5x more tokens per task, so median time to a finished task was a tie. Qwen passed more strict tasks on both GPUs, and the gap was concentrated in tool calling. |
| [002-context-ceiling](002-context-ceiling/) | How much context fits on a 24GB RTX 3090, and what does it cost in speed? | pending |
| [003-context-quality](003-context-quality/) | Long context on a 3090: code holds up, prose falls apart, and none of them can count. | Across Moby-Dick and Django, all three models found a single fact in 128K most of the time; four-fact retrieval and code tracing held up better in code, while counting was weak in both arms. |

## How these are run

Each study records pinned model artifacts, runtime and hardware manifests, frozen tasks and seeds, deterministic scoring, and trial-level results. Each study's README explains its setup and verification commands.

## License

Code: MIT. Results and data: CC BY 4.0. Model and runtime license notices are in [NOTICE.md](NOTICE.md).
