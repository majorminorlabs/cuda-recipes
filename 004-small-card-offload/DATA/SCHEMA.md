# CUDA Recipes 004 data schema

All CSVs have a header row. VRAM and RAM values are MiB. Speeds are tokens/s.

## hosts.json

Contains host snapshots `0` (calibration, load, PPL, and archived 128-thread rows; AMD EPYC 7H12, 31.13-vCPU quota), `A` (thread sweep and T=16 rep 1; AMD EPYC 7763, 31.13-vCPU quota), `B` (reps 2–3; AMD EPYC 7C13, 31.125-vCPU quota), and `C` (desktop-host thread sweep and three bench rounds; Intel Core i5-11600K, 6 cores/12 threads, 11.52-vCPU quota, one RTX 3090 on PCIe Gen4 x16). Host C had 64,125 MiB total RAM; module speed and channel details were unavailable. The model and Wikitext-2 SHA256 values are also recorded here.

## thread-sweep.csv

At 12GB/N=60 and depth 0, thread sweeps record prompt and decode speed. Host A rows use the original sweep; Host C tested the unique counts in `{4, 6, 8, 12, 16}` for two reps (6 physical cores and 12 visible threads). Select T by highest median decode speed. Columns: `host,rep,threads,pp_tok_s,tg_tok_s`.

## calibration.csv

One row per N tried while searching for each budget's offload setting. Calibration uses 128K context; if no N meets the 8GB target at 128K, repeat at 32K. Columns: `host,budget_gb,n_cpu_moe,ctx,loaded,peak_vram_mib,host_ram_peak_mib,chosen,notes`; these rows are host 0. Peak VRAM is measured during model load and short generation.

## load-results.csv

Host 0 load tests cover each chosen N at contexts 32768, 131072, and 262144. Host C adds 128K confirmation loads at each chosen N. Columns: `host,budget_gb,n_cpu_moe,ctx,loaded,peak_vram_mib,host_ram_peak_mib,error`.

## bench-results.csv

`llama-bench` used `-p 512 -n 128` and three repetitions per depth. The depth grid is 0/32768/65536/117964 at 128K; for a 32K fallback it is 0/16384/29491. Historical rep 1 rows use host A and reps 2–3 use host B. Host C uses T=6 and three rounds, each with the 16 cells in a seed-shuffled order. Columns: `budget_gb,n_cpu_moe,ctx,depth,fill_tokens,rep,host,n_threads,pp_tok_s,tg_tok_s,peak_vram_mib,round,probe_gbps`; `fill_tokens` equals `depth`. Host C rows populate `round` (same value as rep) and the 5-second RAM bandwidth `probe_gbps`; historical rows leave both blank.

## ppl-results.csv

Wikitext-2 test PPL at `-c 2048 --chunks 8 -fa on -ctk q8_0 -ctv q8_0`. CPU expert budgets use `--no-op-offload` (`op_offload=0`). Columns: `host,budget_gb,n_cpu_moe,ctx,chunks,op_offload,ppl,ppl_err`; these rows are host 0. The Wikitext file SHA256 is in `hosts.json`.
