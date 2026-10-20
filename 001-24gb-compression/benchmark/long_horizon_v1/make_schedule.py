#!/usr/bin/env python3
"""Create immutable paired scored and unscored pilot assignments."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
TASKS = json.loads((ROOT / "tasks.json").read_text())["tasks"]
MODELS = ["qwen", "nemotron"]
PILOT_TASKS = ["MI01", "RE01", "PK01", "CL01", "AT01"]


def seed(label):
    return int.from_bytes(hashlib.sha256(label.encode()).digest()[:4], "big")


scored = []
pilot = []
for model in MODELS:
    for task in TASKS:
        for repetition in (1, 2, 3):
            pair_seed = seed(f"MAJOR-MINOR-LH1|{task['id']}|{repetition}")
            scored.append({"model":model,"task_id":task["id"],"repetition":repetition,"seed":pair_seed})
        if task["id"] in PILOT_TASKS:
            pilot.append({"model":model,"task_id":task["id"],"repetition":0,
                          "seed":seed(f"MAJOR-MINOR-LH1-PILOT|{model}|{task['id']}")})

(ROOT / "schedule.json").write_text(json.dumps({"suite":"long_horizon_v1","trials":scored},indent=2)+"\n")
(ROOT / "pilot-schedule.json").write_text(json.dumps({"suite":"long_horizon_v1_pilot","trials":pilot},indent=2)+"\n")
print(f"scored={len(scored)} pilot={len(pilot)} paired_seeds={len(scored)//2}")
