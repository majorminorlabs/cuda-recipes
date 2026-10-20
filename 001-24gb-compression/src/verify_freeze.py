import hashlib, json
from pathlib import Path
from .validate import ROOT

def verify():
    p=ROOT/"benchmark/freeze.json"
    if not p.exists(): raise RuntimeError("benchmark has not been frozen")
    frozen=json.loads(p.read_text())
    for name,digest in frozen["files_sha256"].items():
        current=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        if current!=digest: raise RuntimeError(f"frozen input changed: {name}")
    if frozen.get("scored_trials")!=240: raise RuntimeError("unexpected frozen denominator")

if __name__=="__main__": verify(); print("PASS: frozen input hashes match")
