# Number audit for README.md and RESULTS.md

Every numeric token on each listed document line is covered by the cited evidence. JSONL lines include run configuration and measured values, including the raw repetition arrays. Resource CSV citations point to the row or rows containing the sampled peak. RSS values are converted from the cited `/usr/bin/time -v` line. Percent differences are calculated from the cited PPL results and AtomicChat reference.

## README.md

| README line | Numbers covered | Source file and line |
| ---: | --- | --- |
| 1 | Recipe 005, model 1.5-122B, one RTX 3090 | `receipts/recipe_identity.txt:1`; `receipts/model_source.txt:2`; `receipts/gpu.txt:2` |
| 3 | 32K Q4/Q3 prefill and decode; task scores; both PPL results and reference | `logs/depth_q4.jsonl:3-4`; `logs/depth_q3.jsonl:3-4`; `logs/score_q4_base.log:21`; `logs/score_q3_base.log:21`; `logs/ppl_q4.log:30`; `logs/ppl_q3.log:30`; `logs/atomicchat_reference.txt:2` |
| 5 | Pod GPU, CPU, RAM, region, rate, total cost and hours | `receipts/pod_details.txt:2-4`; `receipts/gpu.txt:2`; `receipts/cpu.txt:8`; `receipts/ram_limit.txt:1`; `receipts/T.txt:1`; `receipts/cost_calculation.txt:2-6` |
| 9, 11-12 | Recipe-card host/GPU tiers, MoE layers, threads, context, decode rates | `receipts/pod_details.txt:6`; `receipts/gpu.txt:2`; `logs/depth_q3.jsonl:3-4`; `logs/depth_q4.jsonl:3-4`; `logs/depth_q3.time:10`; `logs/depth_q4.time:10` |
| 14 | Q3 PPL peak RSS, 64 GB target, 125 GB allocation | `logs/ppl_q3.time:10`; `receipts/pod_details.txt:3,6`; `receipts/ram_limit.txt:1` |
| 18 | Model name and parameter count | `receipts/model_source.txt:2-4`; `logs/depth_q3.jsonl:1`; `logs/depth_q4.jsonl:1` |
| 19 | Unsloth revision and six shards | `receipts/unsloth_rev.txt:1`; `receipts/hash_check.txt:1-3`; `receipts/actual_sha256.txt:1-6` |
| 20 | llama.cpp tag and commit | `receipts/llama_commit.txt:1` |
| 21 | AtomicChat dataset revision | `receipts/atomicchat_dataset_revision.txt:1` |
| 23 | SHA256 digest algorithm heading | `receipts/hash_check.txt:1-3`; `receipts/expected_sha256.txt:1-6`; `receipts/actual_sha256.txt:1-6` |
| 25-30 | Shard ordinals and SHA256 values | `receipts/expected_sha256.txt:1-6`; `receipts/actual_sha256.txt:1-6` |
| 34 | Build tag and load-mode adaptation | `receipts/llama_commit.txt:1`; `logs/bench_flag_adaptation.txt:1-2`; `logs/bench_help.txt:1` |
| 36 | GPU and host RAM targets, Q3 card | `receipts/pod_details.txt:6`; `receipts/gpu.txt:2` |
| 39-40 | Q3 model name, GPU layers, CPU MoE layers, context, threads, port | `logs/depth_q3.jsonl:3-4`; `logs/server_q3_base.log:25-29`; `scripts/q3_base.sh:6` |
| 43 | GPU and host RAM targets, Q4 card | `receipts/pod_details.txt:6`; `receipts/gpu.txt:2` |
| 46-47 | Q4 model name, GPU layers, CPU MoE layers, context, threads, port | `logs/depth_q4.jsonl:3-4`; `logs/server_q4_base.log:26-30`; `scripts/q4_tasks.sh:7,18` |
| 50 | Q4 PPL context, chunks, GPU layers, CPU MoE layers, threads | `logs/ppl_q4_retry.time:1`; `logs/ppl_q4.log:22,27,30` |
| 54 | 32K labels for the summary results table | `logs/depth_q4.jsonl:3-4`; `logs/depth_q3.jsonl:3-4` |
| 56-57 | Q4/Q3 32K prefill, decode, PPL and scores | `logs/depth_q4.jsonl:3-4`; `logs/depth_q3.jsonl:3-4`; `logs/ppl_q4.log:30`; `logs/ppl_q3.log:30`; `logs/score_q4_base.log:21`; `logs/score_q3_base.log:21` |
| 63 | Runbook step references, failed Q3 ncmoe, core timestamp | `receipts/core_crash.txt:3-11`; `logs/sweep_ncmoe_q3_32.time:1-6`; `logs/sweep_ncmoe_q3_32.exit_code:1` |
| 64 | First-pass and rerun Q4 prefill values | `logs/sweep_ncmoe_q4_firstpass.txt:3`; `logs/sweep_ncmoe_q4.jsonl:1`; `logs/notes.md:1,3-10` |
| 65 | Host-visible CPUs, cgroup quota, allocated threads, default and explicit-thread rates | `receipts/nproc.txt:1-3`; `receipts/T.txt:1`; `logs/threads_default_q4.jsonl:1-2`; `logs/sweep_threads_q4.jsonl:9-10`; `logs/notes.md:25-26` |
| 66 | Q4 depth, MoE setting, repetition count, Q4 OOM configuration | `logs/depth128k_q4_B40.jsonl:1-2`; `logs/depth128k_q4_B40.time:1,10`; `logs/depth128k_q4_oom.txt:1`; `logs/sweep_ncmoe_q4_oom.txt:1` |
| 67 | MTP CPU MoE setting, draft/accepted counts, task decode rate | `receipts/mtp_succeeded.txt:1`; `logs/tasks_q4_mtp.jsonl:1-20`; `logs/score_q4_mtp_B42.log:21` |
| 68 | Exact-match item count and memory bandwidth | `logs/score_q4_base.log:21`; `logs/score_q3_base.log:21`; `receipts/ram_bw.txt:18-20` |
| 72 | Model version, Unsloth revision, llama.cpp tag/commit, AtomicChat reference and build tip | `receipts/model_source.txt:2-3`; `receipts/unsloth_rev.txt:1`; `receipts/llama_commit.txt:1`; `logs/atomicchat_reference.txt:2-5` |

## RESULTS.md

| RESULTS line | Numbers covered | Source file and line |
| ---: | --- | --- |
| 1 | Recipe identifier 005 | `receipts/recipe_identity.txt:1` |
| 5 | Q4 chosen MoE/thread settings and 32K rates | `logs/depth_q4.jsonl:3-4`; `logs/sweep_threads_q4.jsonl:3-4` |
| 6 | Q3 chosen MoE/thread settings and 32K rates | `logs/depth_q3.jsonl:3-4` |
| 7 | Task scores, MTP setting, drafted and accepted counts | `logs/score_q4_base.log:21`; `logs/score_q3_base.log:21`; `logs/score_q4_mtp_B42.log:21`; `logs/tasks_q4_mtp.jsonl:1-20` |
| 8 | PPL values, reference, percentage differences | `logs/ppl_q4.log:30`; `logs/ppl_q3.log:30`; `logs/atomicchat_reference.txt:2` |
| 9 | Q4 depth used for the stop-rule observation | `logs/depth_q4.jsonl:3-4` |
| 13 | Three repetitions and conversion method; HTTP load time method | `logs/sweep_ncmoe_q4.time:1`; `logs/depth_q4.time:1`; `logs/sweep_ncmoe_q3_36.time:1`; JSONL sample arrays cited below; `logs/load_time_q3.txt:1`; `logs/load_time_q4.txt:1` |
| 17 | Q4 ncmoe 49, 32 threads, depth, rates, sampled VRAM/RAM, load time | `logs/sweep_ncmoe_q4.jsonl:1-2`; `logs/vram_sweep_ncmoe_q4.csv:909-916`; `logs/sweep_ncmoe_q4.time:10`; `logs/load_time_q4.txt:1` |
| 18 | Q4 ncmoe 45 row | `logs/sweep_ncmoe_q4.jsonl:3-4`; `logs/vram_sweep_ncmoe_q4.csv:909-916`; `logs/sweep_ncmoe_q4.time:10`; `logs/load_time_q4.txt:1` |
| 19 | Q4 ncmoe 41 row | `logs/sweep_ncmoe_q4.jsonl:5-6`; `logs/vram_sweep_ncmoe_q4.csv:909-916`; `logs/sweep_ncmoe_q4.time:10`; `logs/load_time_q4.txt:1` |
| 20 | Q4 ncmoe 38 row | `logs/sweep_ncmoe_q4.jsonl:7-8`; `logs/vram_sweep_ncmoe_q4.csv:909-916`; `logs/sweep_ncmoe_q4.time:10`; `logs/load_time_q4.txt:1` |
| 21 | Q4 ncmoe 35 OOM | `logs/sweep_ncmoe_q4_oom.txt:1` |
| 22-24 | Q4 MoE/thread/depth settings and rates | `logs/depth_q4.jsonl:1-6`; `logs/vram_depth_q4.csv:587-588`; `logs/depth_q4.time:10`; `logs/load_time_q4.txt:1` |
| 25 | Q4 128K retry settings and rates, VRAM/RAM, load time | `logs/depth128k_q4_B40.jsonl:1-2`; `logs/vram_depth128k_q4_B40.csv:130-137`; `logs/depth128k_q4_B40.time:1,10`; `logs/load_time_q4.txt:1`; `logs/depth128k_q4_oom.txt:1` |
| 26 | Q3 ncmoe 49 row | `logs/sweep_ncmoe_q3_49.jsonl:1-2`; `logs/vram_sweep_ncmoe_q3_49.csv:145-152`; `logs/sweep_ncmoe_q3_49.time:10`; `logs/load_time_q3.txt:1` |
| 27 | Q3 ncmoe 44 row | `logs/sweep_ncmoe_q3_44.jsonl:1-2`; `logs/vram_sweep_ncmoe_q3_44.csv:132-139`; `logs/sweep_ncmoe_q3_44.time:10`; `logs/load_time_q3.txt:1` |
| 28 | Q3 ncmoe 40 row | `logs/sweep_ncmoe_q3_40.jsonl:1-2`; `logs/vram_sweep_ncmoe_q3_40.csv:123-130`; `logs/sweep_ncmoe_q3_40.time:10`; `logs/load_time_q3.txt:1` |
| 29 | Q3 ncmoe 36 row | `logs/sweep_ncmoe_q3_36.jsonl:1-2`; `logs/vram_sweep_ncmoe_q3_36.csv:121-128`; `logs/sweep_ncmoe_q3_36.time:10`; `logs/load_time_q3.txt:1` |
| 30 | Q3 ncmoe 32 OOM configuration only; no resource values remain | `receipts/core_crash.txt:3-11`; `logs/sweep_ncmoe_q3_32.time:1-6`; `logs/sweep_ncmoe_q3_32.stderr:1-5`; `logs/sweep_ncmoe_q3_32.exit_code:1` |
| 31-33 | Q3 depth, MoE/thread settings and rates | `logs/depth_q3.jsonl:1-6`; `logs/vram_depth_q3.csv:454-461`; `logs/depth_q3.time:10`; `logs/load_time_q3.txt:1` |
| 35 | Sweep/depth markers, 128K OOM size and retry, Q3 crash step | `logs/depth128k_q4_oom.txt:1`; `logs/depth128k_q4_B40.time:1`; `receipts/core_crash.txt:3-11` |
| 37 | Numeric labels in source-log filenames | Corresponding Q4/Q3 JSONL, VRAM CSV and `.time` source lines listed for table rows above |
| 39 | First-pass/rerun discrepancy and measured settings | `logs/sweep_ncmoe_q4_firstpass.txt:3`; `logs/sweep_ncmoe_q4.jsonl:1`; `logs/notes.md:3-10` |
| 41 | Thread sweep section label | `logs/sweep_threads_q4.time:1` |
| 45 | Q4 8-thread row | `logs/sweep_threads_q4.jsonl:1-2`; `logs/vram_sweep_threads_q4.csv:133-140`; `logs/sweep_threads_q4.time:10` |
| 46 | Q4 16-thread row | `logs/sweep_threads_q4.jsonl:3-4`; same VRAM and RSS aggregate sources as line 45 |
| 47 | Q4 24-thread row | `logs/sweep_threads_q4.jsonl:5-6`; same aggregate sources as line 45 |
| 48 | Q4 30-thread row | `logs/sweep_threads_q4.jsonl:7-8`; same aggregate sources as line 45 |
| 49 | Q4 32-thread row | `logs/sweep_threads_q4.jsonl:9-10`; same aggregate sources as line 45 |
| 50 | Default 128-thread row | `logs/threads_default_q4.jsonl:1-2`; `logs/vram_threads_default_q4.csv:175-182`; `logs/threads_default_q4.time:10` |
| 52 | Visible CPU count, cgroup quota, allocation and default threads | `receipts/nproc.txt:1-3`; `receipts/T.txt:1`; `logs/threads_default_q4.jsonl:1-2`; `logs/notes.md:25-26` |
| 58 | Q4 base settings, score and median decode | `logs/depth_q4.jsonl:3-4`; `logs/score_q4_base.log:21` |
| 59 | Q4 MTP settings, score, rate, drafts and accepts | `receipts/mtp_succeeded.txt:1`; `logs/server_q4_mtp_B42.log:6,8,11`; `logs/score_q4_mtp_B42.log:21`; `logs/tasks_q4_mtp.jsonl:1-20` |
| 60 | Q3 base settings, score and median decode | `logs/depth_q3.jsonl:3-4`; `logs/score_q3_base.log:21` |
| 62 | Task IDs and expected/given strings for both quants; MTP OOM configurations/context/port | `logs/tasks_q4_base.jsonl:6,20`; `logs/tasks_q3_base.jsonl:6,20`; `logs/notes.md:15-17`; `receipts/mtp_succeeded.txt:1`; `logs/server_q4_mtp_B42.log:8,11` |
| 66-67 | Q4/Q3 PPL, AtomicChat reference and calculated percentages | `logs/ppl_q4.log:30`; `logs/ppl_q3.log:30`; `logs/atomicchat_reference.txt:2` |
| 69 | Dataset revision, Q4 OOM and successful chunk count | `receipts/atomicchat_dataset_revision.txt:1`; `logs/ppl_q4_lmnone_oom.log:22-26`; `logs/ppl_q4.log:27,30`; `logs/ppl_q3.log:27,30` |
| 73 | Hardware, cost, bandwidth and sysbench block/thread settings | `receipts/pod_details.txt:2-4`; `receipts/gpu.txt:2`; `receipts/cpu.txt:8`; `receipts/ram_limit.txt:1`; `receipts/T.txt:1`; `receipts/cost_calculation.txt:2-6`; `receipts/ram_bw.txt:18-20` |
| 75 | llama.cpp tag and commit | `receipts/llama_commit.txt:1` |
| 76 | Unsloth revision | `receipts/unsloth_rev.txt:1` |
| 77 | Ornith model version and license | `receipts/model_source.txt:2-3`; `logs/depth_q3.jsonl:1`; `logs/depth_q4.jsonl:1` |
| 78 | AtomicChat reference, tested build tip and flag | `logs/atomicchat_reference.txt:2-5` |
| 79 | Six shards and hash audit | `receipts/hash_check.txt:1-3`; `receipts/actual_sha256.txt:1-6`; `receipts/expected_sha256.txt:1-6` |
