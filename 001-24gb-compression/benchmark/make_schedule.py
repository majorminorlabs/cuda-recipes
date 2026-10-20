import hashlib, json, random
from pathlib import Path

root = Path(__file__).resolve().parents[1]
tasks = json.loads((root / "benchmark/tasks.json").read_text())
trials = []
for task in tasks:
    for rep in range(1, 4):
        seed = int(hashlib.sha256(f"nemotron-qwen38|{task['id']}|{rep}".encode()).hexdigest()[:8], 16)
        pair = [{"model": "nemotron", "task_id": task["id"], "repetition": rep, "seed": seed},
                {"model": "qwen", "task_id": task["id"], "repetition": rep, "seed": seed}]
        random.Random(seed).shuffle(pair)
        trials.extend(pair)
out = {"seed_base": 43015, "pairing": "same deterministic seed for each task/repetition across both models", "order": "pair order randomized by pair seed", "trials": trials, "frozen": False}
(root / "benchmark/schedule.json").write_text(json.dumps(out, indent=2) + "\n")
pilot_ids = ["CO01", "TE01", "TO01", "ST01", "MU01"]
pilot = []
for task_id in pilot_ids:
    seed = int(hashlib.sha256(f"nemotron-qwen38|pilot|{task_id}".encode()).hexdigest()[:8], 16)
    pair = [{"model":"nemotron","task_id":task_id,"repetition":0,"seed":seed,"pilot":True}, {"model":"qwen","task_id":task_id,"repetition":0,"seed":seed,"pilot":True}]
    random.Random(seed).shuffle(pair)
    pilot.extend(pair)
(root / "benchmark/pilot-schedule.json").write_text(json.dumps({"trials":pilot,"frozen":False}, indent=2) + "\n")
print(f"Wrote {len(trials)} trial schedule rows")
