#!/usr/bin/env python3
"""Budgeted llama.cpp runner. Run only on the configured RTX 3090 pod."""
import argparse, csv, hashlib, json, os, re, shlex, socket, subprocess, threading, time, urllib.error, urllib.request
from pathlib import Path
from score import content_equal, equal, parse

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"DATA"/"code"; INTERNAL=ROOT/"_internal"/"code"
CFG=json.loads((ROOT/"DATA/study-config.json").read_text())["arms"]["code"]; MODELS=["qwen36_35b_a3b","nemotron","qwen38_27b"]
FIT_COLS=["model","ctx_size","loaded_full_gpu","layers_on_cuda","layers_total","kv_buffer_mib","rs_buffer_mib","peak_vram_mib","error"]
PRE_COLS=["model","length_label","doc_id","prompt_tokens","prefill_s","prefill_tps","peak_vram_mib"]
ANS_COLS=["model","length_label","doc_id","question_id","task_type","position","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","correct","format_strict_correct","failure_class"]
ACTIVE_PROCESS=[None]

def append_csv(path,cols,row):
    path.parent.mkdir(parents=True,exist_ok=True); exists=path.exists() and path.stat().st_size>0
    with path.open("a",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols); 
        if not exists: w.writeheader()
        w.writerow(row)

def health(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",timeout=2) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
    except (urllib.error.URLError,TimeoutError,OSError): return None

def parse_real_pass(log):
    """Use 002's real-allocation rule: start at first non-zero CUDA model buffer."""
    model_lines=list(re.finditer(r"CUDA\d+ model buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)",log,re.I))
    start=next((m.start() for m in model_lines if float(m.group(1).replace(",",""))>0),None)
    placements=list(re.finditer(r"offloaded\s+\d+\s*/\s*\d+\s+layers?\s+to GPU|layers?\s+offloaded\s+to GPU\s*=\s*\d+\s*/\s*\d+",log,re.I))
    prior=[m for m in placements if start is not None and m.start()<start]
    block_start=prior[-1].start() if prior else start
    real=log[block_start:] if block_start is not None else ""
    placement=list(re.finditer(r"offloaded\s+(\d+)\s*/\s*(\d+)\s+layers?\s+to GPU",real,re.I))
    layers=tuple(map(int,placement[-1].groups())) if placement else (0,0)
    def total(label):
        vals=re.findall(rf"CUDA\d+ {label} buffer size\s*=\s*([\d,.]+)\s*(MiB|bytes?)",real,re.I)
        if not vals: return ""
        return round(sum(float(v.replace(",","")) if u.lower().startswith("mi") else float(v.replace(",",""))/1048576 for v,u in vals),2)
    return layers,total("KV"),total("RS")

class Clock:
    def __init__(self): self.path=INTERNAL/"phase1-clock.json"; self.path.parent.mkdir(parents=True,exist_ok=True)
    def start(self,pod_created_epoch=None):
        if not self.path.exists():
            if pod_created_epoch is None: raise SystemExit("First run must provide --pod-created-epoch so the budget includes pod startup/download/build time")
            self.path.write_text(json.dumps({"started_epoch":float(pod_created_epoch),"hard_stop_seconds":CFG["budget_hard_stop_gpu_hours"]*3600,"clock_origin":"pod_creation"},indent=2)+"\n")
        self.started=json.loads(self.path.read_text())["started_epoch"]
    def remaining(self): return CFG["budget_hard_stop_gpu_hours"]*3600-(time.time()-self.started)

def launch(binary,model,model_path,ctx,port):
    fixed=[part for flag in CFG["fixed_server_flags"] for part in shlex.split(flag)]
    cmd=[binary,"--model",str(model_path),"--ctx-size",str(ctx),*fixed,"--port",str(port),"--verbose"]
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",bufsize=1)
    ACTIVE_PROCESS[0]=proc
    lines=[]
    th=threading.Thread(target=lambda: lines.extend(proc.stdout),daemon=True); th.start()
    return proc,lines,th,cmd

def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    if ACTIVE_PROCESS[0] is proc: ACTIVE_PROCESS[0]=None

def request(port,payload):
    data=json.dumps(payload).encode(); req=urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=data,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=1800) as r: return json.loads(r.read())

def post_json(port,path,payload):
    req=urllib.request.Request(f"http://127.0.0.1:{port}{path}",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=1800) as r: return json.loads(r.read())

def sample_peak(proc,values,stop_event,cmd):
    while not stop_event.wait(.25):
        try:
            out=subprocess.check_output(cmd+ ["--query-gpu=memory.used","--format=csv,noheader,nounits"],text=True,stderr=subprocess.DEVNULL)
            values.append(max(int(x.strip()) for x in out.splitlines() if x.strip()))
        except Exception: pass

def make_checkpoint(first_model,clock_started,checkpoint_path=None):
    """Project remaining model work before any second model may start."""
    checkpoint=Path(checkpoint_path) if checkpoint_path else INTERNAL/"budget-checkpoint.json"
    estimate=json.loads((DATA/"phase0-estimate.json").read_text())
    answers=list(csv.DictReader((DATA/"answer-results.csv").open()))
    first=[r for r in answers if r["model"]==first_model]
    # Freeze completion means every question has exactly one first-model answer.
    questions=[json.loads(x) for x in (DATA/"questions.jsonl").read_text().splitlines() if x]
    if len({r["question_id"] for r in first}) != len(questions):
        raise SystemExit("BUDGET CHECKPOINT unavailable: first model did not finish every frozen question")
    measured_avg=sum(int(r["generated_tokens"] or 0) for r in first)/len(first)
    priors=estimate["generated_tokens_per_answer"]
    scale=measured_avg/max(1,priors[first_model])
    remaining=[]
    models=MODELS; later=models[models.index(first_model)+1:]
    manifest=json.loads((DATA/"documents/manifest.json").read_text())
    rate=estimate["rates"]
    for model in later:
        length_rows={}
        for doc in manifest["documents"]:
            length=doc["length_label"]; n=sum(1 for q in questions if q["length_label"]==length)
            prompt=max(doc["estimated_full_prompt_tokens_with_512_template_allowance"].values())
            pps=rate[model][length]["prefill_tps"]; dps=rate[model][length]["decode_tps"]
            if model=="qwen36_35b_a3b" and length=="control":
                preflight=DATA/"host-build-manifest.json"
                if preflight.exists():
                    measured=json.loads(preflight.read_text()).get("qwen36_8k_decode_preflight",{}).get("decode_tokens_per_second")
                    if measured: dps=float(measured)
            avg=min(CFG["generation"]["max_generated_tokens"],priors[model]*scale)
            pre=prompt/pps; dec=n*avg/dps; overhead=n*estimate["request_overhead_seconds_per_answer"]
            length_rows[length]={"questions":n,"estimated_prompt_tokens":prompt,"prefill_tps":pps,"decode_tps":dps,"avg_generated_tokens":round(avg,1),"prefill_seconds":round(pre,1),"decode_seconds":round(dec,1),"request_overhead_seconds":overhead,"total_seconds":round(pre+dec+overhead,1)}
        rest=sum(x["total_seconds"] for x in length_rows.values())+estimate["model_startup_seconds"]+estimate["context_probe_contingency_seconds_per_remaining_model"]
        remaining.append({"model":model,"lengths":length_rows,"estimated_remaining_seconds":round(rest,1)})
    elapsed=time.time()-clock_started
    projected=elapsed+sum(m["estimated_remaining_seconds"] for m in remaining)
    out={"checkpoint":"after first model completed all lengths","first_model":first_model,"completed_questions":len(first),"measured_generated_tokens_per_answer":round(measured_avg,2),"elapsed_gpu_wall_seconds":round(elapsed,1),"remaining_models":remaining,"projected_total_gpu_hours":round(projected/3600,3),"hard_stop_gpu_hours":CFG["budget_hard_stop_gpu_hours"],"decision":"STOP_BEFORE_NEXT_MODEL" if projected>CFG["budget_hard_stop_gpu_hours"]*3600 else "CONTINUE","projection_note":"Scales prior per-model generated-token averages by the completed first model's measured average, capped at the configured 256-token output limit. Uses 002 measured prefill/decode rates by context depth; Qwen3.6 control decode uses the pod preflight rate when available, while deeper rates remain proxies until measured."}
    checkpoint.write_text(json.dumps(out,indent=2)+"\n")
    decision_path=checkpoint.with_name("budget-checkpoint-decision.txt")
    decision_path.write_text(out["decision"]+"\n")
    print(f"BUDGET CHECKPOINT: {out['decision']} projected={out['projected_total_gpu_hours']}h hard_stop={out['hard_stop_gpu_hours']}h")
    if out["decision"]=="STOP_BEFORE_NEXT_MODEL": raise SystemExit("Budget checkpoint exceeded hard stop; stop before next model")

def require_no_think_preflight():
    control=[q for q in (json.loads(x) for x in (DATA/"questions.jsonl").read_text().splitlines() if x.strip()) if q["length_label"]=="control"]
    expected={q["question_id"] for q in control[:3]}
    for model in MODELS:
        path=INTERNAL/"responses"/f"preflight-{model}.jsonl"
        if not path.exists(): raise SystemExit(f"No-thinking preflight missing for {model}; refusing main run")
        records=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        valid={r.get("question_id") for r in records if r.get("model")==model and r.get("arm")=="preflight" and r.get("preflight_pass") is True}
        if not expected.issubset(valid): raise SystemExit(f"No-thinking preflight incomplete or failed for {model}; refusing main run")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--llama-server",default="llama-server"); ap.add_argument("--model",choices=MODELS,required=True); ap.add_argument("--model-file",required=True); ap.add_argument("--nvidia-smi",default="nvidia-smi"); ap.add_argument("--ctx-size",type=int,default=131072); ap.add_argument("--no-reset-clock",action="store_true"); ap.add_argument("--arm",default="primary"); ap.add_argument("--pod-created-epoch",type=float,default=None)
    args=ap.parse_args(); clock=Clock(); model=args.model
    require_no_think_preflight()
    models=MODELS; checkpoint=INTERNAL/"budget-checkpoint.json"
    if model != models[0]:
        if not checkpoint.exists(): raise SystemExit("Mandatory first-model budget checkpoint missing; refusing to start next model")
        decision=json.loads(checkpoint.read_text())["decision"]
        if decision!="CONTINUE": raise SystemExit(f"Budget checkpoint decision is {decision}; refusing next model")
    if model=="qwen36_35b_a3b":
        pre=DATA/"host-build-manifest.json"
        if not pre.exists() or json.loads(pre.read_text()).get("qwen36_8k_decode_preflight",{}).get("status")!="passed":
            raise SystemExit("Qwen3.6 main run requires the pod 8K decode preflight first")
    if not args.no_reset_clock and clock.path.exists(): clock.path.unlink()
    clock.start(args.pod_created_epoch); started=clock.started; model_path=Path(args.model_file)
    hard_deadline=clock.started+CFG["budget_hard_stop_gpu_hours"]*3600
    watchdog_stop=threading.Event()
    def watchdog():
        while not watchdog_stop.wait(.25):
            if time.time()>=hard_deadline:
                proc=ACTIVE_PROCESS[0]
                if proc is not None and proc.poll() is None: proc.kill()
                return
    threading.Thread(target=watchdog,daemon=True).start()
    chosen_ctx=None; port=None
    for ctx in range(args.ctx_size,8191,-8192):
        if clock.remaining()<=0: raise SystemExit("BUDGET STOP before load attempt")
        with socket.socket() as s: s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
        proc,lines,th,cmd=launch(args.llama_server,model,model_path,ctx,port); peak=[]; stop_sample=threading.Event(); st=threading.Thread(target=sample_peak,args=(proc,peak,stop_sample,[args.nvidia_smi]),daemon=True); st.start()
        deadline=time.monotonic()+min(900,clock.remaining()); ready=False
        while time.monotonic()<deadline and proc.poll() is None:
            if health(port)==200: ready=True; break
            time.sleep(.4)
        # wait a moment for real allocations after health has returned
        time.sleep(.5 if ready else 0)
        stop(proc); th.join(timeout=3); stop_sample.set(); st.join(timeout=2)
        log="".join(lines); (INTERNAL/"load-logs").mkdir(parents=True,exist_ok=True); (INTERNAL/"load-logs"/f"{model}-ctx-{ctx}.log").write_text(log)
        layers,kv,rs=parse_real_pass(log); loaded=bool(ready and layers[0]>0 and layers[0]==layers[1])
        append_csv(DATA/"fit-results.csv",FIT_COLS,{"model":model,"ctx_size":ctx,"loaded_full_gpu":int(loaded),"layers_on_cuda":layers[0],"layers_total":layers[1],"kv_buffer_mib":kv,"rs_buffer_mib":rs,"peak_vram_mib":max(peak) if peak else "","error":"" if loaded else ("server exited before /health 200 or incomplete CUDA placement")})
        if loaded: chosen_ctx=ctx; break
        if clock.remaining()<=0: raise SystemExit("BUDGET STOP during context fit probes")
    if chosen_ctx is None: raise SystemExit("No all-GPU context size loaded; no answers were run")
    if chosen_ctx < CFG["ctx_size"]: print(f"FALLBACK: context {chosen_ctx}; long_128k requires truncation to leave prompt room")
    # Reload once at the chosen context and keep that process for all documents.
    with socket.socket() as s: s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
    proc,lines,th,cmd=launch(args.llama_server,model,model_path,chosen_ctx,port)
    deadline=time.monotonic()+min(900,clock.remaining())
    while time.monotonic()<deadline and proc.poll() is None and health(port)!=200: time.sleep(.4)
    if proc.poll() is not None or health(port)!=200: stop(proc); raise SystemExit("Chosen-context server failed health gate")
    sampling=json.loads((DATA/"sampling.json").read_text())["models"][model]
    questions=[json.loads(line) for line in (DATA/"questions.jsonl").read_text().splitlines() if line]
    docs=json.loads((DATA/"documents/manifest.json").read_text())["documents"]
    try:
        for item in docs:
            if clock.remaining()<=0: raise SystemExit("BUDGET STOP before document")
            doc_id=item["doc_id"]; doc=(DATA/item["path"]).read_text(); run_doc_id=doc_id
            if doc_id=="long_128k":
                doc_tokens=post_json(port,"/tokenize",{"content":doc,"add_special":False})["tokens"]
                doc_limit=max(1,chosen_ctx-2048)
                if len(doc_tokens)>doc_limit:
                    doc=post_json(port,"/detokenize",{"tokens":doc_tokens[:doc_limit]})["content"]
                    run_doc_id=f"{doc_id}-truncated-ctx-{chosen_ctx}"
                    print(f"TRUNCATED {doc_id}: {len(doc_tokens)} -> {doc_limit} model tokens; result doc_id={run_doc_id}")
            qs=[q for q in questions if q["doc_id"]==doc_id]
            for index,q in enumerate(qs):
                if clock.remaining()<=0: raise SystemExit("BUDGET STOP before answer")
                seed=int(hashlib.sha256(q["question_id"].encode()).hexdigest()[:8],16)
                sampling_params={k:v for k,v in sampling.items() if k not in ("source",)}
                sampling_params["max_generated_tokens"]=CFG["generation"]["max_generated_tokens"]
                payload={"model":model,"messages":[{"role":"system","content":doc},{"role":"user","content":q["prompt"]}],"max_tokens":sampling_params["max_generated_tokens"],"seed":seed,"temperature":sampling_params["temperature"],"top_p":sampling_params["top_p"],"chat_template_kwargs":{"enable_thinking":False}}
                for source_key,target_key in (("top_k","top_k"),("min_p","min_p"),("presence_penalty","presence_penalty"),("repetition_penalty","repeat_penalty")):
                    if source_key in sampling_params: payload[target_key]=sampling_params[source_key]
                prefill_peak=[]; stop_prefill_sample=threading.Event()
                prefill_sampler=None
                if index==0:
                    prefill_sampler=threading.Thread(target=sample_peak,args=(proc,prefill_peak,stop_prefill_sample,[args.nvidia_smi]),daemon=True); prefill_sampler.start()
                start=time.monotonic(); failure=""; body=""; usage={}; result={};
                message={}; finish=None
                try:
                    result=request(port,payload); elapsed=time.monotonic()-start; message=result["choices"][0]["message"]; body=message.get("content","") or ""; usage=result.get("usage",{}); finish=result["choices"][0].get("finish_reason")
                    strict=equal(parse(body),q["reference"],q["task_type"]); correct=content_equal(parse(body),q["reference"],q["task_type"]); failure="" if correct else ("truncated" if finish=="length" else ("invalid_json" if parse(body) is None else "wrong_answer"))
                except Exception as e:
                    elapsed=time.monotonic()-start; correct=False; strict=False; failure="error"; body=""; (INTERNAL/"request-errors.jsonl").open("a").write(json.dumps({"question_id":q["question_id"],"error":repr(e)})+"\n")
                finally:
                    stop_prefill_sample.set()
                    if prefill_sampler: prefill_sampler.join(timeout=2)
                    raw={"question_id":q["question_id"],"model":model,"arm":args.arm,"content":body,"finish_reason":finish,"usage":usage,"answer_s":round(elapsed,3)}
                    if "reasoning_content" in message: raw["reasoning_content"]=message["reasoning_content"]
                    raw_path=INTERNAL/"responses"/f"{args.arm}-{model}.jsonl"; raw_path.parent.mkdir(parents=True,exist_ok=True)
                    with raw_path.open("a",encoding="utf-8") as raw_file: raw_file.write(json.dumps(raw,ensure_ascii=False)+"\n")
                details=usage.get("prompt_tokens_details",{}) or {}; cached=details.get("cached_tokens",usage.get("cached_tokens",0))
                prompt_n=usage.get("prompt_tokens",0); generated=usage.get("completion_tokens",0)
                if index==0:
                    timing=result.get("timings",{}) or {}; prefill_s=float(timing.get("prompt_ms",0))/1000
                    if not prefill_s and timing.get("prompt_n") and timing.get("prompt_per_second"): prefill_s=float(timing["prompt_n"])/float(timing["prompt_per_second"])
                    append_csv(DATA/"prefill-results.csv",PRE_COLS,{"model":model,"length_label":q["length_label"],"doc_id":run_doc_id,"prompt_tokens":prompt_n,"prefill_s":round(prefill_s,3),"prefill_tps":round(prompt_n/prefill_s,2) if prefill_s else 0,"peak_vram_mib":max(prefill_peak) if prefill_peak else ""})
                append_csv(DATA/"answer-results.csv",ANS_COLS,{"model":model,"length_label":q["length_label"],"doc_id":run_doc_id,"question_id":q["question_id"],"task_type":q["task_type"],"position":q["position"],"prompt_tokens":prompt_n,"cached_prompt_tokens":cached,"generated_tokens":generated,"answer_s":round(elapsed,3),"correct":int(correct),"format_strict_correct":int(strict),"failure_class":failure})
    finally:
        stop(proc); th.join(timeout=3); watchdog_stop.set()
    if model==models[0]: make_checkpoint(model,started)

if __name__=="__main__": main()
