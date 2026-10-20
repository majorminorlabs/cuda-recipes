Prefill discrepancy recorded during the run (not investigated per instruction): Q4 ncmoe=49, pp2048 was 218.96 ± 1.73 tok/s in the first-pass table (`sweep_ncmoe_q4_firstpass.txt`) and had raw samples 599.07, 620.82, 617.903 tok/s (median 617.903; mean 612.597634) in the rerun (`sweep_ncmoe_q4.jsonl`). The runs used the same recorded ncmoe, prompt size, thread count, flash attention, and load mode. The report will use the JSONL samples and show run-to-run spread.

Prefill settings comparison for ncmoe=49, pp2048 (no reruns):

| Source | n_threads | mmap / use_mmap | n_batch / n_ubatch | flash_attn | timestamp |
| --- | ---: | --- | --- | ---: | --- |
| `sweep_ncmoe_q4_firstpass.txt` | 32 (`-t 32` in launch command) | `lm=none` (`-lm none`, adapted from `-mmp 0`); `use_mmap` not emitted | 2048 / 512 (launch prompt size plus bench defaults) | 1 (`-fa on`) | Not recorded in the first-pass table or launch command; tmux session was created at 2026-10-20 19:26:25Z |
| `sweep_ncmoe_q4.jsonl` | 32 | `load_mode=none`; `use_mmap` not emitted | 2048 / 512 | 1 | 2026-10-20T19:38:02Z (`test_time`) |

The recorded settings do not differ in thread count, so this is not labeled a thread trap. The first-pass prefill was 218.96 tok/s; the rerun raw samples were 599.07, 620.82, 617.903 tok/s (median 617.903). This settings table records the evidence only; no further diagnosis was performed.
Q4 repeated depth sweep, d=0 prefill/decode also differs from the earlier thread sweep; recorded without investigation while the depth run continues. `sweep_threads_q4.jsonl` at ncmoe=38, n_threads=16, d=0 had decode samples 22.1832, 18.0469, 20.0165 tok/s (median 20.0165). `depth_q4.jsonl` at ncmoe=38, n_threads=16, d=0 had decode samples 12.2471, 12.4113, 11.1148 tok/s (median 12.2471), and prefill samples 496.195, 455.235, 449.328 tok/s (median 455.235). Runbook output will report per-run samples/min/max.
Q4 depth prefill direction note (logged without investigating while the sweep continues): `depth_q4.jsonl` d=0 prefill samples were 496.195, 455.235, 449.328 tok/s (median 455.235); d=32768 samples were 547.493, 548.03, 550.564 tok/s (median 548.03). The 32K median is higher, opposite the expected lower-at-depth direction. Report the raw samples and ranges.

128K context retry: B=38 OOMed while allocating a 1130 MiB CUDA buffer; retry uses B+2=40.
MTP task-run port note: the b11757 server with `--spec-type draft-mtp` failed to bind port 8081 because it was already occupied; the subsequent score attempt received HTTP 405 from the unrelated listener. The MTP flag was not rejected. Retrying the same MTP configuration and task set on alternate port 18081.
MTP memory retry: the MTP server at ncmoe=38, context 32768 failed to allocate a 2385 MiB CUDA buffer for its rs cache. Retrying with ncmoe=40 (two more MoE layers on CPU) to reduce VRAM use; the speculative flag was accepted.
MTP memory retry at ncmoe=40 also OOMed, failing to allocate a 1032 MiB CUDA buffer. Trying progressively higher CPU-MoE offload settings (42, 44, 46, then 49) at the required context; if all fail, log MTP as unavailable for this VRAM/context configuration and continue.

### Q4 perplexity load-mode retry
The first Q4 PPL invocation (`logs/ppl_q4.log`) included `-lm none` per the benchmark adaptation and failed model load with CUDA OOM allocating 20358.07 MiB (`logs/ppl_q4.log`, `logs/ppl_q4.time`, exit 1). Re-ran the prescribed PPL command with default load mode (omitting `-lm none`); it loaded and is processing all 87 chunks in `logs/ppl_q4_retry.log`. No further diagnosis or setting changes made.

Q4 PPL completed from the prescribed command with default model-loading mode: 5.7746 +/- 0.03590 (`logs/ppl_q4.log`), vs AtomicChat BF16 reference 5.7625 +/- 0.0358. This is about 0.21% above the reference, below the 5% flag threshold and well below 2x. The initial `-lm none` OOM log is retained separately as `logs/ppl_q4_lmnone_oom.log`; the canonical `logs/ppl_q4.log` is the successful retry.
Q3 PPL completed: 5.8312 +/- 0.03628 (`logs/ppl_q3.log`).

### Default thread count versus 32 threads
The default Q4 run selected n_threads=128 and measured prefill 446.692 tok/s (420.786–471.782) and decode 2.5153 tok/s (2.3478–2.7828), from `threads_default_q4.jsonl`. The explicit n_threads=32 row measured prefill 763.216 tok/s (760.007–764.552) and decode 15.8854 tok/s (15.6665–16.3629), from `sweep_threads_q4.jsonl`. This records the thread trap for the writeup; no reruns or further diagnosis.
