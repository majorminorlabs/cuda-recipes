# Limitations

- **Synthetic facts in real text.** Planted facts make answers verifiable and uncontaminated, but may be easier or harder to find than information in real documents.
- **Narrow task set.** Retrieval, aggregation and multi-hop over prose; not code, long conversations or summarization quality.
- **Single sample per question.** Each question runs once per model with a fixed seed.
- **Small cells.** 15 questions per model, length and task type, so one question is 6.7 points. Differences of one or two questions between models are within noise.
- **Thinking off.** The primary results use each model's non-thinking mode. Thinking might help multi-hop and counting, but in the exploratory run it consumed the token budget before answering (see DATA/exploratory-thinking-on/).
- **Small synthetic name vocabulary.** Entity names use a small syllable set, so near-identical and reversed names (for example, “Havi Lumo” and “Lumo Havi”) can represent distinct entities. This makes counting and chaining harder than in typical real text.
- **Multi-retrieval prompt ambiguity.** The prompt did not specify whether list items should be strings or objects. The primary content score collects normalized answer values and set-compares them; exact-format scores are also retained and published. Aggregation and multi-hop continue to use exact scoring.
- **Exploratory arm limitations.** The Qwen3.6 thinking-on run used a 2,048-token cap, the old strict parser, and no raw-response capture; it cannot be rescored and is not a long-context quality result.
- **Hardware/runtime scope.** One RTX 3090 host, one llama.cpp revision, Q8_0 KV cache, no CPU layer offload and no speculative decoding.
- **Specific GGUF files.** Results apply to the pinned artifacts, not all model quantizations.
- **Dense control documents.** Both arms' control documents contain all facts planted for that length (about 47% planted text for prose and 77% for code). Control is a short, dense version of the task, not a clean short-context baseline; length comparisons should use 64K versus 128K.
- **Dense control documents.** Both arms' control documents contain all facts planted for that length (about 47% planted text for prose and 77% for code). Control is a short, dense version of the task, not a clean short-context baseline; length comparisons should use 64K versus 128K.

## Code arm

- One pinned repository and one language; results may not generalize to other codebases.
- Planted code is synthetic (random identifiers, stub bodies) inside real Django source. This measures finding and tracing code across a large codebase, not code understanding or generation. Random-string identifiers are probably easier to find than real code names. Code-versus-prose differences are not a pure domain effect: repository/text structure, placement, facts and task realization differ between arms. Random-string identifiers are probably easier to find than real code names. Code-versus-prose differences are not a pure domain effect: repository/text structure, placement, facts and task realization differ between arms.
- Thirteen control target facts are above 95%, including five single-retrieval targets; the count excludes decoys. The compact-control boundary fallback previously wrapped early and middle facts after exhausting forward boundaries; the corrected allocator keeps control insertions monotonic and constrains single-retrieval targets to their nominal bands. Now 0 of 45 single-retrieval rows are outside their nominal third (early <34%, middle 33–67%, late >66%); actual fractions are published per question.
- Cells contain 15 questions per model, length and task type.
- Multi-retrieval content scoring accepts string or object list items; strict format is reported separately.
- Aggregation call sites and multi-hop links are synthetic and locally verifiable.
