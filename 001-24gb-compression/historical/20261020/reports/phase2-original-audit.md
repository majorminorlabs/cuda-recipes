# Phase 2 audit of the original RTX 5090 study

Audit completed locally on 2026-10-15. This report is additive. The Phase 1 schedule, frozen benchmark, canonical results, checkpoint database, and scored traces were not edited or rescored.

## Verdict

The 33.3% Nemotron versus 91.7% Qwen result on tool-use tasks is **not explained by llama.cpp failing to parse Nemotron's native function calls**. The pinned llama.cpp v0.7.0 (commit `620d2225cc436ab0b001e3200e590e3b286ef9ab`) returned native structured `tool_calls` for both models. Across the 42 tool-bearing tasks per model, the traces contain 83 Nemotron and 89 Qwen structured calls, with zero invalid JSON argument payloads. The task simulator did execute calls and record each result.

The gap is a mixture of model behavior and benchmark/harness strictness. Nemotron produced a much less reliable final JSON answer after successfully calling the requested tool: it completed the exact expected action sequence in 21/24 tool-use trials but passed only 8/24 overall. In 13 of its 16 failed tool-use trials, the action sequence was exact; the recorded failure was an invalid or truncated final response. This is a genuine response-contract failure for this harness, not a parser failure. It is not evidence that Nemotron cannot use tools in general.

The original score remains a valid report of the preregistered strict contract on this particular suite. It is too brittle to support a broad claim about relative agent/tool competence because several fixture rules are hidden or overconstrained, follow-up reasoning is dropped by the adapter, and the two model templates give different reasoning instructions. Corrected scoring or altered prompts would constitute a new benchmark version and must be run separately.

## Trace integrity and original headline

The read-only audit found 240 trace files, 120 per model, matching the checkpoint database counts and success totals. The original freeze receipt still identifies 240 scheduled trials. The reproducible summary is `phase2-original-trace-audit.json`; regenerate it with `scripts/audit-original-traces.py` and private `--trace-dir` / `--db` paths.

| Metric | Nemotron | Qwen |
|---|---:|---:|
| Overall assigned-trial success | 65/120 (54.2%) | 84/120 (70.0%) |
| Coding | 20/36 (55.6%) | 20/36 (55.6%) |
| Terminal/system | 18/24 (75.0%) | 17/24 (70.8%) |
| Tool use | 8/24 (33.3%) | 22/24 (91.7%) |
| Structured data | 13/18 (72.2%) | 14/18 (77.8%) |
| Multi-step | 6/18 (33.3%) | 11/18 (61.1%) |
| Exact expected tool-action sequence | 27/42 | 33/42 |
| Simulator-accepted tool attempts | 60/83 | 68/89 |
| Invalid JSON tool arguments | 0 | 0 |
| Maximum observed prompt tokens / 16K context | 4,124 (25.1%) | 4,533 (27.7%) |

### Tool-use score decomposition (8 tool-use tasks × 3 repetitions)

| Measure | Nemotron | Qwen |
|---|---:|---:|
| Strict task success (original scorer) | 8/24 (33.3%) | 22/24 (91.7%) |
| Correct tool-action execution (exact expected sequence and every attempt accepted) | 21/24 (87.5%) | 22/24 (91.7%) |
| Final-response contract compliance (strict JSON equals `{"done":true}`) | 8/24 (33.3%) | 23/24 (95.8%) |
| Correct action execution, final contract failed | 13/24 | 0/24 |

This isolates the source of the gap in the observed traces: Nemotron completed and had every tool action accepted in 21 of 24 trials, but only 8 of those trials satisfied the final JSON contract. The 13 remaining failures were eight invalid JSON responses and five truncated responses. Qwen had one truncated response after an otherwise correct action sequence and one trial with an incorrect/rejected action sequence despite a valid final response. These are descriptive trace counts; strict task success remains the preregistered headline.

The original task-cluster bootstrap gives an overall paired difference (Nemotron minus Qwen) of -15.8 percentage points, 95% CI [-29.2, -3.3]. The tool-use task-cluster intervals are 8.3–62.5% and 75.0–100.0%, respectively. The complete task-by-task table and latency analysis remain in `publication/research-report.md`. On tool-use tasks, all 3 repetitions passed for TO01 and TO06 on both models. Nemotron passed 0/3 on TO02, TO05, TO07, and TO08; Qwen passed all repetitions on TO02, TO03, TO04, TO06, TO07, and TO08. These patterns are consistent with Nemotron's response-contract failures and the TO05 fixture mismatch described below.

## Tool-call path and adapter behavior

At the pinned server revision, llama.cpp's server chat conversion preserves structured tool calls and reasoning in its internal message representation (`tools/server/server-chat.cpp`, `common/chat.cpp`). The Qwen server used `peg-native` parsing with the pinned Qwen template; its raw trace shows `<tool_call>…</tool_call>` generation followed by a structured OpenAI-compatible `tool_calls` object. Nemotron traces likewise contain structured calls and JSON-decodable arguments. Calls rejected by the simulator were validly parsed calls with an unsupported task argument or ordering; they were not parser exceptions.

There is a real client adapter defect: in `src/run.py`, the assistant message appended after a tool response includes `content` and `tool_calls` but omits `reasoning_content`. The raw server response contains that field on every tool-bearing response inspected. Both pinned templates consume it when rendering conversation history; Qwen's template explicitly wraps it in `<think>`, while Nemotron's template reconstructs `<think>…</think>`. Thus every assistant tool-call message replayed by the runner loses model-generated reasoning. This does not establish that restoring it would change the scores, and the omission affects both models, but it makes this a meaningful multi-turn harness confound. A v2 adapter should preserve the field and be validated before a new scored freeze.

The models also did not receive identical reasoning instructions. The Qwen template defaults to `reasoning_effort=xhigh` and prepends an explicit xhigh instruction to its rendered system prompt. Nemotron's pinned template defaults to thinking enabled but does not inject the same effort directive. Both received `enable_thinking=true`, but the effective prompting was not equivalent. The recorded top-k values also differ (Nemotron 40, Qwen 20) by declared model-specific configuration. Keep these as named configuration factors; do not attribute the outcome solely to quantization.

## Scorer and task-contract findings

The tool score requires all three of: exact final JSON, every attempted tool call accepted, and exact equality of the full action list to a single reference sequence. Extra safe exploration, a recoverable rejected attempt, or a different valid action sequence therefore forces failure even if the requested state is ultimately achieved. For example, MU02's prompt asks to copy, verify, then delete. The scorer additionally requires `list_file` as the first action although the prompt does not request inspection; traces from both models include repetitions that successfully copied, verified, and deleted the file but still failed because the full sequence differed.

Other clear task/scorer concerns:

- **TO05:** the request is to count orders. The simulator accepts only the exact string `SELECT COUNT(*) FROM orders;`; equivalent valid SQL (including the same query without a semicolon) is rejected.
- **MU04:** the prompt asks to schedule “a review”; the simulator requires the title `Review` with exact capitalization. Nemotron's lowercase `review` is rejected although title casing is unspecified.
- **MU05:** the prompt says “fixed source table” but does not expose its identifier `quarterly`; the tool schema and generic tool descriptions do not reveal it. Neither model found the hidden name in the allotted interaction.
- **MU06:** the prompt says `project` but never identifies the fixture's project name `app`; the exact-name requirement is hidden from both models.
- Tool descriptions are generic (“Perform the … operation in the task fixture”), so they do not document task-specific semantics, valid resource names, or constraints. The natural-language task is the only specification and is insufficient in the cases above.

Suggested separately versioned scoring correction: assert task-goal state and a strict final response schema, record simulator errors as a separate reliability metric, and permit any safe action sequence that reaches the goal. Make each task's resource identifiers and exact output constraints explicit. For SQL tasks, validate a constrained read-only query's result rather than one literal string. Validate all positive and negative controls against goal-state assertions. Do not apply these corrections to Phase 1 outputs.

## Task realism, context, and failure classes

The 12 coding prompts are standalone Python function synthesis with small fixed test cases; they do not modify a repository, run a project test suite, or require multi-file debugging. The tool and multi-step tasks exercise short simulated state transitions, not real terminal, browser, filesystem, or service integrations. They support a narrow functional benchmark, not a long-horizon software-engineering benchmark.

The maximum prompt in the trace set is 4,533 tokens against a 16,384 context ceiling; context capacity was not stressed. Tool/multi-step generations were capped at 512 tokens per turn, with at most six turns. Nemotron's tool-use failures split into 10 invalid final JSON and 6 truncations; its multi-step failures include 7 truncations, 4 strict action/final mismatches, and 1 turn-limit failure. Qwen has 1 truncation and 1 action/final mismatch in tool use; its multi-step records include 2 truncations, 3 mismatches, 1 turn-limit failure, and 1 HTTP/server error. Error taxonomies mix model response-contract failures, benchmark contract failures, and runtime errors; a new taxonomy should separate these axes.

## Reproducibility and preservation

Both models were loaded one at a time on one RunPod RTX 5090 with all layers resident on CUDA (Nemotron 89/89; Qwen 66/66), a 16K context, Q8_0 KV cache, and the same pinned llama.cpp build. Recorded peak GPU memory was 21,392 MiB for Nemotron and 17,019 MiB for Qwen. The trace summary checks counts/success totals against SQLite but leaves the database and original canonical outputs untouched. The original paid GPU allocation was 0.87 hours, estimated at $1.04 from the provider rate returned during Phase 1; the billing API returned no posted usage rows, so this is not an invoice amount. It is not counted against the new Phase 2 budget.

The original task suite, freeze receipt, run database, and raw traces remain the authoritative Phase 1 data. This report and its audit script/summary are additions on the local `phase2-original-audit-local-prep` branch. No new GPU was provisioned, and no publication or push occurred.
