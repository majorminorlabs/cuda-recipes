# Key findings

- **Context ceiling:** Nemotron loaded all 89/89 layers at 262,144 tokens, its native maximum, with 2,210 MiB of card headroom. Qwen loaded all 66/66 layers through 221,184 tokens; 229,376 failed, leaving 782 MiB at the ceiling load.
- **KV cache:** Qwen's attention KV allocation was exactly 8× Nemotron's at matching windows: 544 MiB versus 68.01 MiB at 16K, about 34,816 versus 4,353 bytes per token.
- **Decode:** Nemotron was faster at every measured depth. Its decode speed retained 75.30% at 65,536, 60.20% at 131,072 and 44.95% at ceiling90. Qwen retained 70.98%, 55.04% and 44.01% respectively.
- **Prompt processing crossover:** Qwen led at depth zero (1,236.9 vs 821.9 tok/s mean). Nemotron led at 65,536, 131,072 and ceiling90; at 131,072 the rates were 671.5 vs 449.8 tok/s.
- **VRAM sanity:** successful-load buffer totals were 269–334 MiB below measured peak VRAM, a plausible runtime overhead range. No successful row was outside it.

These are fit + speed results only; they do not establish long-context answer quality. Fill was synthetic llama-bench input, with one run per depth above zero. Hardware and measurement differences mean the 001 and 002 speed figures are not directly comparable.
