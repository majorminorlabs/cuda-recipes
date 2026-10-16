# Results

## Context fit

| Model | Largest full-GPU context | Peak VRAM at ceiling | Card headroom |
|---|---:|---:|---:|
| Nemotron | 262,144 (native maximum) | 22,366 MiB | 2,210 MiB |
| Qwen | 221,184 | 23,794 MiB | 782 MiB |

Qwen passed at 221,184 and failed at 229,376, bracketing its largest multiple-of-8,192 ceiling. Nemotron loaded at its native maximum. All successful windows placed every layer on CUDA. The full load table, including buffer breakdown and failed attempts, is [DATA/load-results.csv](DATA/load-results.csv).

![KV cache size vs context](CHARTS/fig4-kv-cache-context.svg)

## Speed by synthetic fill depth

Values are tok/s. Depth zero shows three independent repetitions as a min–max range; each deeper point is one run.

| Model | Fill depth | Prompt tok/s | Decode tok/s | Runs |
|---|---:|---:|---:|---:|
| Nemotron | 0 | 792.1–849.2 (mean 821.9) | 86.0–87.0 (mean 86.6) | 3 |
| Nemotron | 65,536 | 733.0 | 65.2 | 1 |
| Nemotron | 131,072 | 671.5 | 52.2 | 1 |
| Nemotron | 235,930 (ceiling90) | 596.9 | 38.9 | 1 |
| Qwen | 0 | 1,169.7–1,275.7 (mean 1,236.9) | 42.1–42.4 (mean 42.3) | 3 |
| Qwen | 65,536 | 653.8 | 30.0 | 1 |
| Qwen | 131,072 | 449.8 | 23.3 | 1 |
| Qwen | 199,066 (ceiling90) | 335.8 | 18.6 | 1 |

![Decode speed by fill depth](CHARTS/fig2-decode-fill-depth.svg)

![Prompt processing by fill depth](CHARTS/fig3-prompt-fill-depth.svg)

## Allocation and sanity check

KV cache at 16K was 68.01 MiB for Nemotron and 544.00 MiB for Qwen (8×). Across successful rows, bytes/token were about 4,353 and 34,816 respectively. In successful loads, model + KV + RS + compute buffers sit 268.79–334.45 MiB below peak VRAM, consistent with CUDA context and other runtime allocations. Exact per-row residuals are in the validation report.

## Execution and cost

Pod start through termination was 0.867 GPU-hour. At RunPod's advertised RTX 3090 list rate of $0.50/hour, cost is **estimated** at $0.43.
