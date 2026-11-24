# Failed attempts and corrections

## Default and tuned context allocation

Both artifacts failed at default b2048/ub512 when configuring 128K F16. The requested CUDA compute allocation was approximately 12,860.22 MiB. At 256K F16 and Q8 it was approximately 25,532.22 MiB; the FP8 attempt requested about 25,533.72 MiB and also failed. Lower KV precision alone did not remove this compute-buffer demand.

Both passed short generation at 128K F16 with b256/ub128. At 256K Q8, b256/ub128 still failed requesting 6,381.67 MiB; b64/ub32 passed. The retained context table contains 14 attempts: ten failures and four successful short-generation checks. Workload flags, sampled memory and exact allocation errors remain in the evidence.

## Incomplete primary-host depth attempts

The initial 128K-depth captures produced no throughput rows. A long saturated-GPU observation was stopped and retained as incomplete. Utilization, elapsed time and a successful context load do not establish a decode rate. The verified deep rerun supplies the selected results.

## Lost supplemental run

A supplemental Secure Cloud pod completed provisional summaries of 35.384 tok/s base and 35.454 tok/s uncensored at 128K, and 23.640 tok/s base at 256K. The uncensored 256K measurement was still active at the last observation. Connectivity failed; recovery later confirmed the pod no longer existed. Its raw tree was not recovered or transfer-verified.

The operator reported a low-balance termination. Billing evidence did not independently establish that cause. These provisional figures are retained as history in `provenance.json` and are not selected measurements.

A separate RTX 3090 pod reran all four settings, transferring and verifying the evidence before termination. Selected rates are 36.646339 / 36.685906 tok/s at 128K F16 and 24.842185 / 25.018935 tok/s at 256K Q8, base / uncensored. Each point has one repetition. The new host's hardware and cgroup records are separate from the primary host's inventory.

## Setup and retention

The generic CUDA image initially did not provision SSH as expected. Startup was repaired before model or measurement artifacts existed; no timed result was affected. Provisioning credentials and operational administration are not distributed.

Original transfer verification passed for 325 first-arm files and 9,121 deep-rerun entries (9,103 regular files plus 18 symlinks). The package publishes 274 relevant compressed evidence files; model binaries, source/runtime checkouts and environments remain outside the distribution.

The earlier primary-host summary labelled 24,126 MiB as total GPU capacity. The captured device query reports 24,576 MiB and is authoritative. Provider allocation (125 GB RAM, 32 vCPUs) is labelled separately from host-visible resources (1.0 TiB RAM, 256 logical CPUs).

Historical rate-based cost estimates were approximately $0.43 for the first arm, $0.69–$0.91 for the lost supplemental arm and $0.95 for the verified deep rerun. These are not a complete invoice-verified total.
