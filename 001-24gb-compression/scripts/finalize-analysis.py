#!/usr/bin/env python3
"""Generate the final, sanitized analysis from a synced checkpoint database.

This post-run step adds experiment-wide paid-hour accounting and separates a
single HTTP failure from model-response success. It does not alter frozen task
definitions, trial scores, or the pre-run analyzer included in the freeze.
"""
import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True, help="synced private SQLite checkpoint database")
parser.add_argument("--gpu-hours", required=True, type=float,
                    help="complete single-GPU pod lifetime, including preparation and pilots")
parser.add_argument("--hourly-rate", required=True, type=float,
                    help="provider-returned hourly rate in USD")
args = parser.parse_args()
if args.gpu_hours <= 0 or args.hourly_rate < 0:
    raise SystemExit("GPU hours must be positive and hourly rate cannot be negative")

subprocess.run([sys.executable, "-m", "src.analyze", "--db", args.db,
                "--gpu-hours", str(args.gpu_hours)], cwd=ROOT, check=True)
for csv_name in ("canonical-runs.csv", "canonical-tasks.csv"):
    csv_path = ROOT / "results" / csv_name
    csv_path.write_bytes(csv_path.read_bytes().replace(b"\r\n", b"\n"))
db = sqlite3.connect(args.db)
by_model = {}
for model, assigned, successes, complete in db.execute(
        "SELECT model,COUNT(*),SUM(success),SUM(status='complete') FROM trials GROUP BY model"):
    by_model[model] = {"assigned": assigned, "successes": successes,
                       "completed_generations": complete,
                       "success_rate_on_completed_generations": successes / complete}
total_successes = sum(x["successes"] for x in by_model.values())
db.close()

results_path = ROOT / "results/canonical-results.json"
summary = json.loads(results_path.read_text())
for performance in summary["performance"].values():
    performance.pop("successful_trials_per_paid_gpu_hour", None)
summary["completed_generation_success"] = by_model
summary["experiment_efficiency"] = {
    "successful_assignments": total_successes,
    "paid_gpu_hours_estimate": args.gpu_hours,
    "successful_assignments_per_paid_gpu_hour": total_successes / args.gpu_hours,
    "allocation": "combined experiment total; shared costs are not assigned per model",
}
results_path.write_text(json.dumps(summary, indent=2) + "\n")

report_path = ROOT / "publication/research-report.md"
report = report_path.read_text()
qwen = by_model["qwen"]
nemotron = by_model["nemotron"]
assigned = {model: values["successes"] / values["assigned"] for model, values in by_model.items()}
report = report.replace(
    "The benchmark contains 240 terminal trial records across 40 fixed tasks, with three scheduled repetitions per model and task. Overall assigned-trial success was 54.2% for Nemotron and 70.0% for Qwen.",
    f"The benchmark contains 240 terminal trial records across 40 fixed tasks, with three scheduled repetitions per model and task. Overall assigned-trial success was {assigned['nemotron']:.1%} for Nemotron and {assigned['qwen']:.1%} for Qwen. On completed generations alone, Qwen passed {qwen['successes']}/{qwen['completed_generations']} ({qwen['success_rate_on_completed_generations']:.1%}) and Nemotron passed {nemotron['successes']}/{nemotron['completed_generations']} ({nemotron['success_rate_on_completed_generations']:.1%}); the one Qwen HTTP failure remains a runtime failure in the primary denominator.")
report = report.replace("| Successful trials per paid GPU-hour | 74.7 | 96.6 |\n", "")
report = report.replace(
    "Completion time is per assigned trial and includes all model/tool turns. Generation GPU-hours sum trial execution wall time; paid GPU-hours include provider uptime for the complete experiment.",
    f"Completion time is per assigned trial and includes all model/tool turns. Generation GPU-hours sum each model's trial execution wall time. The complete study produced {total_successes} successful assignments in approximately {args.gpu_hours:.2f} paid GPU-hours, or {total_successes/args.gpu_hours:.1f} successes per paid GPU-hour across the experiment. Paid startup, build, model-load, pilot, and scored time is shared, so it is not allocated to each model separately.")
old_tail = "Paid GPU time recorded for this run: "
idx = report.rfind(old_tail)
if idx < 0:
    raise SystemExit("expected frozen analyzer report tail not found")
report = report[:idx]
report += (
    f"The single-GPU pod occupied approximately {args.gpu_hours:.2f} hours from creation through deletion. "
    f"At the provider-returned rate of ${args.hourly_rate:.2f}/hour, the rental cost estimate is "
    f"${args.gpu_hours * args.hourly_rate:.2f}; the provider billing query returned no posted usage rows at final check, "
    "so this is an estimate rather than an invoice total. The study stayed below the 10 GPU-hour target and 15 GPU-hour cap.\n\n"
    "To avoid reloading a 16–22 GiB model between paired repetitions, the full Qwen batch ran before the full Nemotron batch. "
    "Within each batch, task order follows the same frozen paired schedule. Model identity was not interleaved, so unmeasured "
    "time- or thermal-order effects cannot be ruled out for latency and throughput comparisons.\n\n"
    "The container's CUDA 13 compatibility library initially failed to initialize on the host's 570.195.03 driver. The same "
    "llama.cpp revision was rebuilt with CUDA Toolkit 12.8.93, and both all-GPU model placements were then verified. NVIDIA's "
    "compatibility table lists CUDA 13.x with a minimum R580 driver and identifies CUDA 12.8 for Blackwell support "
    "([driver compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html), "
    "[Blackwell compatibility guide](https://docs.nvidia.com/cuda/archive/12.8.0/Blackwell_Compatibility_Guide.pdf)).\n\n"
    "## Model references\n\n"
    "- [NVIDIA Nemotron 3.5 Bolt official GGUF repository](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF/tree/e0fecb69cb3e5e4c5e8a056fa2aec98c78e91246).\n"
    "- [Qwen3.8-27B official upstream model](https://huggingface.co/Qwen/Qwen3.8-27B/tree/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0) and [pinned Q4_K_M GGUF conversion](https://huggingface.co/Abiray/Qwen3.8-27B-Q4_K_M-GGUF/tree/f7a1cda580fe828415151042bf9f3dc5bb8b0d76).\n"
    "- Exact artifact hashes, template checks, and conversion notes are listed in `models/manifest.json`.\n"
)
report_path.write_text(report)
print(json.dumps({"successful_assignments": total_successes,
                  "successes_per_paid_gpu_hour": total_successes / args.gpu_hours,
                  "rental_cost_estimate_usd": round(args.gpu_hours * args.hourly_rate, 2)}, indent=2))
