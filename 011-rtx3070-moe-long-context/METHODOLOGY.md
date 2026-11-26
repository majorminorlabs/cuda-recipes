# Methodology

Hardware: RTX 3070 8GB (8192 MiB), 32GB system RAM. WSL Ubuntu 24.04.2 exposed about 23.47 GiB. Docker 29.10.1; NVIDIA Container Toolkit 1.20.2. System RAM caps are separate from GPU VRAM.

## Engines

- Edge0 0.2.0, commit `92f991720a0d22a506f8a7ea865da3724556cf3e`, Windows Vulkan; Edge0-35B-A3B-preview assets revision `e21098e7faa916a00f5493795f12f20497d032bb`. This is Qwen-derived 4-bit packaging with prerouter/LoRA, predicted routing and thinking disabled. Settings: expert_slots=32, prefill_chunk=4096, cached expert reads. Windows Job Object memory caps: 8/16 GiB.
- Magnitude 0.3.4, commit `e8d7938363f35259db635072505714aa01af8394`, image digest `sha256:fbefeac53542b256fde8202ec874bf6b9d456aaba4ff458ca6e1ffbd09e99be0`. Stock Qwen Q4_K_M with streamed experts; drafter none. Docker `--memory=8g` / `--memory=16g`, GPU passthrough, writable model directory. Read-only model mounts failed storage probes and were corrected. Swap-limit accounting was unavailable; there was no separately enforced swap cap.
- Qwen llama.cpp CUDA: build 12723, commit `abca69200`, image digest `sha256:1c72cbe908cba4310a80d464d9982f65d350a6e603afa0b39f52b063d255df00`. Flags `-ngl 99 -ncmoe 99 -t 16 -b 2048 -ub 512`; 64K/128K contexts 65536/131072, f16 K/V, 100 output tokens, temperature 0, seed 42. MoE experts run on CPU. No Docker memory cap.
- Raon KRAFTON branch `raon-1-mini`: commit `2d38b1d5d9102b0f70f86da18c0cc307080d5a41`, CUDA 12.8.1, CMake `-DGGML_CUDA=ON -DLLAMA_BUILD_BORINGSSL=ON`. Same CPU MoE flags, f16 K/V, contexts 65536/131072, 100 greedy tokens, seed 42, no warmup or Docker cap.
- Later stock Raon probe: upstream build 12767, 1.1.0-dev, commit `a8ad690ca`, image digest `sha256:e8bfbe33d4a8602f94d32c195adc204e8999453693ef640815a2511f1a8c7ccd`. One-token probe, context 2048, f16 K/V, same CPU offload flags. Failed on tensor count, so no larger runs followed.

## Timing and memory

Edge0 and Magnitude used 10 warmup tokens where accepted and 100 timed greedy tokens. Magnitude input counts were 64288/126905; Edge0 64K input was 64290. Qwen llama.cpp 128K input was 126895. Raon inputs were 64283/126900; Flash inputs 64159/126457 (128K not executed). Nominal labels are target context classes, not exact equal token counts.

Magnitude prompt telemetry can include reuse between identical warmup and timed prompts. New long-context fillers did not share earlier prefixes. llama.cpp prompt throughput is rounded; TTFT is derived. There are no repeated full-run estimates or confidence intervals.

RAM measurements differ: Windows Job Object peak commit, Docker samples/cgroup peaks, and WSL cgroup peaks. GPU measurements are sampled peaks or Edge0's dedicated Vulkan ledger. The earlier 8 GiB Magnitude GPU peak was not sampled. Earlier process RSS snapshots are not continuous peaks.

## Quality

60 fixed items: 15 coding, 20 exact math, 23 instruction following and 2 retrieval. One pass per model, same user prompts and ordering, 512-token output cap, greedy sampling, seed 42, reasoning disabled. Bare JSON or one outer JSON fence is accepted for content categories. Instruction tasks require bare JSON. Numeric strings differ from numbers. Coding checks restricted Python cases; passing does not prove general program correctness.

Edge0 uses 65536 context after allocation failure at 131072. Qwen and Raon use 131072 context. Retrieval spans are tokenizer dependent: Qwen 64340/126957 tokens, Raon 51301/100951. Edge0 rejects the second retrieval as over capacity. The original scorer is preserved with item definitions; public score rows retain task outputs but omit operational transport records and failed setup attempts. These are quality records, not executable instructions.
