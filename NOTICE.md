# Model and software notices

- NVIDIA Nemotron 3.5 Bolt 74B-A9B 24GB is distributed under NVIDIA's Open Model Distribution License (OpenMDW-1.1). Review the source model card and license before any redistribution or use beyond this research.
- Qwen3.8-27B is distributed by Qwen under Apache License 2.0. The Q4_K_M GGUF is a third-party conversion from the pinned Qwen upstream model; its converter repository also identifies Apache-2.0 and llama.cpp b10430.
- llama.cpp is MIT-licensed. Its exact source revision and CUDA build flags are recorded in the runtime manifest after deployment.
- Edge0-145B Q3_K is distributed under the Edge0 Community Model License 1.0 with a Qwen license notice. The two prefill request bodies use fixtures from the MIT-licensed Edge0 v0.2.0 Strata prompt bundle, credited in the study.
- Model weights, provider credentials, pod identifiers, host/network details, and raw operational traces are not included in this repository.

- CUDA Recipes 008 references Inkling 2 Mini and Unsloth/AtomicChat GGUF artifacts. Consult their upstream model cards and artifact licenses; no model weights or release binaries are redistributed. Bundled Anton and IBM Plex Mono fonts retain their included SIL Open Font License notices.
- Ternary Bonsai 2.5 27B is credited to PrismML and is built on Qwen3.8-27B (Apache License 2.0). Study 009 also evaluates the Qwen Q4_K_M conversion by its named publisher. Inference uses llama.cpp (MIT) and the PrismML llama.cpp fork. No weights or binaries are included.
- CUDA Recipes 009 graphics bundle Anton and IBM Plex Mono font files from the 008 chart package; both retain their SIL Open Font License notices in the recipe folder.
