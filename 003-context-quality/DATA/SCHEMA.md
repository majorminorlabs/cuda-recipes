# Data schema

## Frozen inputs (added in Phase 0, hashed before any run)
- `documents/`: one text file per document, with source, license and length label in a manifest
- `questions.jsonl`: one question per line: `question_id`, `doc_id`, `length_label`, `task_type`, `position` (early / middle / late / spread), `prompt`, `reference`, `negative_control`, and `entity_key` (randomized entity names used by the guessability audit)

## fit-results.csv
One row per model × attempted context size.

| Column | Meaning |
|---|---|
| model | `nemotron`, `qwen38_27b` or `qwen36_35b_a3b` |
| ctx_size | `--ctx-size` attempted |
| loaded_full_gpu | `1` only if llama-server `/health` returned 200 and every layer is on CUDA |
| layers_on_cuda, layers_total | from the llama.cpp layer-placement line |
| kv_buffer_mib, rs_buffer_mib | real allocation pass only (not llama.cpp's dry-run fit pass) |
| peak_vram_mib | nvidia-smi peak from launch to ready |
| error | reason when not loaded |

## prefill-results.csv
One row per model × document: the first (uncached) request for that document.

| Column | Meaning |
|---|---|
| length_label | `control`, `long_64k` or `long_128k` |
| prompt_tokens | tokens in the full prompt for this model's tokenizer |
| prefill_s, prefill_tps | time and rate to process the uncached prompt |
| peak_vram_mib | nvidia-smi peak during the request |

## answer-results.csv
One row per model × question.

| Column | Meaning |
|---|---|
| task_type | `single_retrieval`, `multi_retrieval`, `aggregation`, `multi_hop` |
| position | where the fact(s) sit in the document |
| prompt_tokens | total prompt tokens for the request |
| cached_prompt_tokens | tokens reused from the prompt cache (must be > 0 for every question after a document's first) |
| generated_tokens | output tokens including thinking |
| answer_s | wall time for the request |
| correct | `1` / `0`, deterministic exact match |
| failure_class | blank if correct; else `wrong_answer`, `invalid_json`, `truncated`, `error` |
