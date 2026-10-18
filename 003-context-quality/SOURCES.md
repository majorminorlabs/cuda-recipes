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

## Added in 003
- Qwen3.6 35B-A3B upstream: [immutable model revision](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0); config used for the attention/KV estimate: [pinned config.json](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/7da1103448ba36029c34ce1a9a741dfe93ee0c50/config.json).
- Official `ggml-org` Q4_K_M conversion: [immutable GGUF revision](https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/tree/baec3ebee244827cda0f4557eafa8b28f7545fa6); file SHA-256 and size are in `DATA/model-manifest.json`. The embedded template exactly matches upstream tokenizer config. The architecture loader exists at [the pinned llama.cpp commit](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/src/models/qwen35moe.cpp).
- Haystack source: [Project Gutenberg eBook 2701, Moby-Dick; or, The Whale](https://www.gutenberg.org/cache/epub/2701/pg2701.txt), by Herman Melville. The underlying work is public domain in the United States. The frozen haystacks are prepared from the narrative beginning at “CHAPTER 1. Loomings”; title matter, contents, Etymology and Extracts are excluded. Synthetic fact sentences are inserted into the narrative. Project Gutenberg's distribution terms and trademark conditions apply to its eBook edition; see the [Project Gutenberg License](https://www.gutenberg.org/policy/license.html). The document source and generated text hashes are in `DATA/documents/manifest.json`.

## Code arm

Django is selected at [commit `d430084791a61b31cecec132bce3dca19194f7f2`](https://github.com/django/django/commit/d430084791a61b31cecec132bce3dca19194f7f2), licensed BSD-3-Clause. It provides 5,232,394 bytes across 594 eligible first-party Python files after excluding tests, migrations, locale data, vendored/generated/static/build content and modules below 200 bytes. SQLAlchemy at `7b95e267c867f9e35ee0aba7e637f373522b0e1d` (MIT) was the alternative. See the [Django license](https://github.com/django/django/blob/d430084791a61b31cecec132bce3dca19194f7f2/LICENSE). Frozen ordered files, tokenizer counts and document hashes are recorded in `DATA/code/documents/manifest.json`; model artifacts and revisions are in `DATA/code/model-manifest.json`.
