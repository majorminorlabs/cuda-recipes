#!/usr/bin/env python3
"""Pair corrected-harness RTX 3090 and RTX 5090 datasets without mutation."""
import argparse
import csv
import hashlib
import json
import random
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase2_hardware_comparison"
OUT5090 = ROOT / "results" / "phase2_rtx5090_corrected"
MODELS = ("nemotron", "qwen")
CATEGORIES = ("coding", "terminal_system", "tool_use", "structured_data", "multi_step")
HARDWARE = ("rtx3090", "rtx5090")


def quantile(values, p):
    vals = sorted(values)
    if not vals:
        return None
    at = (len(vals) - 1) * p
    lo = int(at)
    hi = min(lo + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (at - lo)


def cluster_ci(values, seed, n=20000):
    keys = list(values)
    rng = random.Random(seed)
    means = [sum(values[rng.choice(keys)] for _ in keys) / len(keys) for _ in range(n)]
    return [quantile(means, .025), quantile(means, .975)]


def read_db(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    rows = [dict(r) for r in con.execute("SELECT * FROM trials ORDER BY model,task_id,repetition")]
    con.close()
    return rows, integrity


def wilson(successes, n):
    # Simple Wilson score interval, useful as a descriptive assignment-level CI.
    z = 1.959963984540054
    p = successes / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** .5) / d
    return [mid - half, mid + half]


def model_metrics(rows):
    times = [r["wall_s"] for r in rows]
    prompt = [r["prompt_tps"] for r in rows if r["prompt_tps"] is not None]
    decode = [r["decode_tps"] for r in rows if r["decode_tps"] is not None]
    successes = sum(r["success"] for r in rows)
    gen_hours = sum(times) / 3600
    failures = Counter((r["failure_class"] or "incorrect_or_unclassified") for r in rows if not r["success"])
    return {
        "successes": successes, "assignments": len(rows), "success_rate": successes / len(rows),
        "assignment_wilson_95_ci": wilson(successes, len(rows)),
        "mean_completion_s": statistics.mean(times), "median_completion_s": statistics.median(times),
        "p95_completion_s": quantile(times, .95), "generation_gpu_hours": gen_hours,
        "successes_per_generation_gpu_hour": successes / gen_hours,
        "mean_prompt_tokens_per_second": statistics.mean(prompt),
        "mean_decode_tokens_per_second": statistics.mean(decode),
        "mean_peak_vram_mib": statistics.mean(r["peak_vram_mib"] for r in rows if r["peak_vram_mib"] is not None),
        "peak_vram_mib": max(r["peak_vram_mib"] or 0 for r in rows),
        "mean_peak_system_ram_gib": statistics.mean((r["peak_ram_kib"] or 0) / 1024 / 1024 for r in rows),
        "peak_system_ram_gib": max((r["peak_ram_kib"] or 0) for r in rows) / 1024 / 1024,
        "failure_classifications": dict(failures),
    }


def agreement(a, b):
    agree = sum(x["success"] == y["success"] for x, y in zip(a, b))
    both_yes = sum(x["success"] == 1 and y["success"] == 1 for x, y in zip(a, b))
    a_only = sum(x["success"] == 1 and y["success"] == 0 for x, y in zip(a, b))
    b_only = sum(x["success"] == 0 and y["success"] == 1 for x, y in zip(a, b))
    both_no = sum(x["success"] == 0 and y["success"] == 0 for x, y in zip(a, b))
    n = len(a)
    observed = agree / n
    p_a = (both_yes + a_only) / n
    p_b = (both_yes + b_only) / n
    p_e = p_a * p_b + (1 - p_a) * (1 - p_b)
    return {"paired_assignments": n, "exact_outcome_agreement": agree, "agreement_rate": observed,
            "both_success": both_yes, "both_fail": both_no, "3090_only_success": a_only,
            "5090_only_success": b_only, "cohen_kappa": (observed - p_e) / (1 - p_e) if p_e < 1 else 1.0}


def write_csv(path, rows, fields):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: r.get(k) for k in fields} for r in rows)


def chart_success(summary):
    colors = {"rtx3090": "#2878b5", "rtx5090": "#df7b32"}
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="940" height="420"><rect width="100%" height="100%" fill="white"/><text x="20" y="32" font-size="21">Task success by category and GPU</text>']
    for i, category in enumerate(CATEGORIES):
        y = 66 + i * 67
        pieces.append(f'<text x="12" y="{y+25}" font-size="13">{category.replace("_", " ")}</text>')
        for j, gpu in enumerate(HARDWARE):
            for k, model in enumerate(MODELS):
                rate = summary["categories"][gpu][model][category]["success_rate"]
                yy = y + (j * 2 + k) * 13
                x = 170
                pieces.append(f'<text x="{x}" y="{yy+11}" font-size="10">{gpu[-4:]} {model}</text><rect x="245" y="{yy}" width="520" height="10" fill="#eee"/><rect x="245" y="{yy}" width="{520*rate:.1f}" height="10" fill="{colors[gpu]}"/><text x="{252+520*rate:.1f}" y="{yy+9}" font-size="10">{rate:.1%}</text>')
    pieces.append('</svg>')
    (OUT / "success-by-category.svg").write_text("".join(pieces) + "\n")


def chart_latency(summary):
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="250"><rect width="100%" height="100%" fill="white"/><text x="20" y="30" font-size="20">Median agent completion latency</text>']
    maxv = max(summary["models"][g][m]["median_completion_s"] for g in HARDWARE for m in MODELS)
    colors = {"rtx3090": "#2878b5", "rtx5090": "#df7b32"}
    i = 0
    for gpu in HARDWARE:
        for model in MODELS:
            val = summary["models"][gpu][model]["median_completion_s"]
            y = 64 + i * 41
            pieces.append(f'<text x="18" y="{y+17}" font-size="12">{gpu} {model}</text><rect x="190" y="{y}" width="{460*val/maxv:.1f}" height="22" fill="{colors[gpu]}"/><text x="{198+460*val/maxv:.1f}" y="{y+16}" font-size="12">{val:.2f}s</text>')
            i += 1
    pieces.append('</svg>')
    (OUT / "completion-latency.svg").write_text("".join(pieces) + "\n")


def write_5090_canonical(rows, tasks, metrics, categories, hours, rate, db_hash):
    per_task = {m: {} for m in MODELS}
    task_rows = []
    for model in MODELS:
        for task_id, task in tasks.items():
            n = sum(r["success"] for r in rows if r["model"] == model and r["task_id"] == task_id)
            per_task[model][task_id] = n / 3
            task_rows.append({"model": model, "task_id": task_id, "category": task["category"], "successes": n,
                "assignments": 3, "success_rate": n / 3})
    summary = {"study": "corrected-harness RTX 5090 run on the frozen 240-trial benchmark",
        "dataset_id": "phase2_corrected_rtx5090_v1", "freeze_sha256": hashlib.sha256((ROOT / "benchmark/rtx5090_v1/freeze.json").read_bytes()).hexdigest(),
        "assignments": len(rows), "trials_per_model": 120, "task_count": len(tasks), "sqlite_integrity": "ok", "database_sha256": db_hash,
        "paired_task_mean_success": {m: statistics.mean(per_task[m].values()) for m in MODELS},
        "paired_task_mean_success_bootstrap_95_ci": {m: cluster_ci(per_task[m], 5090 + i) for i, m in enumerate(MODELS)},
        "models": metrics, "categories": categories, "task_comparisons": task_rows,
        "efficiency": {"total_successes": sum(metrics[m]["successes"] for m in MODELS), "pod_gpu_hours_estimate": hours,
            "quoted_rate_usd_per_hour": rate, "rental_cost_estimate_usd": hours * rate,
            "successes_per_paid_gpu_hour": sum(metrics[m]["successes"] for m in MODELS) / hours},
        "telemetry_interpretation": "All layers were assigned to CUDA; CPU_Mapped GGUF buffers are memory-mapped model storage, not CPU-computed layers."}
    OUT5090.mkdir(parents=True, exist_ok=True)
    (OUT5090 / "canonical-results.json").write_text(json.dumps(summary, indent=2) + "\n")
    fields = [k for k in rows[0] if k not in ("raw_path", "response")]
    write_csv(OUT5090 / "canonical-runs.csv", rows, fields)
    write_csv(OUT5090 / "canonical-tasks.csv", task_rows, list(task_rows[0]))
    (OUT5090 / "validation.json").write_text(json.dumps({"result": "PASS", "assignments": len(rows),
        "assignments_per_model": {m: sum(r["model"] == m for r in rows) for m in MODELS},
        "all_complete": all(r["status"] == "complete" for r in rows), "sqlite_integrity": "ok",
        "paired_schedule_and_seed_equivalence_to_rtx3090": True, "raw_traces": 240,
        "publication": "local only; not published or pushed"}, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-3090", required=True, type=Path)
    ap.add_argument("--db-5090", required=True, type=Path)
    ap.add_argument("--hours-3090", required=True, type=float)
    ap.add_argument("--hours-5090", required=True, type=float)
    ap.add_argument("--rate-3090", default=.50, type=float)
    ap.add_argument("--rate-5090", default=1.19, type=float)
    args = ap.parse_args()
    tasks = {t["id"]: t for t in json.loads((ROOT / "benchmark/tasks.json").read_text())}
    schedule = json.loads((ROOT / "benchmark/schedule.json").read_text())["trials"]
    expected = {(x["model"], x["task_id"], x["repetition"]): x["seed"] for x in schedule}
    rows_by_gpu = {}
    integrity = {}
    hashes = {}
    for gpu, path in (("rtx3090", args.db_3090), ("rtx5090", args.db_5090)):
        rows, integrity[gpu] = read_db(path)
        observed = {(r["model"], r["task_id"], r["repetition"]): r["seed"] for r in rows}
        if observed != expected or len(rows) != 240 or any(r["status"] != "complete" for r in rows):
            raise SystemExit(f"{gpu} schedule mismatch or incomplete database")
        if integrity[gpu] != "ok":
            raise SystemExit(f"{gpu} SQLite integrity failed")
        rows_by_gpu[gpu] = {(r["model"], r["task_id"], r["repetition"]): r for r in rows}
        hashes[gpu] = hashlib.sha256(path.read_bytes()).hexdigest()

    bymodel = {g: {m: [r for r in rows_by_gpu[g].values() if r["model"] == m] for m in MODELS} for g in HARDWARE}
    model_summary = {g: {m: model_metrics(bymodel[g][m]) for m in MODELS} for g in HARDWARE}
    categories = {}
    for gpu in HARDWARE:
        categories[gpu] = {}
        for model in MODELS:
            categories[gpu][model] = {}
            for ci, category in enumerate(CATEGORIES):
                tids = [tid for tid, task in tasks.items() if task["category"] == category]
                task_rates = {tid: sum(rows_by_gpu[gpu][(model, tid, rep)]["success"] for rep in (1, 2, 3)) / 3 for tid in tids}
                count = sum(rows_by_gpu[gpu][(model, tid, rep)]["success"] for tid in tids for rep in (1, 2, 3))
                n = len(tids) * 3
                categories[gpu][model][category] = {"successes": count, "assignments": n, "success_rate": count / n,
                    "task_cluster_bootstrap_95_ci": cluster_ci(task_rates, 43190 + ci)}

    paired = {m: [] for m in MODELS}
    task_comparisons = []
    category_differences = {}
    model_hardware_differences = {}
    for model in MODELS:
        for key in sorted(k for k in expected if k[0] == model):
            a, b = rows_by_gpu["rtx3090"][key], rows_by_gpu["rtx5090"][key]
            if a["seed"] != b["seed"]:
                raise SystemExit(f"seed mismatch for {key}")
            paired[model].append((a, b))
        task_diff = {}
        for tid, task in tasks.items():
            rate3090 = sum(rows_by_gpu["rtx3090"][(model, tid, rep)]["success"] for rep in (1, 2, 3)) / 3
            rate5090 = sum(rows_by_gpu["rtx5090"][(model, tid, rep)]["success"] for rep in (1, 2, 3)) / 3
            task_diff[tid] = rate5090 - rate3090
            task_comparisons.append({"model": model, "task_id": tid, "category": task["category"],
                "rtx3090_successes": int(rate3090 * 3), "rtx5090_successes": int(rate5090 * 3),
                "rtx3090_success_rate": rate3090, "rtx5090_success_rate": rate5090,
                "success_rate_difference_5090_minus_3090": task_diff[tid]})
        category_differences[model] = {}
        model_hardware_differences[model] = {
            "success_rate_difference_5090_minus_3090": statistics.mean(task_diff.values()),
            "task_cluster_bootstrap_95_ci": cluster_ci(task_diff, 43190 + 50),
            "tasks_favoring_3090": sum(v < 0 for v in task_diff.values()),
            "tasks_favoring_5090": sum(v > 0 for v in task_diff.values()),
            "tasks_tied": sum(v == 0 for v in task_diff.values()),
        }
        for ci, category in enumerate(CATEGORIES):
            ids = [tid for tid, task in tasks.items() if task["category"] == category]
            category_differences[model][category] = {
                "difference_5090_minus_3090": statistics.mean(task_diff[tid] for tid in ids),
                "task_cluster_bootstrap_95_ci": cluster_ci({tid: task_diff[tid] for tid in ids}, 43190 + 100 + ci),
            }

    agreement_summary = {m: agreement([x[0] for x in paired[m]], [x[1] for x in paired[m]]) for m in MODELS}
    all_keys = sorted(expected)
    overall_task_diff = {tid: statistics.mean(
        sum(rows_by_gpu[g][(m, tid, rep)]["success"] for m in MODELS for rep in (1, 2, 3)) / 6
        for g in ("rtx5090",)) - statistics.mean(
        sum(rows_by_gpu[g][(m, tid, rep)]["success"] for m in MODELS for rep in (1, 2, 3)) / 6
        for g in ("rtx3090",)) for tid in tasks}
    total_success = {g: sum(r["success"] for r in rows_by_gpu[g].values()) for g in HARDWARE}
    hours = {"rtx3090": args.hours_3090, "rtx5090": args.hours_5090}
    rates = {"rtx3090": args.rate_3090, "rtx5090": args.rate_5090}
    overall_rates = {g: total_success[g] / 240 for g in HARDWARE}
    summary = {
        "study": "paired corrected-harness RTX 3090 versus RTX 5090 comparison",
        "freeze_sha256": {"original": "8c58926e573a789982d369d95e74a7938de50d027cba511db31c474f523585fc",
            "corrected_rtx3090": "38a8c61258efd135b3173f524e52336753e6cd854316c83799d0b6d4d506ffab",
            "corrected_rtx5090": hashlib.sha256((ROOT / "benchmark/rtx5090_v1/freeze.json").read_bytes()).hexdigest()},
        "datasets": {g: {"assignments": 240, "sqlite_integrity": integrity[g], "sha256": hashes[g]} for g in HARDWARE},
        "assignment_schedule_and_seed_equivalence": "PASS: exact model/task/repetition/seed mapping verified",
        "task_count": 40, "trials_per_model_per_gpu": 120,
        "overall_success": {g: {"successes": total_success[g], "assignments": 240, "rate": overall_rates[g],
            "task_cluster_bootstrap_95_ci": cluster_ci({tid: statistics.mean(
                sum(rows_by_gpu[g][(m, tid, rep)]["success"] for m in MODELS for rep in (1, 2, 3)) / 6
                for _ in (0,)) for tid in tasks}, 43190)} for g in HARDWARE},
        "overall_success_difference_5090_minus_3090": statistics.mean(overall_task_diff.values()),
        "overall_success_difference_task_cluster_bootstrap_95_ci": cluster_ci(overall_task_diff, 43190),
        "models": model_summary, "categories": categories, "category_hardware_differences": category_differences,
        "model_hardware_differences": model_hardware_differences,
        "task_level_agreement": agreement_summary, "task_level_comparisons": task_comparisons,
        "hardware": {"rtx3090": {"gpu": "NVIDIA GeForce RTX 3090", "vram_mib": 24576, "driver": "580.126.20", "cuda_toolkit": "12.8.93", "compiled_arch": "86"},
            "rtx5090": {"gpu": "NVIDIA GeForce RTX 5090", "vram_mib": 32607, "driver": "570.195.03", "cuda_toolkit": "12.8.93", "compiled_arch": "120a"}},
        "paid_efficiency": {g: {"pod_gpu_hours_estimate": hours[g], "quoted_rate_usd_per_hour": rates[g],
            "rental_cost_estimate_usd": hours[g] * rates[g], "all_model_successes_per_paid_gpu_hour": total_success[g] / hours[g],
            "per_model_successes_per_paid_gpu_hour": {m: model_summary[g][m]["successes"] / hours[g] for m in MODELS}}
            for g in HARDWARE},
        "interpretation_limits": ["RTX 5090 generation used a separate compiled CUDA architecture and a different NVIDIA driver.",
            "Observed success-rate changes are paired run differences, not causal estimates of GPU effects.",
            "The harness uses identical task prompts, scoring, model artifacts, seeds, sampling, context, KV cache, tool budgets, inference commit, and task order."]}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "canonical-results.json").write_text(json.dumps(summary, indent=2) + "\n")
    run_rows = []
    for gpu in HARDWARE:
        for row in sorted(rows_by_gpu[gpu].values(), key=lambda r: (r["model"], r["task_id"], r["repetition"])):
            run_rows.append({"gpu": gpu, **{k: row.get(k) for k in ("trial_id", "model", "task_id", "repetition", "seed", "status", "success", "wall_s", "prompt_tokens", "completion_tokens", "prompt_tps", "decode_tps", "peak_vram_mib", "peak_ram_kib", "failure_class")}})
    write_csv(OUT / "paired-runs.csv", run_rows, list(run_rows[0]))
    write_csv(OUT / "task-comparisons.csv", task_comparisons, list(task_comparisons[0]))
    disagreements = []
    for model in MODELS:
        for old, new in paired[model]:
            if old["success"] != new["success"]:
                disagreements.append({"model": model, "task_id": old["task_id"], "repetition": old["repetition"],
                    "seed": old["seed"], "rtx3090_success": old["success"], "rtx5090_success": new["success"],
                    "rtx3090_failure_class": old["failure_class"], "rtx5090_failure_class": new["failure_class"]})
    write_csv(OUT / "outcome-disagreements.csv", disagreements, list(disagreements[0]))
    chart_success(summary)
    chart_latency(summary)
    (OUT / "validation.json").write_text(json.dumps({"result": "PASS", "dataset_count": 2,
        "assignments_per_dataset": 240, "exact_seed_schedule_match": True, "sqlite_integrity": integrity,
        "raw_traces": "private datasets each contain 240 traces; not included in the public package",
        "publication": "local only; not published or pushed"}, indent=2) + "\n")
    rows5090 = list(rows_by_gpu["rtx5090"].values())
    cats5090 = categories["rtx5090"]
    write_5090_canonical(rows5090, tasks, model_summary["rtx5090"], cats5090, args.hours_5090, args.rate_5090, hashes["rtx5090"])
    print(json.dumps({"overall_success": summary["overall_success"], "difference": summary["overall_success_difference_5090_minus_3090"],
        "agreement": agreement_summary, "cost": summary["paid_efficiency"]}, indent=2))


if __name__ == "__main__":
    main()
