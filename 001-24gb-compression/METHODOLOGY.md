# Methodology

## Design and sample
Forty frozen deterministic tasks: coding 12, terminal/system 8, tool use 8, structured data 6, multi-step execution 6. Each task has a validated reference solution and negative control. Each model received three independent scheduled repetitions per task and GPU. Each GPU has 240 assignments (120/model); total 480. The predetermined assignment IDs, task repetitions, seeds, and order are in `DATA/schedule.json`.

## Harness and scoring
Both replications use `src.run_v2` with the reasoning-history fix: assistant `reasoning_content` is retained with content and tool calls when reconstructing tool-use history. Deterministic task-specific outcome scorers are used; no model judge. Scores are binary strict contract outcomes. Task-specific scoring and controls are in `DATA/scoring.json` and `DATA/tasks.json`.

## Common inference configuration
llama.cpp commit `620d2225cc436ab0b001e3200e590e3b286ef9ab`; Python 3.12.3; PyTorch 2.9.1+cu128; CUDA toolkit 12.8.93; 16,384-token context; Q8_0 K/V cache; one parallel slot; batch 512, ubatch 128, flash attention and Jinja enabled; all layers placed on CUDA; CPU layer offload disabled. Tool-task turn cap 512 generated tokens, single-turn cap 2,048 tokens, maximum six tool turns. Thinking enabled. Common temperature 1.0 and top_p .95; top_k 40 Nemotron, 20 Qwen. Schedule fixes the seed per task repetition and uses the same seed for both models; turn index contributes to per-turn seeding.

## Artifacts
Nemotron is pinned to NVIDIA GGUF revision `e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246`, SHA-256 `91d63363e782c8a3d5f4be42816eba8e0d42dd2530bd07a7d0d2dc440599af75`. Qwen conversion is pinned to `Abiray/Qwen3.8-27B-Q4_K_M-GGUF` revision `f7a1cda580fe828415151042bf9f3dc5bb8b0d76`, SHA-256 `6a96cc760fc65cc6b9ea7f1922e3ff8b2a48c09f209456f23bbae9ef7032c867`; upstream revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. Full manifests are in `DATA/`.

## Hardware-specific differences
GPU architecture and driver necessarily differ: RTX 3090 sm_86, driver 580.126.20; RTX 5090 sm_120a, driver 570.195.03. Both used same CUDA toolkit, Python, PyTorch, llama.cpp commit, model artifacts, settings, task suite, seeds, and scoring. These differences and independent provider nodes confound causal attribution to GPU hardware. Both model placements were fully on CUDA: 89/89 Nemotron layers and 66/66 Qwen layers. `CPU_Mapped` memory reported by llama.cpp is file-backed model mapping, not CPU layer execution.

## Reproduction and integrity
The configuration JSON is included exactly as recorded for both executions. Its `suite` and `original_freeze` fields are identifiers for the common frozen task suite and lineage; they do not indicate inclusion of any other scored result dataset. This package contains only the two corrected datasets and their paired analysis.

Frozen input copies and public manifests accompany canonical outputs. Per-GPU canonical result JSON and the paired validation receipt carry totals and freeze/hash evidence. Per-run CSVs preserve assignment-level scores and sanitized telemetry; no raw model responses are included. Private checkpoint DBs and raw traces remain outside this package.
