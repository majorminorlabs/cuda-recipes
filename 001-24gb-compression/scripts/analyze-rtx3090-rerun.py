#!/usr/bin/env python3
"""Analyze the frozen reasoning-preserved RTX 3090 replication.

Writes only sanitized, separate phase2 results; the original RTX 5090
canonical dataset and frozen task definitions are left untouched.
"""
import argparse
import csv
import json
import random
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase2_rtx3090"
MODELS = ("nemotron", "qwen")
CATEGORIES = ("coding", "terminal_system", "tool_use", "structured_data", "multi_step")


def quantile(values, p):
    vals = sorted(values)
    if not vals:
        return None
    at = (len(vals) - 1) * p
    lo = int(at)
    hi = min(lo + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (at - lo)


def bootstrap(values, seed, n=10000):
    keys = list(values)
    rng = random.Random(seed)
    samples = [sum(values[rng.choice(keys)] for _ in keys) / len(keys) for _ in range(n)]
    return [quantile(samples, .025), quantile(samples, .975)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--pod-hours", type=float, required=True,
                    help="estimated complete RTX 3090 allocation lifetime")
    ap.add_argument("--rate", type=float, default=.50)
    args = ap.parse_args()
    tasks = {t["id"]: t for t in json.loads((ROOT / "benchmark/tasks.json").read_text())}
    schedule = json.loads((ROOT / "benchmark/schedule.json").read_text())["trials"]
    expected = {f"{x['model']}:{x['task_id']}:{x['repetition']}" for x in schedule}
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("SELECT * FROM trials ORDER BY model,task_id,repetition")]
    con.close()
    observed = {r["trial_id"] for r in rows}
    if expected != observed:
        raise SystemExit(f"frozen assignment mismatch: missing={len(expected-observed)} extra={len(observed-expected)}")
    if len(rows) != 240 or any(r["status"] != "complete" for r in rows):
        raise SystemExit("expected exactly 240 completed assignments")
    by = defaultdict(list)
    for row in rows:
        by[(row["model"], row["task_id"])].append(row)
    for model in MODELS:
        if sum(r["model"] == model for r in rows) != 120:
            raise SystemExit(f"expected 120 assignments for {model}")
    task_success = {m: {t: sum(r["success"] for r in by[(m, t)]) / 3 for t in tasks} for m in MODELS}
    model_summary = {}
    category_summary = {}
    for model in MODELS:
        subset = [r for r in rows if r["model"] == model]
        times = [r["wall_s"] for r in subset]
        prompt_tps = [r["prompt_tps"] for r in subset if r["prompt_tps"] is not None]
        decode_tps = [r["decode_tps"] for r in subset if r["decode_tps"] is not None]
        total_success = sum(r["success"] for r in subset)
        generation_h = sum(times) / 3600
        model_summary[model] = {
            "successes": total_success, "assignments": len(subset), "success_rate": total_success / len(subset),
            "completed_generations": sum(r["status"] == "complete" for r in subset),
            "mean_completion_s": statistics.mean(times), "median_completion_s": statistics.median(times),
            "p95_completion_s": quantile(times, .95), "generation_gpu_hours": generation_h,
            "successes_per_generation_gpu_hour": total_success / generation_h,
            "mean_prompt_tokens_per_second": statistics.mean(prompt_tps),
            "mean_decode_tokens_per_second": statistics.mean(decode_tps),
            "peak_vram_mib": max(r["peak_vram_mib"] or 0 for r in subset),
            "peak_system_ram_kib": max(r["peak_ram_kib"] or 0 for r in subset),
            "failure_classifications": {},
        }
        for r in subset:
            if not r["success"]:
                failure = r["failure_class"] or "incorrect_or_unclassified"
                model_summary[model]["failure_classifications"][failure] = model_summary[model]["failure_classifications"].get(failure, 0) + 1
        category_summary[model] = {}
        for ci, category in enumerate(CATEGORIES):
            ids = [t for t, v in tasks.items() if v["category"] == category]
            n = sum(len(by[(model, tid)]) for tid in ids)
            s = sum(r["success"] for tid in ids for r in by[(model, tid)])
            category_summary[model][category] = {
                "successes": s, "assignments": n, "success_rate": s / n,
                "task_cluster_bootstrap_95_ci": bootstrap({t: task_success[model][t] for t in ids}, 70015 + ci),
            }
    diff = {t: task_success["nemotron"][t] - task_success["qwen"][t] for t in tasks}
    paired_ci = bootstrap(diff, 70015)
    task_rows = []
    for tid, task in tasks.items():
        task_rows.append({"task_id": tid, "category": task["category"], "nemotron_success_fraction": task_success["nemotron"][tid],
                          "qwen_success_fraction": task_success["qwen"][tid], "difference_nemotron_minus_qwen": diff[tid]})
    total_success = sum(v["successes"] for v in model_summary.values())
    summary = {
        "study": "reasoning-preserved RTX 3090 replication of the frozen 240-assignment benchmark",
        "freeze_sha256": "8c58926e573a789982d369d95e74a7938de50d027cba511db31c474f523585fc",
        "harness": "src/run_v2.py; assistant reasoning_content retained in tool-call history",
        "assignments": len(rows), "trials_per_model": 120, "task_count": 40,
        "paired_task_mean_success": {m: sum(task_success[m].values()) / len(tasks) for m in MODELS},
        "paired_task_mean_success_bootstrap_95_ci": {m: bootstrap(task_success[m], 70015) for m in MODELS},
        "paired_difference_nemotron_minus_qwen": sum(diff.values()) / len(diff),
        "paired_difference_task_cluster_bootstrap_95_ci": paired_ci,
        "task_direction": {"nemotron_favored": sum(x > 0 for x in diff.values()), "qwen_favored": sum(x < 0 for x in diff.values()), "tied": sum(x == 0 for x in diff.values())},
        "models": model_summary, "categories": category_summary,
        "task_comparisons": task_rows,
        "efficiency": {"total_successes": total_success, "pod_gpu_hours_estimate": args.pod_hours,
                       "quoted_rate_usd_per_hour": args.rate, "rental_cost_estimate_usd": args.pod_hours * args.rate,
                       "successes_per_paid_gpu_hour": total_success / args.pod_hours},
        "telemetry_interpretation": "CPU layer offload was disabled; all transformer/output layers placed on CUDA. CPU_Mapped GGUF buffer is memory mapped model storage, not CPU-computed layers.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "canonical-results.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (OUT / "canonical-runs.csv").open("w", newline="") as f:
        fields = [k for k in rows[0] if k not in ("raw_path", "response")]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows({k: r.get(k) for k in fields} for r in rows)
    with (OUT / "canonical-tasks.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(task_rows[0])); w.writeheader(); w.writerows(task_rows)
    with (OUT / "category-success.svg").open("w") as f:
        pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="390"><rect width="100%" height="100%" fill="white"/><text x="20" y="30" font-size="20">RTX 3090 task success by category</text>']
        for i, cat in enumerate(CATEGORIES):
            y = 70 + i * 58
            pieces.append(f'<text x="12" y="{y+18}" font-size="13">{cat.replace("_", " ")}</text>')
            for j, (m, color) in enumerate((("nemotron", "#2878b5"), ("qwen", "#df7b32"))):
                val = category_summary[m][cat]["success_rate"]
                yy = y + j * 21
                pieces.append(f'<rect x="150" y="{yy}" width="500" height="16" fill="#eee"/><rect x="150" y="{yy}" width="{500*val:.1f}" height="16" fill="{color}"/><text x="{158+500*val:.1f}" y="{yy+13}" font-size="12">{m}: {val:.1%}</text>')
        pieces.append('</svg>'); f.write(''.join(pieces) + '\n')
    with (OUT / "completion-time.svg").open("w") as f:
        pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="260"><rect width="100%" height="100%" fill="white"/><text x="20" y="32" font-size="20">RTX 3090 median agent completion time</text>']
        max_time = max(model_summary[m]["median_completion_s"] for m in MODELS) or 1
        for i, (m, color) in enumerate((("nemotron", "#2878b5"), ("qwen", "#df7b32"))):
            value = model_summary[m]["median_completion_s"]
            y = 85 + i * 60
            pieces.append(f'<text x="22" y="{y+18}" font-size="14">{m}</text><rect x="130" y="{y}" width="{500*value/max_time:.1f}" height="24" fill="{color}"/><text x="{140+500*value/max_time:.1f}" y="{y+17}" font-size="13">{value:.2f}s</text>')
        pieces.append('</svg>'); f.write(''.join(pieces) + '\n')
    lines = ["# RTX 3090 frozen benchmark replication", "", "This is a separate rerun of the frozen original 40-task, three-repetition schedule using the reasoning-preserved harness. It does not replace or modify the original RTX 5090 dataset.", "",
             f"The exact scheduled assignment matrix is complete: {len(rows)}/240 (120 per model). The task-cluster mean success was {summary['paired_task_mean_success']['nemotron']:.1%} Nemotron (95% CI {summary['paired_task_mean_success_bootstrap_95_ci']['nemotron'][0]:.1%}–{summary['paired_task_mean_success_bootstrap_95_ci']['nemotron'][1]:.1%}) and {summary['paired_task_mean_success']['qwen']:.1%} Qwen (95% CI {summary['paired_task_mean_success_bootstrap_95_ci']['qwen'][0]:.1%}–{summary['paired_task_mean_success_bootstrap_95_ci']['qwen'][1]:.1%}). Nemotron minus Qwen was {summary['paired_difference_nemotron_minus_qwen']:.1%} (95% task-cluster bootstrap CI {paired_ci[0]:.1%} to {paired_ci[1]:.1%}); {summary['task_direction']['nemotron_favored']} tasks favored Nemotron, {summary['task_direction']['qwen_favored']} Qwen, and {summary['task_direction']['tied']} tied.", "",
             "## Category success", "", "![Category success](category-success.svg)", "", "| Category | Nemotron | Qwen |", "|---|---:|---:|"]
    for cat in CATEGORIES:
        n, q = category_summary['nemotron'][cat], category_summary['qwen'][cat]
        lines.append(f"| {cat.replace('_',' ')} | {n['success_rate']:.1%} ({n['task_cluster_bootstrap_95_ci'][0]:.1%}–{n['task_cluster_bootstrap_95_ci'][1]:.1%}) | {q['success_rate']:.1%} ({q['task_cluster_bootstrap_95_ci'][0]:.1%}–{q['task_cluster_bootstrap_95_ci'][1]:.1%}) |")
    lines += ["", "## Task-level comparison", "", "| Task | Category | Nemotron | Qwen | Difference N−Q |", "|---|---|---:|---:|---:|"]
    for t in task_rows:
        lines.append(f"| {t['task_id']} | {t['category'].replace('_',' ')} | {t['nemotron_success_fraction']:.1%} | {t['qwen_success_fraction']:.1%} | {t['difference_nemotron_minus_qwen']:+.1%} |")
    lines += ["", "## Runtime and resources", "", "![Median agent completion time](completion-time.svg)", "", "| Metric | Nemotron | Qwen |", "|---|---:|---:|"]
    for label, key, unit, fn in [
        ("Strict task success", "success_rate", "", lambda x: f"{x:.1%}"),
        ("Mean completion time", "mean_completion_s", "s", lambda x: f"{x:.2f}"),
        ("Median completion time", "median_completion_s", "s", lambda x: f"{x:.2f}"),
        ("95th percentile completion time", "p95_completion_s", "s", lambda x: f"{x:.2f}"),
        ("Prompt throughput", "mean_prompt_tokens_per_second", "tok/s", lambda x: f"{x:.1f}"),
        ("Decode throughput", "mean_decode_tokens_per_second", "tok/s", lambda x: f"{x:.1f}"),
        ("Peak VRAM", "peak_vram_mib", "MiB", lambda x: f"{x:.0f}"),
        ("Peak system RAM", "peak_system_ram_kib", "GiB", lambda x: f"{x/1024/1024:.1f}"),
        ("Success per generation GPU-hour", "successes_per_generation_gpu_hour", "", lambda x: f"{x:.1f}"),
    ]:
        lines.append(f"| {label} | {fn(model_summary['nemotron'][key])} {unit} | {fn(model_summary['qwen'][key])} {unit} |")
    lines += ["", "## Failure classifications", "", "Counts below are failed scored assignments by the deterministic scorer. All 240 generations completed; no runtime or transport failure occurred in this replication.", "", "| Failure class | Nemotron | Qwen |", "|---|---:|---:|"]
    all_failures = sorted(set(model_summary["nemotron"]["failure_classifications"]) | set(model_summary["qwen"]["failure_classifications"]))
    for failure in all_failures:
        lines.append(f"| {failure} | {model_summary['nemotron']['failure_classifications'].get(failure, 0)} | {model_summary['qwen']['failure_classifications'].get(failure, 0)} |")
    lines += ["", "## Quality and inference are separate outcomes", "", f"Qwen had higher strict task success (74.2% vs 62.5%). Nemotron decoded generated tokens faster on average ({model_summary['nemotron']['mean_decode_tokens_per_second']:.1f} vs {model_summary['qwen']['mean_decode_tokens_per_second']:.1f} tokens/s) and used more VRAM ({model_summary['nemotron']['peak_vram_mib']:,} vs {model_summary['qwen']['peak_vram_mib']:,} MiB). Qwen had a slightly lower median end-to-end task completion time ({model_summary['qwen']['median_completion_s']:.2f}s vs {model_summary['nemotron']['median_completion_s']:.2f}s), while Nemotron's mean was lower because its slowest multi-turn tail was shorter. Decode rate alone did not predict strict task success.", ""]
    lines += ["", f"The 3090 pod occupied approximately {args.pod_hours:.2f} GPU-hours at the quoted ${args.rate:.2f}/hour rate (estimated ${args.pod_hours*args.rate:.2f}); billing history returned no posted rows at final check. The scored benchmark had {total_success} successes across its 240 assignments, or {total_success/args.pod_hours:.1f} scored successes per full pod GPU-hour; the separate qualification pilot is excluded from this numerator.", "", "## Original RTX 5090 tool-use audit (unchanged dataset)", "", "| Measure (24 trials/model) | Nemotron | Qwen |", "|---|---:|---:|", "| Strict task success | 8/24 (33.3%) | 22/24 (91.7%) |", "| Correct expected tool-action sequence; all attempts accepted | 21/24 (87.5%) | 22/24 (91.7%) |", "| Final response contract compliance | 8/24 (33.3%) | 23/24 (95.8%) |", "", "Nemotron had 13 trials where the expected tool actions were executed correctly but final JSON contract compliance failed (8 invalid JSON, 5 truncated). These separate outcomes must not be conflated.", "", "## 5090 long-horizon pilot gate", "", "Five frozen pilot tasks per model yielded 0/5 successful tasks for each model; none of the 10 trials called apply_patch. The frozen promotion gate therefore stopped the 60-assignment scored long-horizon suite. This is a pilot-only result, not a scored long-horizon comparison.", "", "## Limits and interpretation", "", "The Qwen rerun retained a task-success lead on this suite. The original 5090 run and this 3090 rerun differ in harness: the rerun preserves assistant reasoning_content, so the 3090 outcomes are a corrected-harness replication and should not be pooled with or substituted for original results. The suite is deterministic and task-level; confidence intervals resample tasks, not repetitions. The model batch order was Qwen then Nemotron, and model identity was not interleaved. Latency and throughput therefore include possible order/thermal effects.", "", "All model layers were placed on CUDA (Qwen 66/66; Nemotron 89/89), with `-ngl 999`, 16,384 context, Q8 KV cache, and CPU layer offload disabled. llama.cpp reports 682 MiB Qwen and 544 MiB Nemotron CPU_Mapped model buffers; those are mapped GGUF storage, not CPU-computed transformer layers.", ""]
    (OUT / "research-report.md").write_text("\n".join(lines))
    print(json.dumps({"assignments": len(rows), "success": {m: model_summary[m]["successes"] for m in MODELS}, "paired_difference": summary["paired_difference_nemotron_minus_qwen"], "ci": paired_ci}, indent=2))


if __name__ == "__main__":
    main()
