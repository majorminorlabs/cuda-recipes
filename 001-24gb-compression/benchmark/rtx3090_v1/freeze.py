#!/usr/bin/env python3
"""Freeze/verify the corrected-harness RTX 3090 replication before scoring."""
import argparse
import hashlib
import json
import time
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE.parents[1]
FILES = [
    "config.json", "freeze.py", "../freeze.json", "../tasks.json", "../schedule.json",
    "../config.json", "../../src/run.py", "../../src/run_v2.py", "../../src/validate.py",
    "../../src/tools.py", "../../src/verify_freeze.py", "../../tests/test_run_v2_reasoning_history.py",
    "../../tests/test_run_v2_telemetry.py",
    "../../models/manifest.json", "../../scripts/run-llama-server.sh",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current():
    return {name: digest((BASE / name).resolve()) for name in FILES}


def verify():
    frozen = json.loads((BASE / "freeze.json").read_text())
    if current() != frozen["files_sha256"]:
        raise SystemExit("RTX 3090 Phase 2 freeze hash mismatch")
    if frozen["original_freeze_receipt_sha256"] != digest(ROOT / "benchmark/freeze.json"):
        raise SystemExit("original Phase 1 freeze receipt changed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    receipt = BASE / "freeze.json"
    if args.write:
        original = json.loads((ROOT / "benchmark/freeze.json").read_text())
        if original.get("scored_trials") != 240:
            raise SystemExit("original frozen benchmark receipt invalid")
        config = json.loads((BASE / "config.json").read_text())
        schedule = json.loads((BASE / "../schedule.json").resolve().read_text())
        tasks = json.loads((BASE / "../tasks.json").resolve().read_text())
        if len(schedule["trials"]) != 240 or len(tasks) != 40:
            raise SystemExit("original schedule or task denominator changed")
        payload = {
            "suite": "phase2_original_rtx3090_v1",
            "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scored_trials": 240,
            "original_freeze_receipt_sha256": digest(ROOT / "benchmark/freeze.json"),
            "runner_change": config["runner_change"],
            "files_sha256": current(),
            "immutable_after_scored_start": True,
        }
        receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"Frozen corrected RTX 3090 runner and original 240-trial inputs ({len(payload['files_sha256'])} hashes).")
    else:
        verify()
        print("PASS: corrected RTX 3090 harness freeze matches SHA-256 receipt")


if __name__ == "__main__":
    main()
