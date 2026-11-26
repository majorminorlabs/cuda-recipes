# CUDA Recipes 010: Qwen3.8-27B coding-agent LoRA on RTX 3090

A fresh paired run of 40 tasks × 3 repetitions per arm. Base passed 82/120 (68.3%); the merged coding-agent adapter passed 87/120 (72.5%). Mean decode fell from 37.83 to 32.00 tok/s (15.4%).

The adapter stayed resident in both arms; scale 0 defined base, scale 1 defined adapter. This is a comparison of applying the adapter, not of memory with the adapter unloaded.

- [Results, setup, model pins and credits](RESULTS.md)
- [Effective configuration](config.json)
- [Trial data](DATA/trials.csv), [summary](DATA/summary.json), and [per-trial evidence](evidence/)
- [Frozen tasks, scorer, runner and paired schedule](suite/)
- [Verification](verify.py)

Run `python3 verify.py` from this directory. It checks all 240 trial assignments against the schedule, recomputes scores and summary metrics, and verifies published file hashes. No GPU or network is required.

To repeat inference, build llama.cpp at the commit pinned in RESULTS.md and download the pinned GGUF base and LoRA artifacts. Start the server with the flags in COMMANDS.md, then run the suite. A fresh run requires a CUDA GPU and incurs compute costs.

The inherited runner writes `both` in the SQLite model column during paired mode. Published trial data derives the correct arm from the trial ID and cross-checks it against each raw assignment. The inherited common configuration had older output caps; config.json records the effective 4096/1024 caps in the executed runner. Neither issue changes observed scores.

Original operational archives are retained privately. Public evidence omits server request IDs and machine-specific database paths. Task inputs, scorer, schedule, outputs and model pins are preserved. Code is MIT; results and data are CC BY 4.0 under the repository licenses. Model and adapter licenses remain upstream.
