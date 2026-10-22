# Number audit for `ARTICLE_UPDATE_5090.md`

Every numeric claim in blocks A–D was checked against the listed local evidence before publication. Rounded article numbers retain the displayed units; computed ratios and totals are identified as calculations.

## Block A

| Claim | Source and trace |
| --- | --- |
| Update date, Oct 22 | `receipts/5090/end_time.txt` (`2026-10-22T02:50:28Z`); client date is also 2026-10-22. |
| Q4 decode 30.4 tok/s, approximately doubled | `RESULTS_5090.md`, Q4 32K row: 30.416 tok/s; `RESULTS.md`, Q4 32K row: 15.4985 tok/s. Ratio 30.416 / 15.4985 = 1.96×, rounded to “doubled.” |
| 64 GB-class RAM | `RESULTS_5090.md`, measured verdict: 57.74 GiB cgroup limit (`memory.max=61999996928` bytes); 32K server RSS 50.40 GiB Q4 and 30.23 GiB Q3. |
| RTX 5090 (32GB) heading | `receipts/5090/gpu.txt` records RTX 5090, 32607 MiB; user-provided RunPod Details in `receipts/5090/pod_details.txt` identifies one RTX 5090. |

## Block B

| Claim | Source and trace |
| --- | --- |
| One RTX 5090 32GB; 16 vCPUs; Xeon Gold 6530; 62 GB RAM; $1.22/hr | User-provided Details recorded in `receipts/5090/pod_details.txt`; GPU model/memory also in `receipts/5090/gpu.txt`. |
| About $1.64 total | `receipts/5090/cost.md`: uptime-derived estimate about 1.34 h × displayed $1.22/hr = about $1.64; screenshot clock is minute-resolution. |
| Extra 8 GB VRAM vs 3090 | `receipts/5090/gpu.txt` reports 32607 MiB (32GB-class); existing `RESULTS.md` / `README.md` report the 3090 as 24GB. Difference is 8GB by the stated nominal card capacities. |
| CPU expert layers: Q4 38→33; Q3 36→27 | Existing `RESULTS.md`, 3090 depth/offload recommendations; `RESULTS_5090.md`, recommended Q4 `ncmoe=33` and Q3 `ncmoe=27`. |
| Table values (Q4 3090: 548, 15.5, 55.1; Q4 5090: 563, 30.4, 46.5; Q3 3090: 311, 26.3, 38.6; Q3 5090: 889, 30.2, 26.4) | Existing `RESULTS.md`, 32K Q4/Q3 rows; `RESULTS_5090.md`, head-to-head 32K table. Article values are rounded from 548.030/15.4985/55.13, 562.714/30.416/46.54, 311.307/26.2562/38.55, and 888.585/30.241/26.36 respectively. |
| Median of three runs; task scores 18/20 | `RESULTS_5090.md`, throughput methodology and task table; raw `logs/5090/tasks_summary.jsonl` records each quant at 18/20. |
| RAM limit 57.74 GiB; Q4 50.40 GiB; Q3 30.23 GiB; no RAM-limit kills | `receipts/5090/memory.max.txt`, `ram_headroom.txt`; `RESULTS_5090.md`, 64 GB-class verdict and OOM summary. |
| 3090 Q4 peak 55.1 GiB | Existing `RESULTS.md`, Q4 32K/depth result: 55.13 GiB. |
| Memory bandwidth 136,718 MiB/s and 48,773 MiB/s; about 2.8× | `receipts/5090/sysbench_memory.txt`: 136718.19 MiB/sec; existing `RESULTS.md`: 48,773.25 MiB/s. 136718.19 / 48773.25 = 2.802, rounded to 2.8×. |
| Both quant decodes around 30 tok/s; Q3 prefill about 1.6× faster (889 vs 563) | `RESULTS_5090.md`, 32K head-to-head rows: Q4 30.416/562.714 and Q3 30.241/888.585 tok/s. 888.585 / 562.714 = 1.579, rounded to 1.6×. |
| PPL within 0.2% of BF16 | Existing `RESULTS.md`: Q4 5.7746 vs BF16 5.7625, +0.21%, rounded to 0.2%. |
| Q3 prefill at 36 and 27 CPU layers: 771 and 989 tok/s | `RESULTS_5090.md`, Q3 offload sweep: 770.929 at `ncmoe=36`; 989.172 at `ncmoe=27`, rounded. |
| Q4 prefill barely moved between cards | Existing `RESULTS.md` Q4 32K: 548.030; `RESULTS_5090.md` Q4 32K: 562.714. |
| Q4 at 128K, `ncmoe=33` CUDA OOM; retry at 35; 483 prefill, 28.2 decode, 51.6 GiB RSS; one run | `RESULTS_5090.md`, Q4 context-depth table; raw `logs/5090/depth_q4_131072*` files. The successful retry was one repetition. |
| Q3 at 27 CPU layers CUDA OOM at 64K | `RESULTS_5090.md`, Q3 context-depth table (`depth=65,536`, `ncmoe=27`, failure type CUDA OOM). |
| Three 32K Q4 invocations, at least 10 minutes apart; decode 28.2/29.7/30.4 and prefill 562.7–564.0 | `RESULTS_5090.md`, Q4 variance table; `logs/5090/variance_q4_schedule.txt` and each JSONL `test_time`. First invocation 01:58:29Z, second 02:21:19Z, third 02:33:54Z. |
| 3090 decode spread 12–22 tok/s | Existing `RESULTS.md`, Q4 repeated runs: 12.2471–21.6680 tok/s, rounded to whole tok/s. |
| Default thread count 64; 6.6 tok/s; `-t 14`; 13.6 CPU-equivalents | `RESULTS_5090.md`, Q4 thread sweep (default picked 64 and decoded at 6.6321); `receipts/5090/cpu.max.txt` and `T_derivation.txt` (quota 13.6, rounded T=14). |
| Q3 quality within 1%; Q3 RAM about 30 GiB; Q4 RAM tight on 3090 | Existing `RESULTS.md`: Q3 PPL +1.19%, Q4 PPL +0.21%, Q4 55.13 GiB on the 125 GB pod; `RESULTS_5090.md`: Q3 server RSS 30.23 GiB. |

## Block C

| Claim | Source and trace |
| --- | --- |
| 32GB GPU + 64 GB RAM; Q4 `--n-cpu-moe 33`; Q3 `--n-cpu-moe 27`; `-c 32768`; `-t 14` | `RESULTS_5090.md`, Recipe card table and measured server runs; `receipts/5090/T.txt` and `T_derivation.txt`. |
| Q4 128K uses `--n-cpu-moe 35` | `RESULTS_5090.md`, Q4 131,072 context retry at `ncmoe=35` completed. |

## Block D

| Claim | Source and trace |
| --- | --- |
| 64 GB recommendation was unverified on 3090; 3090 Q4 peak 55.1 GiB | Existing `RESULTS.md` and `README.md` state 125 GB pod and 55.13 GiB measured RSS; original `ARTICLE.md` says the 64 GB claim was unverified. |
| RTX 5090 comparison host: Xeon Gold 6530, 14 threads; 3090 host: EPYC 7763, 16 threads | `receipts/5090/pod_details.txt`; `receipts/5090/T.txt`; existing `README.md`/`RESULTS.md` host line and 3090 Q4 configuration. |
| 2.8× RAM bandwidth | Same calculation and sources as Block B above. |
| 5090 cost row: about 1.34 h at $1.22/hr, about $1.64; combined total about $3.17 | `receipts/5090/cost.md` gives approximately 1.34 h / $1.64 from screenshot uptime; existing `README.md` gives 3090 total $1.53; $1.53 + $1.64 = $3.17. |

The site article JSON has a publication `date` but no separate modified-date field. The published date remains 2026-10-21; the new update line is dated Oct 22 per Block A. The site markdown renderer’s `slugify()` converts `Update: RTX 5090 (32GB)` to `update-rtx-5090-32gb`, matching Block A’s anchor.

Audit result: all numeric claims in blocks A–D trace to `RESULTS_5090.md`, `receipts/5090/`, or the existing `RESULTS.md` / `README.md`. No untraceable number found; publication may proceed.
