# Key findings

1. **8/12/16GB fit 128K on the desktop host.** At empty depth, Host C decode was 32.8/39.9/49.9 tok/s; at 117,964 tokens it was 27.5/32.4/38.5 tok/s. The 24GB GPU-only baseline measured 91.6 tok/s empty and 58.6 tok/s at 117,964.
2. **PPL stayed unchanged with CPU expert execution.** With `--no-op-offload`, N>0 Wikitext-2 results were 4.5850–4.5883; the 24GB baseline was 4.5816. These differences are inside the reported roughly 0.116 error. PPL was run on host 0 only.
3. **Thread count matters.** On Host C the decode ranking was `-t 6 > 12 > 8 > 4 > 16`; the best was 6 physical cores. Host A's `-t 128` 12GB result was 7.40 tok/s versus 46.36 at `-t 16`. Host 0's default-128 depth-zero rates were 7.15/9.55/10.78 at 8/12/16GB; relative to the corresponding optimized cloud runs, the default lost roughly fivefold.
4. **Offloaded decode is limited by host memory throughput.** Host C probes were 39.8–40.7 GB/s, consistent with dual-channel DDR4-class bandwidth. The host did not expose module speed or channel count, so that hardware characterization is inferred from measured bandwidth.
5. **Shared rented CPU slices varied sharply.** At 12GB/depth zero the cloud rows ranged 25.20–47.03 tok/s (1.87×); Host B's 45.07 tok/s start check fell to 25.20–30.63 later on the same pod. Within Host C's three reps, most budget/depth cell spreads were below 1%; the maximum was 5.0%.
6. **The 24GB GPU-only baseline also varied by host.** Host C's depth-zero median was 91.6 tok/s versus 87.3 tok/s across cloud hosts A/B, a 4.9% difference.
