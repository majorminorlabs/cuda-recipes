# Sources

- PrismML Ternary Bonsai 2.5 27B GGUF repository: https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF (revision `28a7093cc25bc151cc2b284c5570f12ce343fdcf`).
- PrismML Bonsai demo and speculative decoding notes: https://github.com/PrismML-Eng/Bonsai-demo . The CUDA MTP profile was pinned from `presets/llama.cpp/mtp-cuda.json` at the model study date.
- PrismML llama.cpp fork: https://github.com/PrismML-Eng/llama.cpp (tag `prism-b12128-d7b2896`, commit recorded in `systems.json`).
- ggml-org llama.cpp: https://github.com/ggml-org/llama.cpp (commit recorded in `systems.json`).
- Qwen3.8 27B Q4_K_M artifact: https://huggingface.co/Abiray/Qwen3.8-27B-Q4_K_M-GGUF (pinned revision in `models.json`).
- Frozen task suite, scorer, and Qwen quality baseline: https://github.com/majorminorlabs/cuda-recipes/tree/main/001-24gb-compression .
- License: Bonsai model card identifies Apache-2.0; Qwen3.8 is Apache-2.0; llama.cpp is MIT. See root `NOTICE.md` for attribution.
