# Phase 0 scripts and pod pre-flight

Every script reads `DATA/study-config.json`. The load and bench runners write exactly the columns in `DATA/SCHEMA.md`. Result rows are saved as work completes; private run-clock state and raw selected load-log lines go only under `_internal/`.

## First commands on a fresh pod

Run the hash check first to start the shared 0.9-GPU-hour clock. On a new pod, use `--reset-budget-window`; do not use that option again during the same run.

```sh
python3 scripts/verify_gguf.py --model-dir <GGUF_DIRECTORY> --reset-budget-window
python3 scripts/pod_preflight.py --model-dir <GGUF_DIRECTORY> --llama-source <LLAMA_CPP_SOURCE_DIRECTORY>
```

The pre-flight checks the llama.cpp source checkout against the configured commit, calls the pinned `llama-bench --help`, and confirms the advertised `-fa` spelling. It uses `on` when the help lists `on|off|auto`, and `1` if that is the supported spelling instead. Every bench JSON result is also checked for the configured build commit. Pre-flight then makes one 16,384-token anchor load for each model. `/health` must return HTTP 200; 503 and connection errors are treated as “still loading.” Those anchor rows are saved and reused by the full sweep, so pre-flight adds no duplicate load.

The anchor load is also the live log-format check. Its parser must match the layer-placement, model, KV, compute and `CPU_Mapped` buffer diagnostics before the full sweep proceeds. llama.cpp emits a dry-run fit pass before the real allocation; parsing uses the real allocation block associated with its first non-zero model buffer, so dry-run RS and compute values are excluded. RS lines are summed within that real pass and remain blank when absent. Filtered raw buffer and layer-placement lines for every attempt are retained only under `_internal/load-logs/`; inspect both model anchor files before proceeding if you want to verify the exact emitted text. If required strings do not match, the runner stops before attempting larger windows.

## Run order

After pre-flight:

```sh
python3 scripts/run_load_sweep.py --model-dir <GGUF_DIRECTORY>
python3 scripts/run_bench.py --model-dir <GGUF_DIRECTORY>
```

The load sweep proceeds by model and ascending context: 16,384 anchor, then configured sizes up to 262,144. It stops at the first failed full-GPU load, then binary-searches 8,192-token multiples between the highest passing context and that failure. It never probes above `native_ctx_max`; a passing 262,144 load is the ceiling. If the hard stop interrupts a model, completed rows remain saved and the incomplete ceiling is left unmarked.

The bench runner reads each model's marked ceiling from `load-results.csv`. It runs depth 0, 65,536 and 131,072 as eligible, then the models' `ceiling90` depths last. A depth is skipped when `depth + 512 + 128` exceeds that model's ceiling. Each depth has its own llama-bench invocation and VRAM sampler; repetitions are 3 at zero and 1 above zero. The hard-stop guard projects the next invocation and stops at 0.9 GPU-hour, or skips a `ceiling90` invocation when its projection crosses that limit. Completed bench rows are written after each invocation.

The shared clock starts with the first hash-check command and persists under `_internal/phase0-budget.json` across scripts. `sample_vram.py` is a standalone 0.4-second cadence sampler and also exits at the configured hard stop. Stop the rented pod after the scripts exit; the scripts cannot stop the provider instance itself.

## Completed-run package tools

After results have been copied locally, `python3 scripts/derived_stats.py` prints ceilings, VRAM headroom, KV bytes per token, speed retention from the depth-zero mean, and cross-model ratios. `python3 scripts/make_charts.py` regenerates the four SVG charts in `CHARTS/` using only Python standard-library code.

## Parser dry run

```sh
python3 scripts/dry_run_parsers.py
python3 validate.py
```

The dry run uses representative llama.cpp startup lines with repeated KV and RS buffers, a simulated `/health` 503 → 503 → 200 sequence, and per-repetition llama-bench JSON. It writes sample rows into a temporary scratch copy and runs that copy's `validate.py`; the real CSVs remain unchanged.
