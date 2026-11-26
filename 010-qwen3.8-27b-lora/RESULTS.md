# CUDA recipe 010 — Qwen3.8-27B base vs. coding-agent super-adapter on RTX 3090

## Summary

A fresh, paired study ran all 120 trials for each arm on the same NVIDIA GeForce RTX 3090 (24 GB). The adapter arm passed 87/120 (72.5%) versus 82/120 (68.3%) for base, a gain of 5 trials (+4.2 percentage points). The paired outcomes were 8 adapter-only passes, 3 base-only passes, 79 both-pass pairs, and 30 both-fail pairs. The adapter helped most on coding tasks; structured-data results were slightly lower. Mean decode speed was about 15.4% lower with the adapter.

## Design and configuration

- Suite: 40 tasks, 3 repetitions each, 120 trials per arm. The same prompt, seed, and task/repetition were paired; order alternated within pairs.
- Base arm: Qwen3.8-27B Q4_K_M, no adapter applied.
- Adapter arm: same quantized base with the merged coding-agent LoRA enabled. The server kept the LoRA loaded for both arms and toggled its scale to 0 for base requests and 1 for adapter requests.
- Engine: llama.cpp server `1.1.0-dev`, commit `a866b4ade63921826c530307a368fbca3a334a0b`, GCC 13.3.0, CUDA 12.8.93, compute capability 8.6.
- Quant: Q4_K_M. It fit with the adapter resident and a 16,384-token context; maximum observed GPU allocation was 20,263 MiB of 24,576 MiB.
- GPU offload: `--n-gpu-layers 99`; context 16,384; KV cache K/V both `q8_0`; flash attention on; parallel slots 1.
- Thinking: enabled for both arms. The server used `--chat-template-kwargs '{"enable_thinking":true}'`; requests also explicitly enabled thinking. llama.cpp emitted a deprecation notice for the server CLI template-kwargs option, but the paired requests used the explicit setting in both arms.
- Sampling: temperature 1.0, top-p 0.95, top-k 20, min-p 0.0; fixed paired seeds from the schedule.
- Output caps: 4,096 tokens for non-tool turns and 1,024 tokens per tool turn.
- TTFT probe: 3 measurements per arm, alternating; median reported below.
- The adapter was served directly as the official GGUF LoRA. No conversion was performed.

## Models and upstream credit

- Base model: [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B), revision `37561816e66b5b9153b1b64c10968c18c1e6f4a0`.
- Base GGUF used: [ggml-org/Qwen3.8-27B-GGUF](https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF), revision `c1869413dece09109e55b7dcc2c77ef382b0d0bd`; `Qwen3.8-27B-Q4_K_M.gguf`, 19,403,684,480 bytes; SHA-256 `d15d4b6de55f662ac40e867702d31afe738d032fa06b829b2b1a21a49d4a48ee`.
- Merged LoRA used: [harness-hub/Qwen3.8-27B-super-adapter-GGUF](https://huggingface.co/harness-hub/Qwen3.8-27B-super-adapter-GGUF), revision `dcdf29a1ba09546e8c9e6afc5c7a86d7032b0572`; `Qwen3.8-27B-super-adapter-lora-F16.gguf`, 956,336,640 bytes; SHA-256 `90dc73d4f67fa2e8fc66d501e4278313eacec460f36ec7225ff64a420ffe5ab4`.
- PEFT adapter credit: [harness-hub/Qwen3.8-27B-super-adapter](https://huggingface.co/harness-hub/Qwen3.8-27B-super-adapter), revision `3358a71529ce56aba0095addd6a60a66d7c4228b`.
- The merged adapter combines three harness-specialized LoRAs. Credit-only source revisions: [Pi](https://huggingface.co/harness-hub/Qwen3.8-27B-pi-adapted) `41396a9f14d9c1a1bf5bee4fb89e9dddadaeae7e`; [Hermes Agent](https://huggingface.co/harness-hub/Qwen3.8-27B-hermes-adapted) `0467acba2ff7788ec8050e7349fb5aa60bb6ddba`; [OpenCode](https://huggingface.co/harness-hub/Qwen3.8-27B-opencode-adapted) `9c6545360eb1fea3a1fb2d142e5c166a88ffc275`. These specialist adapters were not separate study arms.
- Adapter background: [Harness adapters at scale](https://huggingface.co/blog/harness-adapters-at-scale).
- Serving engine: [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## Results

| Category | Base | +adapter |
|---|---:|---:|
| Overall | 82/120 (68.3%) | 87/120 (72.5%) |
| Coding | 20/36 (55.6%) | 24/36 (66.7%) |
| Terminal/system | 16/24 (66.7%) | 17/24 (70.8%) |
| Tool use | 22/24 (91.7%) | 22/24 (91.7%) |
| Structured data | 15/18 (83.3%) | 14/18 (77.8%) |
| Multi-step | 9/18 (50.0%) | 10/18 (55.6%) |

Paired disagreements: adapter-only pass 8; base-only pass 3. Both passed 79 pairs; both failed 30 pairs. No trials were missing and no API/server errors were recorded.

## Speed and memory

| Metric | Base | +adapter |
|---|---:|---:|
| Decode speed, mean | 37.83 tok/s | 32.00 tok/s |
| Decode speed, median | 37.84 tok/s | 32.00 tok/s |
| Prefill speed, mean | 743.68 tok/s | 628.55 tok/s |
| Prefill speed, median | 270.25 tok/s | 248.95 tok/s |
| TTFT, median of 3 probes | 370.23 ms | 375.81 ms |
| Per-trial wall time, mean | 11.59 s | 10.13 s |
| Per-trial wall time, median | 6.25 s | 6.69 s |
| Sum of measured trial wall times | 23m 11s | 20m 16s |
| Peak VRAM | 20,263 MiB | 20,263 MiB |
| Peak host RAM | 30.16 GiB | 30.13 GiB |

The runner's first-trial to last-trial interval was 43m34s (13:43:56–14:27:30 UTC). Mean and median prefill rates differ because prompt lengths vary and the server reports cached and evaluated prompt timing differently. Per-trial means are affected by different response/tool lengths and do not represent an identical fixed-length speed test.

## Failures and truncation

Failures are scorer/harness outcome classes; a completed failure is not an infrastructure error.

| Failure type | Base | +adapter |
|---|---:|---:|
| Code tests failed | 16 | 12 |
| Tool action or final mismatch | 8 | 7 |
| Tool-turn limit | 3 | 3 |
| Incorrect structured result | 3 | 4 |
| Incorrect command | 6 | 6 |
| Invalid JSON | 1 | 1 |
| Output truncated at model length limit | 1 | 0 |

The single detected truncation was base trial TE07 repetition 2, with a length finish reason at the 4,096-token cap. The adapter arm had no length-finish truncations. No trial was stopped by the pod budget guard.


## Interpretation limits

This is one suite execution per arm on one GPU, with 40 tasks repeated three times. The repetitions are not 120 independent tasks. The five-pass net gain is descriptive and does not establish general statistical superiority. Both arms kept the adapter resident, so equal VRAM does not measure the memory cost of loading the adapter. Decode rates are task-run aggregates, and output lengths vary. TTFT used only three probes per arm. Host RAM is sampled container/system usage, not isolated model RAM.
