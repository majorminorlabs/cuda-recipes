# RTX 3090 results

Rates are llama-bench means in tokens per second. Sample standard deviations and sample arrays are reproduced from the captured JSON. Single-repetition results do not estimate variation.

## Primary measurements

| Artifact | Metric | Mean tok/s | Sample SD | Samples | Evidence |
|---|---|---:|---:|---|---|
| Base UD-Q4_K_M | pp512 | 1411.470954 | 6.338578 | 1404.27, 1413.96, 1416.19 | [base_bench_pp512_tg128.stdout.log.gz](evidence/rtx3090/base_bench_pp512_tg128.stdout.log.gz) |
| Base UD-Q4_K_M | tg128 | 59.106860 | 0.167931 | 59.3007, 59.0051, 59.0148 | [base_bench_pp512_tg128.stdout.log.gz](evidence/rtx3090/base_bench_pp512_tg128.stdout.log.gz) |
| Uncensored AD-Q4_K | pp512 | 1454.322674 | 8.866765 | 1444.1, 1458.92, 1459.95 | [uncensored_bench_pp512_tg128.stdout.log.gz](evidence/rtx3090/uncensored_bench_pp512_tg128.stdout.log.gz) |
| Uncensored AD-Q4_K | tg128 | 58.713510 | 0.172738 | 58.8914, 58.7027, 58.5464 | [uncensored_bench_pp512_tg128.stdout.log.gz](evidence/rtx3090/uncensored_bench_pp512_tg128.stdout.log.gz) |

## Decode with existing synthetic context

| Host | Artifact | Depth | Mean tok/s | Sample SD | Reps | KV | Batch / ubatch | Evidence |
|---|---|---:|---:|---:|---:|---|---|---|
| RTX 3090 / primary host | Base UD-Q4_K_M | 0 | 56.793065 | 3.234888 | 3 | f16/f16 | 2048/512 | [base_decode_depth0.stdout.log.gz](evidence/rtx3090/base_decode_depth0.stdout.log.gz) |
| RTX 3090 / primary host | Base UD-Q4_K_M | 8,192 | 55.898236 | 0.678655 | 3 | f16/f16 | 2048/512 | [base_decode_depth8k.stdout.log.gz](evidence/rtx3090/base_decode_depth8k.stdout.log.gz) |
| RTX 3090 / primary host | Uncensored AD-Q4_K | 0 | 57.349878 | 2.997235 | 3 | f16/f16 | 2048/512 | [uncensored_decode_depth0.stdout.log.gz](evidence/rtx3090/uncensored_decode_depth0.stdout.log.gz) |
| RTX 3090 / primary host | Uncensored AD-Q4_K | 8,192 | 55.811643 | 0.934872 | 3 | f16/f16 | 2048/512 | [uncensored_decode_depth8k.stdout.log.gz](evidence/rtx3090/uncensored_decode_depth8k.stdout.log.gz) |
| RTX 3090 / depth host | Base UD-Q4_K_M | 131,072 | 36.646339 | 0.000000 | 1 | f16/f16 | 256/128 | [base_decode_depth128k_f16_b256_ub128.stdout.json.gz](evidence/rtx3090-depth/base_decode_depth128k_f16_b256_ub128.stdout.json.gz) |
| RTX 3090 / depth host | Base UD-Q4_K_M | 262,144 | 24.842185 | 0.000000 | 1 | q8_0/q8_0 | 64/32 | [base_decode_depth256k_q8_b64_ub32.stdout.json.gz](evidence/rtx3090-depth/base_decode_depth256k_q8_b64_ub32.stdout.json.gz) |
| RTX 3090 / depth host | Uncensored AD-Q4_K | 131,072 | 36.685906 | 0.000000 | 1 | f16/f16 | 256/128 | [uncensored_decode_depth128k_f16_b256_ub128.stdout.json.gz](evidence/rtx3090-depth/uncensored_decode_depth128k_f16_b256_ub128.stdout.json.gz) |
| RTX 3090 / depth host | Uncensored AD-Q4_K | 262,144 | 25.018935 | 0.000000 | 1 | q8_0/q8_0 | 64/32 | [uncensored_decode_depth256k_q8_b64_ub32.stdout.json.gz](evidence/rtx3090-depth/uncensored_decode_depth256k_q8_b64_ub32.stdout.json.gz) |

The initial 128K depth attempts produced no result rows. The verified 128K/256K rerun used a separate RTX 3090 host and one repetition per setting. Cache precision and batch settings change with depth.

## Context allocation and short generation

The configured window was allocated and a short response requested. These checks do not score full-window recall.

| Artifact | Attempt | Outcome | Metadata / command | Output |
|---|---|---|---|---|
| Base UD-Q4_K_M | base_context128k_f16 | failed_oom | [base_context128k_f16.meta.txt.gz](evidence/rtx3090/base_context128k_f16.meta.txt.gz) | [base_context128k_f16.stdout.log.gz](evidence/rtx3090/base_context128k_f16.stdout.log.gz) |
| Base UD-Q4_K_M | base_context256k_f16 | failed_oom | [base_context256k_f16.meta.txt.gz](evidence/rtx3090/base_context256k_f16.meta.txt.gz) | [base_context256k_f16.stdout.log.gz](evidence/rtx3090/base_context256k_f16.stdout.log.gz) |
| Base UD-Q4_K_M | base_context256k_f8_e4m3 | failed_oom | [base_context256k_f8_e4m3.meta.txt.gz](evidence/rtx3090/base_context256k_f8_e4m3.meta.txt.gz) | [base_context256k_f8_e4m3.stdout.log.gz](evidence/rtx3090/base_context256k_f8_e4m3.stdout.log.gz) |
| Base UD-Q4_K_M | base_context256k_q8_0 | failed_oom | [base_context256k_q8_0.meta.txt.gz](evidence/rtx3090/base_context256k_q8_0.meta.txt.gz) | [base_context256k_q8_0.stdout.log.gz](evidence/rtx3090/base_context256k_q8_0.stdout.log.gz) |
| Base UD-Q4_K_M | base_tuned_context131072_f16_b256_ub128 | passed | [base_tuned_context131072_f16_b256_ub128.meta.txt.gz](evidence/rtx3090/base_tuned_context131072_f16_b256_ub128.meta.txt.gz) | [base_tuned_context131072_f16_b256_ub128.stdout.log.gz](evidence/rtx3090/base_tuned_context131072_f16_b256_ub128.stdout.log.gz) |
| Base UD-Q4_K_M | base_tuned_context262144_q8_0_b256_ub128 | failed_oom | [base_tuned_context262144_q8_0_b256_ub128.meta.txt.gz](evidence/rtx3090/base_tuned_context262144_q8_0_b256_ub128.meta.txt.gz) | [base_tuned_context262144_q8_0_b256_ub128.stdout.log.gz](evidence/rtx3090/base_tuned_context262144_q8_0_b256_ub128.stdout.log.gz) |
| Base UD-Q4_K_M | base_tuned_context262144_q8_0_b64_ub32 | passed | [base_tuned_context262144_q8_0_b64_ub32.meta.txt.gz](evidence/rtx3090/base_tuned_context262144_q8_0_b64_ub32.meta.txt.gz) | [base_tuned_context262144_q8_0_b64_ub32.stdout.log.gz](evidence/rtx3090/base_tuned_context262144_q8_0_b64_ub32.stdout.log.gz) |
| Uncensored AD-Q4_K | uncensored_context128k_f16 | failed_oom | [uncensored_context128k_f16.meta.txt.gz](evidence/rtx3090/uncensored_context128k_f16.meta.txt.gz) | [uncensored_context128k_f16.stdout.log.gz](evidence/rtx3090/uncensored_context128k_f16.stdout.log.gz) |
| Uncensored AD-Q4_K | uncensored_context256k_f16 | failed_oom | [uncensored_context256k_f16.meta.txt.gz](evidence/rtx3090/uncensored_context256k_f16.meta.txt.gz) | [uncensored_context256k_f16.stdout.log.gz](evidence/rtx3090/uncensored_context256k_f16.stdout.log.gz) |
| Uncensored AD-Q4_K | uncensored_context256k_f8_e4m3 | failed_oom | [uncensored_context256k_f8_e4m3.meta.txt.gz](evidence/rtx3090/uncensored_context256k_f8_e4m3.meta.txt.gz) | [uncensored_context256k_f8_e4m3.stdout.log.gz](evidence/rtx3090/uncensored_context256k_f8_e4m3.stdout.log.gz) |
| Uncensored AD-Q4_K | uncensored_context256k_q8_0 | failed_oom | [uncensored_context256k_q8_0.meta.txt.gz](evidence/rtx3090/uncensored_context256k_q8_0.meta.txt.gz) | [uncensored_context256k_q8_0.stdout.log.gz](evidence/rtx3090/uncensored_context256k_q8_0.stdout.log.gz) |
| Uncensored AD-Q4_K | uncensored_tuned_context131072_f16_b256_ub128 | passed | [uncensored_tuned_context131072_f16_b256_ub128.meta.txt.gz](evidence/rtx3090/uncensored_tuned_context131072_f16_b256_ub128.meta.txt.gz) | [uncensored_tuned_context131072_f16_b256_ub128.stdout.log.gz](evidence/rtx3090/uncensored_tuned_context131072_f16_b256_ub128.stdout.log.gz) |
| Uncensored AD-Q4_K | uncensored_tuned_context262144_q8_0_b256_ub128 | failed_oom | [uncensored_tuned_context262144_q8_0_b256_ub128.meta.txt.gz](evidence/rtx3090/uncensored_tuned_context262144_q8_0_b256_ub128.meta.txt.gz) | [uncensored_tuned_context262144_q8_0_b256_ub128.stdout.log.gz](evidence/rtx3090/uncensored_tuned_context262144_q8_0_b256_ub128.stdout.log.gz) |
| Uncensored AD-Q4_K | uncensored_tuned_context262144_q8_0_b64_ub32 | passed | [uncensored_tuned_context262144_q8_0_b64_ub32.meta.txt.gz](evidence/rtx3090/uncensored_tuned_context262144_q8_0_b64_ub32.meta.txt.gz) | [uncensored_tuned_context262144_q8_0_b64_ub32.stdout.log.gz](evidence/rtx3090/uncensored_tuned_context262144_q8_0_b64_ub32.stdout.log.gz) |

See [FAILURES.md](FAILURES.md) for failed allocations, changed settings and the lost-pod correction. Full row settings are in [results.json](results.json); expanded invocations are in [COMMANDS.md](COMMANDS.md).
