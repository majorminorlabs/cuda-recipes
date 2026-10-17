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
