"""Create a hash manifest after every empirical validity gate has passed."""
import hashlib, json, sys, time
from pathlib import Path
from .validate import ROOT, validate

FILES = ["benchmark/tasks.json","benchmark/scoring.json","benchmark/config.json","benchmark/schedule.json","benchmark/pilot.json","benchmark/pilot-schedule.json","benchmark/make_suite.py","benchmark/make_schedule.py","models/manifest.json","protocol/PROTOCOL.md","src/validate.py","src/tools.py","src/run.py","src/analyze.py","src/freeze.py","src/verify_freeze.py","tests/test_benchmark.py","scripts/build-llama-cpp.sh","scripts/download-models.sh","scripts/run-llama-server.sh","docs/REPRODUCE.md"]

def main():
    validate()
    model = json.loads((ROOT / "models/manifest.json").read_text())
    if not all(model[k].get("payload_hash_verified") for k in ("nemotron","qwen")):
        raise SystemExit("freeze blocked: downloaded model payload hashes are not verified")
    for path in (ROOT/"manifests/llama-cpp.json",ROOT/"manifests/hardware.json",ROOT/"manifests/environment.json"):
        if not path.exists(): raise SystemExit(f"freeze blocked: missing {path.relative_to(ROOT)}")
    hw=json.loads((ROOT/"manifests/hardware.json").read_text())
    engine=json.loads((ROOT/"manifests/llama-cpp.json").read_text())
    if hw.get("gpu_model")!="NVIDIA GeForce RTX 5090" or hw.get("vram_bytes",0)<32_000_000_000 or hw.get("cpu_offload") is not False or hw.get("common_context_tokens")!=16384 or not all(hw.get("model_fit",{}).get(k) is True for k in ("nemotron","qwen")) or not hw.get("verified"):
        raise SystemExit("freeze blocked: GPU, no-offload, common-context, or model-fit gate failed")
    if not engine.get("cuda_enabled") or not engine.get("build_verified") or not all(engine.get("model_load_verified",{}).get(k) is True for k in ("nemotron","qwen")) or not all(engine.get("no_cpu_offload_verified",{}).get(k) is True for k in ("nemotron","qwen")) or not engine.get("revision"):
        raise SystemExit("freeze blocked: llama.cpp CUDA build has not been recorded")
    env=json.loads((ROOT/"manifests/environment.json").read_text())
    if not env.get("verified"): raise SystemExit("freeze blocked: execution environment manifest is incomplete")
    for name in ("benchmark/config.json","benchmark/schedule.json","benchmark/pilot-schedule.json","benchmark/scoring.json"):
        p=ROOT/name; data=json.loads(p.read_text()); data["frozen"]=True; p.write_text(json.dumps(data,indent=2)+"\n")
    records = {}
    for name in FILES + ["manifests/llama-cpp.json","manifests/hardware.json","manifests/environment.json"]:
        data = (ROOT/name).read_bytes()
        records[name] = hashlib.sha256(data).hexdigest()
    result = {"protocol_version":"1.0","frozen_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"files_sha256":records,"scored_trials":240,"gpu_hour_hard_limit":15,"gpu_hour_target":10,"frozen":True}
    (ROOT/"benchmark/freeze.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Frozen benchmark/scoring/config/schedule and runtime provenance hashes.")

if __name__ == "__main__": main()
