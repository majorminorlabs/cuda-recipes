# Data schema

## load-results.csv
One row per model × attempted `--ctx-size` (grid sizes plus ceiling-search attempts). Measures what the server window costs.

| Column | Meaning |
|---|---|
| model | `nemotron` or `qwen` |
| ctx_size | `--ctx-size` value (never above the model's native maximum, 262,144) |
| loaded_full_gpu | `1` only if llama-server `/health` returned 200 and every layer is on CUDA |
| layers_on_cuda, layers_total | from the llama.cpp layer-placement log line |
| model_buffer_mib | `CUDA0 model buffer size` from the real allocation pass |
| kv_buffer_mib | sum of `CUDA0 KV buffer size` lines in the real allocation pass (attention-layer KV cache) |
| rs_buffer_mib | sum of `CUDA0 RS buffer size` lines in the real allocation pass (recurrent state for Mamba-2 / DeltaNet layers); blank if not logged |
| compute_buffer_mib | sum of `CUDA0 compute buffer size` lines in the real allocation pass |
| cpu_mapped_mib | `CPU_Mapped model buffer size` from the real allocation pass (the mmap'd file, not offload) |

llama.cpp emits a dry-run fit pass before real allocation. Ignore all diagnostics before the first non-zero `CUDA0 model buffer size` line; parse only that line and subsequent real-pass diagnostics. This avoids counting dry-run RS and compute estimates twice. If a failed attempt never logs a field in its real pass, leave that CSV field blank and explain the missing real-allocation diagnostic in `error`.
| peak_vram_load_mib | nvidia-smi peak from launch until `/health` = 200 |
| is_ceiling | `1` for the largest context that loaded fully on GPU for that model |
| error | short reason when `loaded_full_gpu` is 0 |

## bench-results.csv
One row per model × fill depth × repetition. Measures how speed changes as the context fills. llama-bench sizes its own context to depth + prompt + generated tokens, so these rows are keyed by depth, not by server window.

| Column | Meaning |
|---|---|
| depth_tokens | tokens already in context before measuring (`-d`) |
| depth_label | `fixed` for the configured depths, `ceiling90` for round(0.9 × that model's ceiling) |
| repetition | 1..n (3 reps at depth 0, 1 rep at 64K and deeper) |
| prompt_tps | prompt-processing tokens/s for a 512-token prompt at that depth |
| decode_tps | generation tokens/s for 128 tokens at that depth |
| peak_vram_mib | nvidia-smi peak during that depth's own llama-bench invocation |
