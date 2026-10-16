# CUDA Recipes

Reproducible inference tests on NVIDIA CUDA GPUs, by MAJOR//MINOR.

Each folder is one study: the frozen task suite, validation scripts, sanitized trial results, environment records, charts, and a summary of findings.

| Study | Question | Headline |
|---|---|---|
| [001-24gb-compression](001-24gb-compression/) | Does a native 2-bit 74B mixture-of-experts model outperform a 27B Q4_K_M model on one 24GB card? | Nemotron fit fully on a 24GB RTX 3090 and decoded at 85.2 tok/s vs Qwen's 41.5, but Qwen passed more strict tasks on both GPUs. The gap was concentrated in tool calling. |

## How these are run

Each study records pinned model artifacts, runtime and hardware manifests, frozen tasks and seeds, deterministic scoring, and trial-level results. The [001 study](001-24gb-compression/README.md) explains its setup and verification commands.

## License

Code: MIT. Results and data: CC BY 4.0. Model and runtime license notices are in [NOTICE.md](NOTICE.md).
