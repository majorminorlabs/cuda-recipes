#!/usr/bin/env python3
"""Render the local research report from the paired canonical analysis."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results/phase2_hardware_comparison/canonical-results.json'
OUT = ROOT / 'results/phase2_hardware_comparison/research-report.md'
PUB = ROOT / 'publication/phase2-hardware-comparison-report.md'


def pct(x): return f'{100*x:.1f}%'
def ci(x): return f'{pct(x[0])}–{pct(x[1])}'
def nrate(x): return f"{x['successes']}/{x['assignments']} ({pct(x.get('success_rate', x.get('rate')))})"


def render(d):
    s = d['overall_success']
    diffci = d['overall_success_difference_task_cluster_bootstrap_95_ci']
    mm = d['models']
    lines = [
        '# Corrected-harness RTX 3090 vs RTX 5090 benchmark', '',
        '## Result', '',
        f"The paired comparison contains **240 completed assignments per GPU** (120 per model), covering the same 40 tasks, three repetitions, and exact frozen seeds. Strict task success was **{nrate(s['rtx3090'])}** on RTX 3090 and **{nrate(s['rtx5090'])}** on RTX 5090. The paired task-cluster difference (RTX 5090 minus RTX 3090) was **{pct(d['overall_success_difference_5090_minus_3090'])}** (95% bootstrap CI **{ci(diffci)}**). The interval includes zero; these results do not establish a success-rate advantage for either GPU.", '',
        'The 5090 completed trials faster and sustained higher prompt and decode throughput for both models. Qwen retained higher strict task success than Nemotron on both GPUs. These are separate observations: inference speed changed substantially, while success-rate differences were small and uncertain.', '',
        '## Exact paired outcomes', '',
        '| Model | RTX 3090 strict success | RTX 5090 strict success | Paired task-rate delta (5090−3090), 95% task-cluster CI | Tasks favor 3090 / favor 5090 / tied | Exact assignment agreement |',
        '|---|---:|---:|---:|---:|---:|'
    ]
    for m in ('nemotron', 'qwen'):
        delta = d['model_hardware_differences'][m]
        a = mm['rtx3090'][m]; b = mm['rtx5090'][m]
        ag = d['task_level_agreement'][m]
        lines.append(f"| {m.title()} | {nrate(a)} | {nrate(b)} | {pct(delta['success_rate_difference_5090_minus_3090'])} ({ci(delta['task_cluster_bootstrap_95_ci'])}) | {delta['tasks_favoring_3090']} / {delta['tasks_favoring_5090']} / {delta['tasks_tied']} | {ag['exact_outcome_agreement']}/{ag['paired_assignments']} ({pct(ag['agreement_rate'])}; κ={ag['cohen_kappa']:.2f}) |")
    agree = d['task_level_agreement']
    lines += ['',
        f"Across both models, **{sum(agree[m]['exact_outcome_agreement'] for m in agree)}/240 ({pct(sum(agree[m]['exact_outcome_agreement'] for m in agree)/240)})** paired task/repetition outcomes agreed. There were {sum(agree[m]['3090_only_success'] for m in agree)} 3090-only successes and {sum(agree[m]['5090_only_success'] for m in agree)} 5090-only successes. Agreement is not identity of generated text or tool traces.", '',
        '## Success by category', '',
        '| Category | Nemotron 3090 | Nemotron 5090 | Qwen 3090 | Qwen 5090 |',
        '|---|---:|---:|---:|---:|'
    ]
    for cat in ('coding','terminal_system','tool_use','structured_data','multi_step'):
        vals = [d['categories'][g][m][cat] for m in ('nemotron','qwen') for g in ('rtx3090','rtx5090')]
        lines.append(f"| {cat.replace('_',' ').title()} | {nrate(vals[0])} | {nrate(vals[1])} | {nrate(vals[2])} | {nrate(vals[3])} |")
    lines += ['', '![Task success by category and GPU](phase2-hardware-success.svg)', '',
        'The category estimates are based on only 4–12 tasks per category. Confidence intervals use 20,000 task-cluster bootstrap resamples with fixed seeds. The canonical JSON includes intervals for each model/GPU/category, and `task-comparisons.csv` preserves each task’s success counts.', '',
        '## Inference performance and resources', '',
        '| GPU | Model | Mean / median / p95 completion (s) | Prompt tok/s | Decode tok/s | Peak VRAM (MiB) | Peak container RAM (GiB) |',
        '|---|---|---:|---:|---:|---:|---:|']
    for g in ('rtx3090','rtx5090'):
        for m in ('nemotron','qwen'):
            x = mm[g][m]
            lines.append(f"| {g.upper()} | {m.title()} | {x['mean_completion_s']:.2f} / {x['median_completion_s']:.2f} / {x['p95_completion_s']:.2f} | {x['mean_prompt_tokens_per_second']:.1f} | {x['mean_decode_tokens_per_second']:.1f} | {x['peak_vram_mib']:,} | {x['peak_system_ram_gib']:.2f} |")
    lines += ['', '![Median completion latency](phase2-hardware-latency.svg)', '',
        'Trial latency includes the model’s complete response and any tool turns. Throughput is the arithmetic mean of per-trial measurements. Generation GPU-hours sum trial wall time; full pod allocation also includes bootstrap, model load, build, qualification, and evidence transfer.', '',
        'At 16K context and no CPU layer offload, peak VRAM increased from 21,339 to 21,865 MiB for Nemotron and from 16,481 to 16,514 MiB for Qwen. The RTX 5090 run placed 89/89 Nemotron layers and 66/66 Qwen layers on CUDA. Its 544 MiB and 682 MiB `CPU_Mapped` buffers are file-backed model storage, not CPU layer execution.', '',
        '## Paired outcome investigation', '',
        'There were 33 assignment-level outcome flips across 240 pairs. Most task/repetition results agreed, and no trial failed to load, ran out of VRAM, or used CPU layer offload. The score differences arose from response and tool-action differences under the unchanged deterministic scorer:', '',
        '- On Qwen coding task CO11 repetition 1, the RTX 5090 response used a conditional expression (`... if words else None`). It is semantically equivalent on the task’s cases, but the frozen restricted-Python scorer’s AST allowlist rejects conditional expressions. The 3090 response used an allowed `if` statement. Scoring was left unchanged.',
        '- On Qwen tool task TO05 repetition 2, both final responses were `{"done":true}`. The 3090 trace made the single expected query. The 5090 trace first made two syntactically different, out-of-order query attempts, then recovered; the scorer requires the exact expected tool action sequence, so it failed.',
        '- Other changes include coding cases rejected by the same restricted scorer, terminal command differences, and truncated or malformed tool calls. `outcome-disagreements.csv` lists all 33 flips and their frozen failure classes; internal raw traces contain the full histories.', '',
        'These examples show why equal seeds do not guarantee identical sampled token sequences across different compiled GPU architectures. They do not show that the GPU alone caused the success-rate difference. The RTX 3090 and RTX 5090 used different CUDA targets (sm_86 vs sm_120a), different NVIDIA drivers (580.126.20 vs 570.195.03), and separate provider nodes. Model sampling is stochastic, and the study did not interleave model batches across nodes or repeat each hardware condition. Small numerical changes, runtime environment, and sampling variation remain confounded.', '',
        'The task-cluster confidence intervals for the paired success differences include zero for both models and overall. The observed 3.75 percentage-point lower aggregate success on the 5090 is therefore not evidence of a stable GPU-quality effect. Across both hardware runs, Qwen’s strict success exceeded Nemotron’s by 11.7 points on the 3090 and 10.8 points on the 5090; this fixed benchmark alone does not support a broader model-quality claim.', '',
        '## Failure classes', '',
        '| Model / GPU | Failure classifications among unsuccessful assignments |', '|---|---|']
    for g in ('rtx3090','rtx5090'):
        for m in ('nemotron','qwen'):
            fs = ', '.join(f'{k}: {v}' for k,v in sorted(mm[g][m]['failure_classifications'].items()))
            lines.append(f'| {m.title()} / {g.upper()} | {fs} |')
    lines += ['', '## Paid runtime and cost', '', '| GPU | Allocated GPU hours | Quoted rate | Estimated rental | Total successes | Successes per paid GPU-hour |', '|---|---:|---:|---:|---:|---:|']
    for g in ('rtx3090','rtx5090'):
        p = d['paid_efficiency'][g]
        lines.append(f"| {g.upper()} | {p['pod_gpu_hours_estimate']:.3f} | ${p['quoted_rate_usd_per_hour']:.2f}/h | ${p['rental_cost_estimate_usd']:.2f} | {s[g]['successes']}/240 | {p['all_model_successes_per_paid_gpu_hour']:.1f} |")
    p3090, p5090 = d['paid_efficiency']['rtx3090'], d['paid_efficiency']['rtx5090']
    lines += ['',
        f"The 5090 run used {sum(x['generation_gpu_hours'] for x in mm['rtx5090'].values()):.3f} GPU-hours for actual generation versus {sum(x['generation_gpu_hours'] for x in mm['rtx3090'].values()):.3f} on the 3090. It was faster and delivered more successes per allocated GPU-hour, but its hourly rate was higher and its absolute rental estimate was ${p5090['rental_cost_estimate_usd']:.2f} versus ${p3090['rental_cost_estimate_usd']:.2f}. Provider billing history returned no row for the corrected pod at final check; these are estimates from the quoted rate and provider-reported uptime, not invoice totals.", '',
        '## Equivalence, artifacts, and limits', '',
        'The frozen comparison used the identical task suite, reference solutions, negative controls, scoring code, assignment IDs and seeds, model artifact hashes, model sampling settings, context length, KV cache, layer-offload policy, per-trial generation limits (512 tokens per tool turn, 2,048 tokens for single-turn tasks, six tool turns), llama.cpp commit, runner, and model execution order. The reasoning-history regression test passed before scored execution. Both GPUs passed only the required model-load and structured tool-call qualification smoke; the previously failed long-horizon pilot was not repeated. The paid allocation caps were authorization-specific: 3 hours for the earlier RTX 3090 run and 2 hours for this RTX 5090 correction; neither run approached its cap. Both existing databases remained unchanged; the RTX 5090 result is a third independent dataset.', '',
        'The declared unavoidable differences were GPU model and VRAM, CUDA compilation target, host driver, and provider node. Both used CUDA Toolkit 12.8.93, Python 3.12.3, PyTorch 2.9.1+cu128, and the same llama.cpp commit. Full parity receipts and SHA-256 records are in the frozen config and sanitized manifests. Private databases, 240 raw traces, and operational logs remain outside the repository.', '',
        'The benchmark uses a small fixed text-only workload and deterministic outcome scorers. Confidence intervals resample tasks, not individual tokens. Results characterize these artifacts, settings, and tasks; they do not isolate a causal hardware effect or predict all workloads.', '',
        '## Reproducibility files', '',
        '- `results/phase2_rtx5090_corrected/` — sanitized standalone 5090 canonical results and execution receipt.',
        '- `results/phase2_hardware_comparison/` — paired runs, per-task comparisons, all outcome flips, validation, and figures.',
        '- `benchmark/rtx5090_v1/` — frozen 5090 config, budget, freeze receipt, and parity verifier.',
        '- `manifests/rtx5090-corrected-public.json` — sanitized hardware and runtime manifest.',
        '- `docs/REPRODUCE_PHASE2.md` — repeat and compare instructions.', '',
        'No results have been pushed or published.'
    ]
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    report = render(json.loads(DATA.read_text()))
    OUT.write_text(report)
    PUB.write_text(report)
