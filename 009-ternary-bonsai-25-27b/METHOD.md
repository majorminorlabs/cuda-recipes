# Method

## Quality suite

The task set, scoring rules, common configuration, schedule seeds, and deterministic scorer are copied from study 001. Forty tasks were run three times for each Bonsai arm. The Qwen3.8 27B Q4_K_M quality result is reused from 001 and was not rerun; that baseline used llama.cpp commit `620d2225cc436ab0b001e3200e590e3b286ef9ab`.

Both Bonsai quality arms used the PrismML fork, context 16384, parallelism 1, batch 512, ubatch 128, Q8_0 K/V cache, all layers on GPU, Flash Attention, Jinja, and verbose server logging. Sampling used thinking mode, temperature 1.0, top_p 0.95, top_k 20, min_p 0, single-turn cap 2048, tool-turn cap 512, and six turns. Reasoning effort stayed at the model/server default (`xhigh`); no override was passed.

## Speed and context

Primary `llama-bench` rows used `-r 3 -p 512 -n 128 -ngl 99 -t 8 -b 2048 -ub 512 -ctk f16 -ctv f16 -fa auto -o json`. Qwen was benchmarked on each build used for a Bonsai speed column.

Filled-context decode used `-p 0 -n 128 --no-warmup -d DEPTH`. Bonsai 32K used F16 KV with batch/ubatch 2048/512; 128K used F16 with 256/128; 262K used Q8_0 with 64/32. Qwen used the same reduced 128K and 262K profiles; its 262K attempt failed allocation. Attempt records are retained in curated evidence.

For MTP server throughput, the PTQ1 MTP-head file was served against three fixed prompts with drafting off and with CUDA-default `--spec-type draft-mtp --spec-draft-n-min 0 --spec-draft-n-max 3 --spec-draft-p-min 0.1`. The separate cutoff check also measured p_min 0. No model responses are published.

## Statistics

Strict success is the number of trials that pass the frozen scorer. Latency reports the arithmetic mean, median, and linearly interpolated 95th percentile of per-trial completion time. Prompt and decode rates are arithmetic means of per-trial rates. `llama-bench` values and standard deviations are preserved as emitted. VRAM is the maximum sampled value recorded for each row or arm.
