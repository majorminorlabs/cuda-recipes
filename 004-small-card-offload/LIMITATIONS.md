# Limitations

- The 8/12/16GB conditions use a 24GB RTX 3090 capped to a VRAM budget, not real small cards. Real small cards generally have less GPU memory bandwidth, so GPU-side work here is a best case for them.
- Host C's RAM module speed and channel count were unreadable through `dmidecode` and `lshw`. Its 39.8–40.7 GB/s probe is consistent with dual-channel DDR4-class bandwidth, but that is an inference.
- The offloaded 8/12/16GB configurations did not fit the 256K load test; only the 24GB baseline did.
- In the archived Host 0 `-t 128` 118K bench rows, the 8GB and 12GB peaks were 115 and 117 MiB above their budget-minus-500-MiB ceilings. Host C's corresponding 118K peaks stayed below the ceilings.
- PPL was measured on host 0 only. It measures the same model math and is expected to be host-independent, but this study did not repeat PPL on Host C.
- Cloud host CPU slices were shared and variable; Host C is the desktop-class comparison host. The host-to-host speed differences should not be read as model changes.
- llama-bench fill depth is synthetic; real prompts and concurrent workloads may differ.
- RunPod and Vast costs use recorded provider list rates and runtime estimates, not invoices.
