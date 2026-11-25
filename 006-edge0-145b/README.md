# CUDA Recipes 006 · Edge0-145B on one RTX 3090

Edge0-145B Q3_K reached **48.6 tok/s median chat decode** on one RTX 3090 24 GB. Timed trials peaked at **23,929 MiB VRAM** and **87.4 GiB host cgroup RAM**. One of three agent trials returned a valid tool call.

- [Illustrated article](https://majorminor.xyz/research/cuda-recipes-006)
- [Results and reproduction](results/edge0-145b-3090.md)
- [Exact requests and hashes](results/prompts/)
- [Per-trial evidence](receipts/trials.jsonl) and [memory summary](receipts/benchmark_summary.json)
- [Run cost](cost.md), $1.1893 billed
- [Streaming trial recorder](scripts/record_trial.py)

The model is distributed separately under the [Edge0 Community Model License and Qwen notice](https://huggingface.co/Edge0/Edge0-145B-q3k/tree/a19f88cc07d78047c273cdb88f3250f36c143999).
