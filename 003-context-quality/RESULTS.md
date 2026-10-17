# Results

The primary arm contains 540 answers (three models × 180 questions). Each model received 60 questions at each length: 15 per task. `correct` is the content score; `format_strict_correct` preserves exact-format scoring for the multi-retrieval comparison. Percentages below are correct / 15.

## Accuracy by model, length and task

| Model | Length | Single retrieval | Multi retrieval | Aggregation | Multi-hop |
|---|---|---:|---:|---:|---:|
| Qwen3.6 35B-A3B | Control | 13/15 (86.7%) | 15/15 (100%) | 3/15 (20.0%) | 2/15 (13.3%) |
| Qwen3.6 35B-A3B | 64K | 14/15 (93.3%) | 6/15 (40.0%) | 5/15 (33.3%) | 0/15 |
| Qwen3.6 35B-A3B | 128K | 11/15 (73.3%) | 4/15 (26.7%) | 2/15 (13.3%) | 0/15 |
| Nemotron 3.5 Bolt | Control | 15/15 (100%) | 15/15 (100%) | 3/15 (20.0%) | 3/15 (20.0%) |
| Nemotron 3.5 Bolt | 64K | 13/15 (86.7%) | 7/15 (46.7%) | 2/15 (13.3%) | 0/15 |
| Nemotron 3.5 Bolt | 128K | 12/15 (80.0%) | 3/15 (20.0%) | 2/15 (13.3%) | 0/15 |
| Qwen3.8 27B | Control | 15/15 (100%) | 13/15 (86.7%) | 6/15 (40.0%) | 2/15 (13.3%) |
| Qwen3.8 27B | 64K | 15/15 (100%) | 3/15 (20.0%) | 4/15 (26.7%) | 2/15 (13.3%) |
| Qwen3.8 27B | 128K | 14/15 (93.3%) | 0/15 | 5/15 (33.3%) | 2/15 (13.3%) |

## Single retrieval by nominal position

Counts pool all three lengths (15 questions per model and band).

| Model | Early | Middle | Late |
|---|---:|---:|---:|
| Qwen3.6 35B-A3B | 13/15 (86.7%) | 14/15 (93.3%) | 11/15 (73.3%) |
| Nemotron 3.5 Bolt | 12/15 (80.0%) | 14/15 (93.3%) | 14/15 (93.3%) |
| Qwen3.8 27B | 14/15 (93.3%) | 15/15 (100%) | 15/15 (100%) |

The actual planted fractions are published per question in `DATA/questions.jsonl`; nominal labels are used for these grouped results.

## Multi-retrieval content and exact-format scores

The prompt said `{"answers":[...]}` without defining list-item structure. Content scoring compares the set of normalized answer strings, extracting strings directly or string-valued fields from object items while excluding entity-name fields. The secondary exact-format column compares the parsed structure with the reference exactly after case and whitespace normalization.

| Model | Length | Content | Exact format |
|---|---|---:|---:|
| Qwen3.6 35B-A3B | Control | 15/15 (100%) | 1/15 (6.7%) |
| Qwen3.6 35B-A3B | 64K | 6/15 (40.0%) | 0/15 |
| Qwen3.6 35B-A3B | 128K | 4/15 (26.7%) | 0/15 |
| Nemotron 3.5 Bolt | Control | 15/15 (100%) | 12/15 (80.0%) |
| Nemotron 3.5 Bolt | 64K | 7/15 (46.7%) | 5/15 (33.3%) |
| Nemotron 3.5 Bolt | 128K | 3/15 (20.0%) | 3/15 (20.0%) |
| Qwen3.8 27B | Control | 13/15 (86.7%) | 7/15 (46.7%) |
| Qwen3.8 27B | 64K | 3/15 (20.0%) | 2/15 (13.3%) |
| Qwen3.8 27B | 128K | 0/15 | 0/15 |

The content results match the expected counts. Lower exact-format results reflect equivalent answer values returned in a different list-item structure (especially Qwen3.6), as well as ordinary incorrect, missing or extra values. Aggregation and multi-hop remain exact-scored.

## Speed and output

| Model | Prefill time, control / 64K / 128K | Mean answer time | Mean generated tokens | Truncated | Invalid JSON |
|---|---|---:|---:|---:|---:|
| Qwen3.6 35B-A3B | 5.691 / 45.671 / 96.081 s | 1.783 s | 42.3 | 0 | 0 |
| Nemotron 3.5 Bolt | 11.614 / 89.965 / 180.022 s | 2.503 s | 24.0 | 0 | 0 |
| Qwen3.8 27B | 7.754 / 79.551 / 193.241 s | 3.241 s | 30.4 | 0 | 0 |

Prefill values are the measured per-document prefill time for each model and length. Answer time and generated-token means use 180 requests per model.

## Fit, cache and cost

All three models loaded all layers on GPU at 131,072 context with no fallback. Peak VRAM: Qwen3.6 21,232 MiB; Nemotron 21,658 MiB; Qwen3.8 20,476 MiB. Prompt caching was reused on 177/177 follow-up questions for each model (100%). The validation script checks every captured answer against the raw response file and checks reuse per document.

Primary arm: 0.624 GPU-hours × $0.50/hour = **$0.312 estimated**. Exploratory Qwen3.6 thinking-on arm: approximately 1.49 GPU-hours = **$0.745 estimated**. These use the advertised rate, not an invoice.

## Exploratory arm

The separate Qwen3.6 thinking-on run averaged 1,632 generated tokens per answer and hit its 2,048-token cap on 100/180 questions. Among 49 completed valid-JSON answers, 43 were correct. It is budget-bound exploratory evidence, not a long-context quality result. It used the old strict parser and retained no raw responses, so its multi-retrieval answers cannot be rescored.
