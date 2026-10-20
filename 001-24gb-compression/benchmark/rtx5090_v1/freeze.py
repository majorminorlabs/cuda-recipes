#!/usr/bin/env python3
"""Freeze and verify the corrected RTX 5090 equivalence run before scoring."""
import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parents[1]
REF = ROOT / "benchmark/rtx3090_v1"
COMMON = [
    "../freeze.json", "../tasks.json", "../scoring.json", "../schedule.json", "../config.json",
    "../../models/manifest.json", "../../src/run_v2.py", "../../src/tools.py", "../../src/validate.py",
    "../../src/verify_freeze.py", "../../scripts/run-llama-server.sh", "../../scripts/download-models.sh",
    "../../tests/test_run_v2_reasoning_history.py", "../../tests/test_run_v2_telemetry.py",
]
FILES = ["config.json", "execution-budget.json", "freeze.py"] + COMMON


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current():
    return {name: sha((BASE / name).resolve()) for name in FILES}


def verify_equivalence():
    cfg3090 = json.loads((REF / "config.json").read_text())
    cfg5090 = json.loads((BASE / "config.json").read_text())
    ignore = {"suite", "purpose", "gpu", "checkpointing"}
    left = {k: v for k, v in cfg3090.items() if k not in ignore}
    right = {k: v for k, v in cfg5090.items() if k not in ignore}
    if left != right:
        raise SystemExit("RTX 5090 inference/benchmark configuration differs from frozen RTX 3090 configuration")
    budget = json.loads((BASE / "execution-budget.json").read_text())
    if budget["current_secure_cloud_quote_usd_per_hour"] > budget["maximum_hourly_rate_usd"]:
        raise SystemExit("live RTX 5090 quote exceeds authorized rate")
    if budget["projected_gpu_hours_including_setup_and_teardown"] > budget["maximum_additional_gpu_hours"]:
        raise SystemExit("projected allocation exceeds authorized RTX 5090 GPU-hour cap")
    for name in ("../tasks.json", "../scoring.json", "../schedule.json", "../config.json", "../../models/manifest.json", "../../src/run_v2.py", "../../src/tools.py"):
        rel = name
        if sha((BASE / name).resolve()) != sha((REF / name).resolve()):
            raise SystemExit(f"RTX 3090 and RTX 5090 frozen input hash mismatch: {rel}")
    return budget


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write pre-score freeze receipt")
    args = ap.parse_args()
    budget = verify_equivalence()
    receipt_path = BASE / "freeze.json"
    if args.write:
        payload = {
            "suite": "phase2_corrected_rtx5090_v1",
            "frozen_before_scored_execution": True,
            "reference_rtx3090_freeze_sha256": sha(REF / "freeze.json"),
            "original_benchmark_freeze_sha256": sha(ROOT / "benchmark/freeze.json"),
            "equivalent_benchmark_inputs": ["tasks", "scoring", "schedule", "model artifacts", "runner", "tool implementation", "sampling", "generation limits", "context", "KV cache", "CPU offload policy"],
            "allowed_declared_differences": ["GPU model/VRAM", "GPU architecture and compiled CUDA target", "driver/CUDA deployment versions", "system RAM cgroup source if kernel differs", "independent dataset identity and its authorized 2-hour budget"],
            "projected_gpu_hours": budget["projected_gpu_hours_including_setup_and_teardown"],
            "maximum_gpu_hours": budget["maximum_additional_gpu_hours"],
            "maximum_rate_usd_per_hour": budget["maximum_hourly_rate_usd"],
            "files_sha256": current(),
        }
        receipt_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print("PASS: RTX 5090 settings match frozen RTX 3090 run; pre-score equivalence receipt written")
    else:
        receipt = json.loads(receipt_path.read_text())
        if current() != receipt["files_sha256"]:
            raise SystemExit("corrected RTX 5090 frozen input hash mismatch")
        if receipt["reference_rtx3090_freeze_sha256"] != sha(REF / "freeze.json"):
            raise SystemExit("reference RTX 3090 freeze receipt changed")
        if receipt["original_benchmark_freeze_sha256"] != sha(ROOT / "benchmark/freeze.json"):
            raise SystemExit("original benchmark freeze receipt changed")
        print("PASS: corrected RTX 5090 freeze and RTX 3090 equivalence checks")


if __name__ == "__main__":
    main()
