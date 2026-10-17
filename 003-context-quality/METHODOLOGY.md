# Methodology

## Models and runtime
- Nemotron 3.5 Bolt 74B-A9B 24GB, native 2-bit GGUF (same pinned file as 001 and 002)
- Qwen3.8 27B Q4_K_M (same pinned file as 001 and 002)
- Qwen3.6 35B-A3B Q4_K_M (pinned in Phase 0)

llama.cpp `620d2225cc436ab0b001e3200e590e3b286ef9ab`, built for sm_86, one RunPod RTX 3090 24GB, every layer on the GPU, no CPU offload. Server flags: `--ctx-size 131072 --parallel 1 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 -ngl 999 --flash-attn on --jinja`.

## Documents
Public-domain long-form text, beginning at the narrative's first chapter, with synthetic facts inserted at recorded positions so no answer can come from training data. Three lengths: about 8K tokens (control), 64K and 128K. Each document is sized so every model's full prompt stays at least 2,048 tokens under the window; actual per-model token counts are reported because tokenizers differ. Position bands are nominal: early is approximately the first third, middle approximately the second third, and late approximately the last third. `fact_fractions` in each question row publishes the actual character fraction(s) of its planted fact(s).

## Tasks
| Task | What it tests |
|---|---|
| Single retrieval | Find one planted fact |
| Multi retrieval | Find four planted facts spread through the document (content set equality) |
| Aggregation | Count or collect occurrences across the whole document |
| Multi-hop | Follow a three-step chain of facts placed at different positions |

Every question has a reference answer and a negative control that the scorer must reject. No model judge. Aggregation and multi-hop are exact-matched after case and whitespace normalization. Single retrieval is exact-matched on its answer field.

The multi-retrieval prompt requested `{"answers":[...]}` but did not specify whether each list item should be a string or an object. Models returned both forms. The primary content score collects each list item's string value, or all string-valued fields of an object item except the entity-name field (`shoal`, `entity`, `entity_name`, or `name`), then lowercases, strips and compares the values as a set with the four reference answers. Missing or extra values fail. `format_strict_correct` separately records exact parsed-structure equality for multi-retrieval; `correct` is the content score. Both columns are published. This study measures retrieval, not format compliance; CUDA Recipes 001 covered strict formatting.

## Generation
The primary arm uses thinking off (`chat_template_kwargs.enable_thinking=false`), each model's published non-thinking sampling settings in `DATA/sampling.json`, a 256-token generation cap, and a fixed seed per question shared across models. Pinned Qwen3.6 and Qwen3.8 tokenizer templates contain explicit false branches for `enable_thinking`; the pinned Nemotron GGUF template was verified against its upstream template, and NVIDIA documents the same false switch. Before the main run, three control questions per model must produce empty `reasoning_content`, no `<think>` tag in `content`, and a parseable answer below 128 generated tokens. That GPU preflight confirms runtime behavior; any failure stops the run before main-arm answers are collected. The Qwen3.6 thinking-on run is retained separately in `DATA/exploratory-thinking-on/`; it used a 2,048-token cap, the old strict parser, and had no raw response capture. Its budget-bound metrics are exploratory, not the primary long-context result.

## Answer extraction and raw responses
The scorer accepts a bare JSON object, an object in a fenced code block (with or without a `json` label), or the last top-level JSON object in response text. Every primary-arm inference response is appended to `_internal/responses/primary-<model>.jsonl`, including content, optional reasoning content, finish reason, usage, and answer time. `scripts/score_responses.py` rebuilds answer rows offline from these files; no GPU is needed to re-score. Unit tests cover all extraction forms and the multi-retrieval content cases.

## Prompt caching
Each document gets many questions. The document is placed first in the prompt so llama.cpp processes it once per document per model and reuses it for the following questions. Cache reuse is verified per request from llama.cpp's prompt-token counts.

## Measurements
Accuracy overall, by task type and by fact position; document prefill time; per-question answer time and generated tokens; peak VRAM; truncation and invalid-JSON counts.

## Fit fallback
If a model cannot load a 131,072-token window fully on the GPU, that is recorded, and its 128K documents are run truncated to the largest 8,192 multiple it can load, labeled as such.
