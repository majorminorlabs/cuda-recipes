#!/usr/bin/env python3
"""Write or verify the immutable long_horizon_v1 pre-score receipt."""
import argparse
import hashlib
import json
import time
from pathlib import Path

BASE=Path(__file__).parent
REPO=BASE.parents[1]
FILES=["tasks.json","schedule.json","pilot-schedule.json","config.json","scoring.json","pilot.json","prepare_suite.py","make_schedule.py","validate_suite.py","freeze.py","../../src/long_horizon.py","../../tests/test_long_horizon.py","../../requirements-long-horizon.txt","../../models/manifest.json","../../manifests/llama-cpp.json","../../scripts/run-llama-server.sh","../../scripts/download-models.sh","../../scripts/build-llama-cpp-phase2.sh","../../reports/phase2-budget-and-execution-gate.md"]
for case in sorted((BASE/"cases").iterdir()):
    if case.is_dir():
        for f in sorted(case.rglob("*")):
            if f.is_file() and not ({".pytest_cache", "__pycache__", ".git"} & set(f.parts)):
                FILES.append(str(f.relative_to(BASE)))


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_map():
    return {name:sha((BASE/name).resolve()) for name in FILES}


def verify():
    receipt=json.loads((BASE/"freeze.json").read_text())
    current=digest_map()
    if current!=receipt["files_sha256"]: raise SystemExit("long_horizon_v1 freeze hash mismatch")
    print("PASS: long_horizon_v1 frozen files match SHA-256 receipt")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--write",action="store_true"); ap.add_argument("--validation",type=Path,default=BASE/"validation.json"); args=ap.parse_args()
    if not args.write: verify(); return
    validation=json.loads(args.validation.read_text())
    if validation.get("tasks")!=10 or validation.get("positive_references_passed")!=10 or validation.get("negative_controls_rejected")!=10:
        raise SystemExit("all 10 references and negative controls must validate before freeze")
    tasks=json.loads((BASE/"tasks.json").read_text())
    if len(tasks["tasks"])!=10: raise SystemExit("unexpected task count")
    schedule=json.loads((BASE/"schedule.json").read_text())
    if len(schedule["trials"])!=60: raise SystemExit("unexpected scored denominator")
    payload={"suite":"long_horizon_v1","version":"1.0.0","frozen_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
             "scored_trials":60,"pilot_trials":10,"validation_summary_sha256":sha(args.validation.resolve()),
             "files_sha256":digest_map(),"immutable_after_scored_start":True}
    (BASE/"freeze.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print(f"Frozen {len(payload['files_sha256'])} artifacts for 60 scored trials.")


if __name__=="__main__": main()
