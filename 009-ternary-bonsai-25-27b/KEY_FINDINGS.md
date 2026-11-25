# Key findings

On the frozen 001 task suite, Bonsai PTQ1 plain passed 81 of 120 trials and the MTP quality arm passed 79 of 120. The existing Qwen3.8 27B Q4_K_M result from 001 passed 89 of 120. Bonsai plain's two-trial advantage over its MTP quality arm is small; neither arm matched Qwen's strict success count.

The speed results depend on measurement. In F16 KV `llama-bench` with the Prism build, PTQ1 plain generated at 94.536232 tok/s and the fresh Qwen comparator at 45.972666 tok/s. In a separate fixed-prompt server check, MTP raised generation throughput from 92.92596269119396 to 115.28064754265156 tok/s and recorded 206 accepted drafts out of 506 draft tokens. It lowered prompt throughput and used more VRAM in this check.

Bonsai PTQ1 remained measurable at 262144-token filled context after using Q8 KV and batch/ubatch 64/32. Qwen's 262144 attempt failed to allocate the context buffer; the 131072 row completed with reduced batch/ubatch.
