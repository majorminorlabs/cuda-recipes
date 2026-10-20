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

## Code arm

The code arm uses the same 540-answer design (three models × 180 questions). Counts are correct answers out of 15. Control is listed for completeness; context-length comparisons use 64K versus 128K.

### Accuracy by model, length and task

| Model | Length | Single retrieval | Multi retrieval | Aggregation | Multi-hop |
|---|---|---:|---:|---:|---:|
| Qwen3.6 35B-A3B | Control | 15/15 | 12/15 | 2/15 | 6/15 |
| Qwen3.6 35B-A3B | 64K | 15/15 | 11/15 | 2/15 | 6/15 |
| Qwen3.6 35B-A3B | 128K | 15/15 | 8/15 | 1/15 | 8/15 |
| Nemotron 3.5 Bolt | Control | 15/15 | 13/15 | 0/15 | 8/15 |
| Nemotron 3.5 Bolt | 64K | 15/15 | 10/15 | 1/15 | 7/15 |
| Nemotron 3.5 Bolt | 128K | 15/15 | 8/15 | 2/15 | 6/15 |
| Qwen3.8 27B | Control | 15/15 | 11/15 | 6/15 | 15/15 |
| Qwen3.8 27B | 64K | 15/15 | 11/15 | 5/15 | 13/15 |
| Qwen3.8 27B | 128K | 15/15 | 10/15 | 4/15 | 10/15 |

### Single retrieval by nominal position

| Model | 64K early | 64K middle | 64K late | 128K early | 128K middle | 128K late |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.6 35B-A3B | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Nemotron 3.5 Bolt | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Qwen3.8 27B | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

### Multi-retrieval content and format scores

| Model | Length | Content `correct` | `format_strict_correct` |
|---|---|---:|---:|
| Qwen3.6 35B-A3B | Control | 12/15 | 1/15 |
| Qwen3.6 35B-A3B | 64K | 11/15 | 0/15 |
| Qwen3.6 35B-A3B | 128K | 8/15 | 0/15 |
| Nemotron 3.5 Bolt | Control | 13/15 | 12/15 |
| Nemotron 3.5 Bolt | 64K | 10/15 | 5/15 |
| Nemotron 3.5 Bolt | 128K | 8/15 | 3/15 |
| Qwen3.8 27B | Control | 11/15 | 7/15 |
| Qwen3.8 27B | 64K | 11/15 | 2/15 |
| Qwen3.8 27B | 128K | 10/15 | 0/15 |

At control, Qwen3.6 counted the exact aggregation target plus its `_near` decoy in 9/15 answers; those are not content-correct aggregation answers under exact scoring.

### Prefill and answer output

| Model | Prefill control / 64K / 128K (s) | Mean answer time (s) | Mean generated tokens | Truncated at cap | Invalid JSON |
|---|---|---:|---:|---:|---:|
| Qwen3.6 35B-A3B | 4.769 / 48.616 / 103.307 | 1.494 | 27.65 | 5 | 0 |
| Nemotron 3.5 Bolt | 9.627 / 88.468 / 173.639 | 2.243 | 17.38 | 0 | 0 |
| Qwen3.8 27B | 6.680 / 77.786 / 189.425 | 3.055 | 29.16 | 7 | 2 |

Twelve answers hit the 256-token generation cap while producing visible reasoning: `003-code-control-mh-01`, `-mh-04`, `-mh-07`, `-mh-13`, `-mh-15` (Qwen3.6); `003-code-control-mr-04`, `-mr-14`, `003-code-long_64k-mr-03`, `-mr-08`, `-mr-13`, `003-code-long_128k-mr-05`, `-mr-13` (Qwen3.8). The Qwen3.8 128K multi-retrieval cell also has one invalid JSON response in addition to the two capped responses.

All models fit fully on GPU at 131,072 context, with no fallback. Prompt cache reuse was confirmed on all follow-up questions (177/177 per model). The run used 0.61 GPU-hours at the $0.50/hour advertised rate (approximately $0.305). Figures: [fig4](CHARTS/fig4-code-accuracy-by-task.png), [fig5](CHARTS/fig5-prose-vs-code-128k.png), [fig6](CHARTS/fig6-code-prefill-vs-length.png).


## Scratchpad counting addendum

The scratchpad changes only the aggregation prompt by asking for a line-by-line tally before the count. Each model × arm × length cell has **n=15**. The primary response-list cap was 1,024 generated tokens. The raw response metadata records 29 `finish_reason=length` answers (Qwen3.6 6, Nemotron 13, Qwen3.8 10); these are counted as wrong. Qwen3.8 omitted the tally entirely in 8 answers after extraction was widened.

| Model | Control final count | 64K final count | 128K final count |
|---|---:|---:|---:|
| Qwen3.6 35B-A3B | 17/30 | 11/30 | 9/30 |
| Nemotron 3.5 Bolt | 15/30 | 6/30 | 3/30 |
| Qwen3.8 27B | 17/30 | 8/30 | 9/30 |

The corrected `repetition_loop` flag is set for Qwen3.6 9/90 answers, Nemotron 25/90 and Qwen3.8 7/90; it requires at least two repeated listings beyond identical planted-target multiplicity. `followed_format` is set for 90/90, 90/90 and 61/90 answers, respectively.

Scratchpad cost estimate: **1.421 GPU-hours** (0.356 + 1.065) × **$0.50/hour** = approximately **$0.71**. The scratchpad package includes per-answer/item CSVs and column definitions in [`DATA/scratchpad/SCHEMA.md`](DATA/scratchpad/SCHEMA.md).

The extraction rules were widened after inspecting raw outputs: (1) attach adjacent code continuation lines to a `found N:` entry; (2) accept the literal placeholder `found N:` and assign sequential item numbers; and (3) if no `found` label exists, recover exact recorded target/decoy source lines quoted in the pre-JSON text, including bare prose lines and numbered code explanations. Matching and accepted formats are documented in the scratchpad schema.

Figures: [final-count baseline comparison](CHARTS/scratchpad-final-count-baseline.png), [failure classes](CHARTS/scratchpad-failure-classes.png), and [planted-item recall](CHARTS/scratchpad-planted-recall.png).
