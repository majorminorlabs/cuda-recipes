# CUDA Recipes 011: long-context MoE on an RTX 3070 8GB

One physical RTX 3070 8GB with 32GB system RAM, Windows Vulkan for Edge0 and WSL CUDA for Magnitude/llama.cpp. This study asks which configurations complete 64K/128K requests, how quickly they decode, and how they score on a fixed 60-item set.

Stock Qwen3.6 Q4_K_M through uncapped llama.cpp completed both contexts at 14.9 and 8.0 tok/s. Magnitude completed them at both Docker memory caps, with lower decode throughput. Edge0 reached 20.74 tok/s at 64K under the 16 GiB Job Object cap, but failed at 128K. These paths use different model packaging, runtimes and memory accounting.

Raon completed 64K/128K through KRAFTON's branch at 5.7/5.0 tok/s. The later stock load probe failed. Flash Next's 64K run was stopped after an hour without output; its 128K and quality runs were not attempted.

See [results](RESULTS.md), [methodology](METHODOLOGY.md), [limitations](LIMITATIONS.md), and [model pins](DATA/models.json). Quality item definitions, scorer and per-item outcomes are in DATA/quality. Reports and score records were curated for public release; machine-specific operational records are excluded. No new benchmarks were run for publication.

Run `python3 validate.py` to verify package checksums and quality totals.

Credits: Qwen, Edge0, Magnitude, KRAFTON, and ggml-org/llama.cpp for models, runtimes and GGUF distributions. The quality design was informed by the CUDA-009/OpenBMB harness; that separate suite was inspected but not executed here.
