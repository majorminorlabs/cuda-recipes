#!/usr/bin/env python3
"""Compute experiment-wide success per paid GPU-hour from the checkpoint DB."""
import argparse
import json
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--gpu-hours", required=True, type=float,
                    help="complete experiment pod lifetime in GPU-hours")
args = parser.parse_args()
db = sqlite3.connect(args.db)
rows = db.execute("SELECT model, COUNT(*), SUM(success) FROM trials GROUP BY model ORDER BY model").fetchall()
if not rows or args.gpu_hours <= 0:
    raise SystemExit("database must contain terminal trials and gpu-hours must be positive")
total = sum(successes for _, _, successes in rows)
out = {
    "by_model": {model: {"assigned": assigned, "successes": successes}
                 for model, assigned, successes in rows},
    "total_successes": total,
    "paid_gpu_hours": args.gpu_hours,
    "successes_per_paid_gpu_hour": total / args.gpu_hours,
    "allocation": "combined experiment total; shared costs are not assigned per model",
}
print(json.dumps(out, indent=2))
