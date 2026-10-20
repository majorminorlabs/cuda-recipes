# Key findings

- At 128K, single-fact retrieval remained relatively strong (11–14/15 per model), while four-fact retrieval fell to 0–4/15. The gap is the clearest result in this task set.
- Qwen3.8 led on 128K single retrieval (14/15); Qwen3.6 led on 128K four-fact retrieval (4/15). No model exceeded 3/15 on 128K multi-hop.
- Multi-retrieval content scoring matters: the prompt left list-item type undefined. After rescoring answer values independent of object-vs-string representation, the expected content counts were Qwen3.6 15/15, 6/15, 4/15; Nemotron 15/15, 7/15, 3/15; and Qwen3.8 13/15, 3/15, 0/15 for control, 64K and 128K.
- The thinking-on Qwen3.6 arm is budget-bound and separate. Its high generation cap confounded context quality with long reasoning/output.

See [RESULTS.md](RESULTS.md) for all task-level accuracy, position, speed and cost numbers, and [CHARTS](CHARTS/) for figures.

## Code arm

- Single retrieval scored 15/15 at both 64K and 128K for all three models. Four-fact retrieval was lower (8/15, 8/15 and 10/15 at 128K for Qwen3.6, Nemotron and Qwen3.8). Aggregation remained difficult (1/15, 2/15 and 4/15 at 128K); multi-hop was 8/15, 6/15 and 10/15.
- At control, Qwen3.6 included the exact aggregation count and the `_near` decoy in 9/15 answers, illustrating the challenge of distinguishing near-miss identifiers.
- Twelve answers reached the 256-token cap while emitting visible reasoning: Qwen3.6 control multi-hop 01, 04, 07, 13 and 15; Qwen3.8 multi-retrieval control 04 and 14, 64K 03/08/13, and 128K 05/13. Two additional Qwen3.8 multi-retrieval responses had invalid JSON (one at 64K and one at 128K).
- Prefill rose from 4.8–9.6 seconds on control to 48.6–88.5 seconds at 64K and 103.3–189.4 seconds at 128K. Compare 64K with 128K for context-length results; control is a short, dense task variant.

See [RESULTS.md](RESULTS.md) for complete tables and [CHARTS](CHARTS/) for figures.


## Scratchpad counting addendum

- Pooling the two arms (n=30 per model × length), final-count accuracy was Qwen3.6 17/30, 11/30, 9/30; Nemotron 15/30, 6/30, 3/30; and Qwen3.8 17/30, 8/30 for control, 64K and 128K.
- Qwen3.8 returned no tally in 8 answers. Reading the raw responses recovered line lists that lacked `found N:` labels; eight other responses contained only a JSON count.
- The corrected repetition-loop flag is set for 9 Qwen3.6, 25 Nemotron and 7 Qwen3.8 answers; it subtracts the expected multiplicity of identical planted target lines. The `found N:` form appears in 90, 90 and 61 answers, respectively.
- Preserved raw metadata marks 29 answers as `finish_reason=length` (Qwen3.6 6, Nemotron 13, Qwen3.8 10); these count as wrong.
- Extraction was widened after output review: code continuations are joined to found entries, the literal `found N:` placeholder is accepted, and exact planted/decoy source quotes are recovered when labels are absent. See [`DATA/scratchpad/SCHEMA.md`](DATA/scratchpad/SCHEMA.md) and the three scratchpad charts in `CHARTS/`.
