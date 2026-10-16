# Sources and artifact provenance

## Model artifacts
- NVIDIA Nemotron 3.5 Bolt 74B-A9B official GGUF: [pinned repository revision](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF/tree/e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246); native 2-bit; artifact SHA-256 `91d63363e782c8a3d5f4be42816eba8e0d42dd2530bd07a7d0d2dc440599af75`. Upstream model revision `c6cc2e8ffa353403213d6b9b18aaf8eb684d705a`.
- Qwen3.8 27B upstream: [pinned upstream revision](https://huggingface.co/Qwen/Qwen3.8-27B/tree/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0). Q4_K_M conversion: [pinned GGUF revision](https://huggingface.co/Abiray/Qwen3.8-27B-Q4_K_M-GGUF/tree/f7a1cda580fe828415151042bf9f3dc5bb8b0d76); artifact SHA-256 `6a96cc760fc65cc6b9ea7f1922e3ff8b2a48c09f209456f23bbae9ef7032c867`. Converter repository states llama.cpp b10430.

## Runtime and hardware
- llama.cpp commit `620d2225cc436ab0b001e3200e590e3b286ef9ab` (both GPUs).
- Python 3.12.3, PyTorch 2.9.1+cu128, CUDA toolkit 12.8.93.
- CUDA Recipes 001 used an RTX 3090 driver 580.126.20 and RTX 5090 driver 570.195.03. This study used an RTX 3090 with driver 610.57.04; its sanitized host manifest is `DATA/rtx3090-manifest.json`, while the 001 record is retained as `DATA/rtx3090-manifest-001.json`.
- CUDA compatibility documentation: [NVIDIA CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html); [CUDA 12.8 Blackwell compatibility guide](https://docs.nvidia.com/cuda/archive/12.8.0/Blackwell_Compatibility_Guide.pdf).

The Qwen conversion is third party; its Hub metadata included an inconsistent automated scanner message. The pinned artifact SHA-256 and embedded chat template were verified, and the exact provenance note is retained in `DATA/model-manifest.json`.

All model revision, artifact hash, template verification, and runtime details are also in accompanying manifest JSON files.
