# Preregistered protocol (draft pending artifact and hardware gates)

## Question

On an identical NVIDIA RTX 5090 32 GB system, does NVIDIA Nemotron 3.5 Bolt 74B-A9B in its official native 2-bit checkpoint achieve higher deterministic task success than Qwen3.8-27B in Q4_K_M?

## Design

Forty fixed tasks: coding 12, terminal/system 8, tool use 8, structured data 6, multi-step execution 6. Each task-model pair receives three independent repetitions (240 scored trials). Every task has a reference state/result and a negative control. Scoring is deterministic, task specific, and evaluator-side. No retries or replacement runs after exposure. On resume, terminal trials are skipped, stale `running` trials are finalized as explicit `interrupted_process` failures with an audit trace noting that no response was persisted, and only unstarted assignments run. An interrupted assignment is never retried.

The five unscored pilots (CO01, TE01, TO01, ST01, MU01) use separate seeds and are additional to the scored denominator. Tool and multi-step tasks use safe, stateful fixture tools through OpenAI-compatible function calls; each trial allows at most six model turns, at most 512 generated tokens per tool turn, and records every call/result. Non-tool tasks allow one response up to 2,048 generated tokens.

## Controls

Same GPU, llama.cpp build, runner, prompt template, context ceiling, and task order. One model loaded at a time, all layers on GPU, Q8_0 KV cache, one slot, 16,384-token context ceiling. Sampling follows official model recommendations: both use temperature 1.0 and top_p 0.95; Nemotron uses top_k 40 (llama.cpp default, recorded explicitly) and Qwen uses top_k 20. Both use a 2,048-token maximum completion. Each task/repetition seed is identical across paired models and frozen in the schedule. No retries or replacement runs after a trial has started; interrupted trials remain unresolved.

## Budget and stopping

GPU-time target 10 hours; hard ceiling 15 GPU-hours inclusive of setup, downloads, pilots, and scored execution. Projected time beyond 15 hours means stop before scored execution and request approval. No additional GPU. Cost is reported from actual provider metering; storage and network charges are separate.

## Validity gates

Before scored freeze: resolve exact model repositories/revisions/files and hashes; verify llama.cpp architecture and CUDA support; prove both models fit entirely in VRAM at common context; validate every scorer against positive reference and negative control; run harness recovery and telemetry checks. Freeze task definitions, scoring, model config, scored seed schedule, engine build and hashes before any scored inference. The five-task pilots use separate seeds, are unscored, and are additional to the 240 scored trials.

## Pre-score amendment

The first unscored Qwen setup pilot exposed an underspecified terminal JSON response shape and a structured-data reference wrapper that did not match the requested direct array. Before any scored trial, terminal prompts were amended to state the required `result` field, task-validated command equivalents were allowlisted for deterministic scoring, and structured-data references were changed to the direct requested JSON value. The benchmark is re-frozen with a new receipt before any scored execution. Pilot outcomes are excluded from all quality estimates.

## Estimands

Primary: task success proportion by model, with paired task-level three-repetition outcomes. Secondary: category success, completion latency, prompt/decode throughput, peak VRAM, peak system RAM, and successful tasks per GPU-hour. Report 95% task-cluster bootstrap intervals (10,000 resamples, frozen seed 70015) for each model's mean task success, category success, and the paired success-rate difference, plus exact discordant task counts. Avoid generalization beyond this task suite and tested configurations.

## Provenance

Capture model file hashes, source revisions, engine commit/build flags, driver/CUDA versions, GPU UUID/model/memory, OS, runner revision, configs, seeds, wall-clock timestamps, token usage, tool traces, outcome, failure class, peak VRAM and host RAM per trial.

## Freeze state

`benchmark/freeze.json` is the authoritative freeze receipt. `src.freeze` may create it only after exact artifact hashes, scorer gates, CUDA build, no-offload loading of both models at the common context, and environment manifests verify. The receipt hashes the task suite, scoring rules, schedules, settings, runner/analysis code, tests, protocol, and runtime manifests.
