# Scratchpad result schema

This package contains the offline rescore of the 90 aggregation questions in each of the prose and code arms (270 answers total). Each model × arm × length cell has 15 questions.

## `answer-results.csv`

One row per model × arm × aggregation question.

| Column | Meaning |
|---|---|
| `arm` | `prose` or `code`. |
| `model` | Model key: `qwen36_35b_a3b`, `nemotron`, or `qwen38_27b`. |
| `question_id` | Frozen question identifier. |
| `length_label` | `control`, `long_64k`, or `long_128k`. |
| `task_type` | `aggregation` for every row. |
| `prompt_tokens` | Prompt-token count reported by the server. |
| `cached_prompt_tokens` | Prompt tokens reused from cache. |
| `generated_tokens` | Completion-token count reported by the server. |
| `answer_s` | Wall time for the request, seconds. |
| `finish_reason` | Server completion reason, including `stop` or `length`. |
| `final_count_correct` | `1` if the extracted final JSON object exactly matches the reference count; otherwise `0`. |
| `listed_items` | Number of tally entries extracted before the final JSON object. |
| `matched_planted` | Number of planted target items credited. |
| `missed_planted` | Planted target items not credited for this answer. |
| `matched_decoy` | Number of planted decoy items credited as listed. |
| `ambiguous` | Number of listed entries matching distinct planted text candidates; these receive no planted/decoy credit. |
| `extra_items` | Count of ambiguous entries plus in-document entries that match neither a target nor a decoy. |
| `unmatched` | Listed entries that match neither target/decoy candidates nor text in the source document. |
| `list_count_consistent` | `1` when the final integer count equals the number of extracted tally entries; otherwise `0`. |
| `failure_class` | One primary class, assigned by the priority order below. |
| `repetition_loop` | `1` if some normalized listed line occurs at least two times beyond the number of identical planted target lines for that question; otherwise `0`. |
| `followed_format` | `1` if the response used a `found <number or N>:` prefix; otherwise `0`. |

### `failure_class` values and priority

Exactly one class is assigned per answer, using this order:

1. `truncated`: server `finish_reason` is `length`.
2. `invalid_json`: no final JSON object can be extracted.
3. `no_list`: no tally entries can be extracted before the final JSON.
4. `decoy_included`: at least one planted decoy was matched.
5. `extra_item`: at least one ambiguous or in-document extra entry was listed.
6. `missed_items`: one or more planted targets were not matched.
7. `miscount_of_list`: final count is wrong or differs from the number of extracted entries.
8. `correct`: none of the above apply.

Per-answer counts remain available even where the primary class takes precedence. For example, a truncated answer can also have matched targets and extras.

## `items.csv`

One row per extracted tally entry.

| Column | Meaning |
|---|---|
| `arm`, `model`, `question_id` | Answer identity. |
| `item_index` | One-based order in the extracted tally. |
| `found_number` | Number following `found`; inferred sequentially when the literal placeholder `N` was used or when a source quote had no prefix. |
| `listed_text` | Extracted text for that entry, including code continuation lines when attached to a `found` prefix. |
| `match_class` | `planted`, `decoy`, `ambiguous`, `extra_item`, or `unmatched`. |
| `matched_event_id` | Planting-map event credited for a planted or decoy match; blank otherwise. |
| `in_document` | `1` if the listed text is found in the raw document after whitespace/indentation normalization (or contains a complete recorded source candidate); else `0`. |

## Matching rules

- Normalize case and whitespace. A listed entry matches a planted candidate when it contains the full candidate, or when the listed entry is a substring covering at least 80% of the candidate and contains more than the entity/helper key.
- If one entry can match candidates with different normalized text, mark it `ambiguous` and give no target/decoy credit. Identical target text represents distinct occurrences and is consumed one occurrence at a time.
- A candidate match is credited to the target before a decoy when both types match. Entries that are not planted matches are checked against the raw document with whitespace and indentation ignored. Present-but-unplanted text is `extra_item`; absent text is `unmatched`.
- `repetition_loop` compares repeated normalized listed lines with the count of identical planted target lines for that question. It is set only when the excess is at least two. Thus three identical planted targets listed three times are not a loop; the same line listed six times is.

## Extraction formats

- The final answer parser accepts a bare JSON object, an object in a `json` or plain code fence, or the last top-level JSON object in the response.
- Tally extraction accepts `found 1: ...` and markdown/bullet/numbered wrappers around that label. The literal `found N:` placeholder is accepted and assigned the next sequential number.
- Adjacent code lines (for example, an indented `return lookup_x()` after a `found N: def call_x():` line) are attached to that entry.
- After reviewing raw responses, extraction was widened: when no `found` labels occur, exact recorded target/decoy source candidates quoted in pre-JSON text are recovered, including bare document lines, numbered explanations and code blocks. Generic reasoning and final JSON alone do not create a tally.

These post-run extraction extensions are documented because they were added after inspecting model outputs; the item-level CSV preserves the resulting entries for review.
