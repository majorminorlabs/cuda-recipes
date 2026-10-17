#!/usr/bin/env python3
"""Mock parser, validator, and checkpoint-write checks without a GPU."""
import csv,json,shutil,subprocess,sys,tempfile,time
from pathlib import Path
import run_phase1
from run_phase1 import parse_real_pass,health
from score import parse

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"DATA"
SAMPLE="""load_tensors: offloaded 3/3 layers to GPU
CUDA0 model buffer size = 0.00 MiB
CUDA0 KV buffer size = 0.00 MiB
CUDA0 RS buffer size = 32.00 MiB
load_tensors: offloaded 3/3 layers to GPU
CUDA0 model buffer size = 120.00 MiB
CUDA0 KV buffer size = 512.00 MiB
CUDA0 RS buffer size = 16.00 MiB
CUDA1 RS buffer size = 0.75 MiB
"""

def main():
    assert parse_real_pass(SAMPLE)==((3,3),512.0,16.75); assert health(9) is None
    assert parse('before {"draft":true} after ```json\n{"answer":"ok"}\n```')=={"answer":"ok"}
    subprocess.run([sys.executable,str(ROOT/"scripts/score.py")],check=True)
    questions=[json.loads(s) for s in (DATA/"questions.jsonl").read_text().splitlines() if s]
    with tempfile.TemporaryDirectory(prefix="003-checkpoint-") as td:
        root=Path(td); scratch=root/"scratch"; sd=scratch/"DATA"; si=scratch/"_internal"; sd.mkdir(parents=True); si.mkdir()
        for name in ("study-config.json","phase0-estimate.json","questions.jsonl"): shutil.copy2(DATA/name,sd/name)
        (sd/"documents").mkdir(); shutil.copy2(DATA/"documents/manifest.json",sd/"documents/manifest.json")
        rows=[]
        for q in questions: rows.append({"model":"qwen36_35b_a3b","question_id":q["question_id"],"generated_tokens":"32"})
        with (sd/"answer-results.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["model","question_id","generated_tokens"]); w.writeheader(); w.writerows(rows)
        original=run_phase1.DATA; run_phase1.DATA=sd
        checkpoint=si/"budget-checkpoint.json"
        try:
            try: run_phase1.make_checkpoint("qwen36_35b_a3b",time.time(),checkpoint)
            except SystemExit: pass
            assert checkpoint.exists(),"checkpoint was not auto-written"
            assert (si/"budget-checkpoint-decision.txt").exists(),"checkpoint decision file was not auto-written"
            assert json.loads(checkpoint.read_text())["decision"] in ("CONTINUE","STOP_BEFORE_NEXT_MODEL")
        finally: run_phase1.DATA=original
    scratch=ROOT/"_internal/dry-run/copy"
    if scratch.exists(): shutil.rmtree(scratch)
    (scratch/"DATA").mkdir(parents=True); (scratch/"_internal/responses").mkdir(parents=True)
    for name in ("study-config.json","questions.jsonl","fit-results.csv","prefill-results.csv","answer-results.csv"): shutil.copy2(DATA/name,scratch/"DATA"/name)
    shutil.copytree(DATA/"exploratory-thinking-on",scratch/"DATA/exploratory-thinking-on")
    shutil.copy2(ROOT/"validate.py",scratch/"validate.py")
    for name in ("study-config.json","questions.jsonl","fit-results.csv","prefill-results.csv","answer-results.csv"): (scratch/"DATA"/name).unlink(missing_ok=True)
    shutil.copy2(DATA/"study-config.json",scratch/"DATA/study-config.json"); shutil.copy2(DATA/"questions.jsonl",scratch/"DATA/questions.jsonl")
    with (scratch/"DATA/fit-results.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["model","ctx_size","loaded_full_gpu","layers_on_cuda","layers_total","kv_buffer_mib","rs_buffer_mib","peak_vram_mib","error"])
        for m in ("nemotron","qwen38_27b","qwen36_35b_a3b"): w.writerow([m,131072,1,1,1,512,16,22000,""])
    with (scratch/"DATA/prefill-results.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["model","length_label","doc_id","prompt_tokens","prefill_s","prefill_tps","peak_vram_mib"])
        for m in ("nemotron","qwen38_27b","qwen36_35b_a3b"):
            for doc,length,n in (("control","control",8192),("long_64k","long_64k",65536),("long_128k","long_128k",126000)): w.writerow([m,length,doc,n,1,n,22000])
    for model in ("nemotron","qwen38_27b","qwen36_35b_a3b"):
        with (scratch/"_internal/responses"/f"primary-{model}.jsonl").open("w") as f:
            for q in questions: f.write(json.dumps({"question_id":q["question_id"],"model":model,"arm":"primary"})+"\n")
    with (scratch/"DATA/answer-results.csv").open("w",newline="") as f:
        cols=["model","length_label","doc_id","question_id","task_type","position","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","correct","failure_class"]
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for m in ("nemotron","qwen38_27b","qwen36_35b_a3b"):
            seen=set()
            for q in questions:
                first=q["doc_id"] not in seen; seen.add(q["doc_id"])
                w.writerow({"model":m,"length_label":q["length_label"],"doc_id":q["doc_id"],"question_id":q["question_id"],"task_type":q["task_type"],"position":q["position"],"prompt_tokens":8192,"cached_prompt_tokens":0 if first else 1024,"generated_tokens":8,"answer_s":.1,"correct":1,"failure_class":""})
    subprocess.run([sys.executable,str(scratch/"validate.py")],cwd=scratch,check=True)
    real=subprocess.run([sys.executable,str(ROOT/"validate.py")],cwd=ROOT,text=True,capture_output=True,check=True)
    assert "PENDING: primary arm has no answers yet" in real.stdout,real.stdout
    print("PASS: checkpoint files auto-write in scratch; primary mock validates with complete raw-response coverage; production arm remains pending.")

if __name__=="__main__": main()
