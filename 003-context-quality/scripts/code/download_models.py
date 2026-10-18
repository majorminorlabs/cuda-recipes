#!/usr/bin/env python3
"""Download all pinned GGUFs and verify local size and SHA-256 before use."""
import concurrent.futures,hashlib,json,subprocess,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"DATA"/"code"; INTERNAL=ROOT/"_internal"/"code"; MODELS=ROOT/"_internal"/"code"/"models"; PATH_KEY={"qwen":"qwen38_27b"}

def download(key,spec):
    repo=spec["source"].split("huggingface.co/")[-1].rstrip("/"); revision=spec["revision"]; item=spec["files"][0]; target=MODELS/PATH_KEY.get(key,key); target.mkdir(parents=True,exist_ok=True)
    log=INTERNAL/"raw-logs"/f"download-{key}.log"; log.parent.mkdir(parents=True,exist_ok=True)
    cmd=[str(ROOT/"_internal"/"code"/"venv/bin/hf"),"download",repo,item["path"],"--revision",revision,"--local-dir",str(target)]
    proc=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_text(proc.stdout)
    if proc.returncode: raise RuntimeError(f"{key}: download failed; inspect {log}")
    path=target/item["path"]
    if not path.is_file(): raise RuntimeError(f"{key}: expected downloaded file missing")
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(16*1024*1024),b""): digest.update(block)
    actual=digest.hexdigest(); size=path.stat().st_size
    result={"model":PATH_KEY.get(key,key),"file":item["path"],"revision":revision,"bytes":size,"sha256":actual,"verified":size==item["bytes"] and actual==item["sha256"]}
    if not result["verified"]: raise RuntimeError(f"{key}: SHA-256 or byte-size mismatch; expected {item['sha256']}/{item['bytes']}, got {actual}/{size}")
    return result

def main():
    specs=json.loads((DATA/"model-manifest.json").read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(download,key,spec):key for key,spec in specs.items()}
        results=[]
        for future in concurrent.futures.as_completed(futures): results.append(future.result())
    results.sort(key=lambda x:x["model"])
    out={"status":"all_artifacts_sha256_verified","verified_at_epoch":time.time(),"models":results}
    (DATA/"download-manifest.json").write_text(json.dumps(out,indent=2)+"\n")
    for row in results: print(f"PASS {row['model']} {row['bytes']} bytes sha256={row['sha256']}")

if __name__=="__main__":
    try: main()
    except Exception as e: print(f"STOP: {e}",file=sys.stderr); raise SystemExit(1)
