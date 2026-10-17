# Key findings

- At 128K, single-fact retrieval remained relatively strong (11–14/15 per model), while four-fact retrieval fell to 0–4/15. The gap is the clearest result in this task set.
- Qwen3.8 led on 128K single retrieval (14/15); Qwen3.6 led on 128K four-fact retrieval (4/15). No model exceeded 3/15 on 128K multi-hop.
- Multi-retrieval content scoring matters: the prompt left list-item type undefined. After rescoring answer values independent of object-vs-string representation, the expected content counts were Qwen3.6 15/15, 6/15, 4/15; Nemotron 15/15, 7/15, 3/15; and Qwen3.8 13/15, 3/15, 0/15 for control, 64K and 128K.
- The thinking-on Qwen3.6 arm is budget-bound and separate. Its high generation cap confounded context quality with long reasoning/output.

See [RESULTS.md](RESULTS.md) for all task-level accuracy, position, speed and cost numbers, and [CHARTS](CHARTS/) for figures.
