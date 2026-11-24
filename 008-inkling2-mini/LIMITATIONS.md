# Limits of the measurements

- Results describe the two named Q4 artifacts, pinned build, recorded RTX 3090 hosts and exact flags. Tensor quantization and training differ; this does not isolate a training-only effect.
- Primary throughput and initial 0/8K depth points have three repetitions. Verified 128K/256K points have one. No confidence interval or broad stability claim is supported for those deep points.
- The deep rerun used a separate host. Cache precision and batch/ubatch also change with depth. The depth points cannot isolate depth as the only cause of a speed change.
- Configured context checks allocate a window and request a short response. Synthetic filled-context decode measures speed. Neither scores recall, retrieval, reasoning or answer quality over the full window.
- Successful tested settings are not an optimized context maximum. No 1M-context experiment is reported.
- Sampled VRAM peaks can miss instantaneous maxima. Host RAM, process residency, provider allocation and cgroup usage are different quantities. No minimum RAM requirement was established.
- The lost supplemental summaries lack recovered raw evidence and are provisional. Incomplete initial 128K attempts have no rate. The verified rerun replaces those observations.
- One refusal prompt is a behavioral observation. No scored accuracy, perplexity or vision suite was run.
