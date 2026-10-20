#!/usr/bin/env python3
"""Pod-only scratchpad aggregation runner. CPU planning checks use --dry-run."""
import argparse,csv,hashlib,json,os,re,signal,socket,subprocess,sys,threading,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"DATA"; INTERNAL=ROOT/"_internal"/"scratchpad"
sys.path.insert(0,str(ROOT/"scripts"))
import run_phase1 as base
MODELS=["qwen36_35b_a3b","nemotron","qwen38_27b"]
LENGTHS=("control","long_64k","long_128k")
APPEND="Before answering, list every occurrence as you find it, one per line, in the form `found N: <copy the exact line from the document>`. Then output the final JSON object."
final_once=threading.Lock(); finished=False; stop_watch=threading.Event()

def durable_raw(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(obj,ensure_ascii=False)+"\n"); f.flush(); os.fsync(f.fileno())

def build_payload(doc,q,model,params,max_tokens,append_scratchpad=True):
    """Mirror run_phase1.py request fields; only add this arm's suffix and output cap."""
    seed=int(hashlib.sha256(q["question_id"].encode()).hexdigest()[:8],16)
    user=q["prompt"]+("\n\n"+APPEND if append_scratchpad else "")
    payload={"model":model,"messages":[{"role":"system","content":doc},{"role":"user","content":user}],"max_tokens":max_tokens,"seed":seed,"temperature":params["temperature"],"top_p":params["top_p"],"chat_template_kwargs":{"enable_thinking":False}}
    for source_key,target_key in (("top_k","top_k"),("min_p","min_p"),("presence_penalty","presence_penalty"),("repetition_penalty","repeat_penalty")):
        if source_key in params: payload[target_key]=params[source_key]
    return payload

def preflight_pass(choice):
    message=choice.get("message",{}) or {}; content=message.get("content","") or ""
    reasoning=message.get("reasoning_content","") or ""
    return (choice.get("finish_reason")=="stop" and not reasoning
            and not re.search(r"<\s*think\b",content,re.I)
            and base.parse(content) is not None)

def project_remaining(progress_rows, reference_model, remaining_models, estimate, safety_factor=1.35, startup_seconds=180):
    """Scale observed same-task wall time by pinned decode-rate ratios.

    Rows are the completed model's scratchpad answers; answer_s already includes
    prompt processing and decode. Exclude preflight by reading progress.jsonl,
    which contains main answers only. The 35% margin and 3-minute model startup
    allowance are applied once per remaining model.
    """
    ref_rates=estimate["rates"][reference_model]
    remaining=0.0; by_model={}
    for model in remaining_models:
        rates=estimate["rates"][model]; seconds=0.0
        for length in LENGTHS:
            group=[r for r in progress_rows if r.get("model")==reference_model and r.get("length_label")==length]
            if not group: raise ValueError(f"no completed timings for {reference_model}/{length}")
            observed=sum(float(r.get("answer_s",0) or 0) for r in group)
            seconds+=observed*ref_rates[length]["decode_tps"]/rates[length]["decode_tps"]
        seconds=seconds*safety_factor+startup_seconds
        by_model[model]=seconds; remaining+=seconds
    return remaining,by_model

def preflight_model(binary, model, model_path, qs, arm_docs, sampling, deadline):
    """Verify fit, no-thinking extraction, and cache reuse before any model answers run."""
    with socket.socket() as s: s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
    proc,log_lines,reader,_=base.launch(binary,model,model_path,131072,port)
    try:
        end=min(deadline,time.time()+900)
        while proc.poll() is None and base.health(port)!=200 and time.time()<end: time.sleep(.4)
        if base.health(port)!=200: raise SystemExit(f"{model}: preflight /health failed")
        time.sleep(.5)
        layers,kv,rs=base.parse_real_pass("".join(log_lines))
        if layers[0]<=0 or layers[0]!=layers[1]: raise SystemExit(f"{model}: 131072 preflight fit failed; CUDA placement={layers[0]}/{layers[1]}")
        print(f"FIT PREFLIGHT PASS {model}: context=131072 CUDA layers={layers[0]}/{layers[1]} KV={kv} MiB RS={rs} MiB",flush=True)
        pre_q=[qs["prose"][0],qs["prose"][1],qs["code"][0]]
        for preflight_index,q in enumerate(pre_q):
            arm="code" if q["question_id"].startswith("003-code-") else "prose"
            doc=arm_docs[arm][q["doc_id"]].read_text(errors="replace")
            response=base.request(port,build_payload(doc,q,model,sampling[model],max_tokens=1024))
            choice=response["choices"][0]; msg=choice.get("message",{}) or {}
            content=msg.get("content","") or ""; usage=response.get("usage",{}) or {}
            cached=(usage.get("prompt_tokens_details",{}) or {}).get("cached_tokens",usage.get("cached_tokens",0)) or 0
            reasoning=msg.get("reasoning_content","") or ""
            good=preflight_pass(choice)
            durable_raw(INTERNAL/"responses"/f"preflight-{model}.jsonl",{"question_id":q["question_id"],"model":model,"arm":arm,"content":content,"reasoning_content":reasoning,"finish_reason":choice.get("finish_reason"),"usage":usage,"preflight_pass":good})
            if not good: raise SystemExit(f"{model} no-think/extraction preflight failed at {q['question_id']}")
            if preflight_index==1 and int(cached or 0)<=0: raise SystemExit(f"{model} prompt-cache preflight failed: second request had no cached tokens")
            if preflight_index==1: print(f"CACHE PREFLIGHT PASS {model}: cached_prompt_tokens={int(cached or 0)}",flush=True)
        print(f"PREFLIGHT PASS {model}: 3 control questions, finish_reason=stop, no thinking, valid JSON",flush=True)
    finally:
        base.stop(proc); reader.join(timeout=3)

def finalize(sync_cmd,stop_cmd):
    global finished
    with final_once:
        if finished: return
        finished=True
        for command in (sync_cmd,stop_cmd):
            if command:
                try: subprocess.run(command,shell=True,check=False,timeout=180)
                except Exception as exc: print(f"finalize command failed: {exc}",file=sys.stderr)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--llama-server",default="llama-server"); ap.add_argument("--model-file",action="append",default=[],help="MODEL=PATH for each pinned GGUF")
    ap.add_argument("--pod-created-epoch",type=float); ap.add_argument("--sync-command"); ap.add_argument("--stop-command"); ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--models",default=",".join(MODELS),help="Comma-separated subset in run order")
    ap.add_argument("--hard-stop-hours",type=float,default=2.25)
    args=ap.parse_args()
    selected=[m for m in args.models.split(",") if m]
    if not selected or any(m not in MODELS for m in selected) or len(set(selected))!=len(selected): raise SystemExit(f"invalid --models; choose from {MODELS}")
    qfiles={"prose":DATA/"questions.jsonl","code":DATA/"code"/"questions.jsonl"}
    questions={a:[json.loads(x) for x in p.read_text().splitlines() if x.strip()] for a,p in qfiles.items()}
    qs={a:[q for q in rows if q["task_type"]=="aggregation"] for a,rows in questions.items()}
    if args.dry_run:
        assert {a:len(v) for a,v in qs.items()}=={"prose":45,"code":45}
        assert sum(map(len,qs.values()))*len(selected)==90*len(selected)
        assert all(q["prompt"]+"\n\n"+APPEND for v in qs.values() for q in v)
        print(f"DRY RUN PASS: 90 frozen aggregation questions × {len(selected)} models = {90*len(selected)} responses; prompts append scratchpad instruction; no GPU/server calls made.")
        return
    paths={}
    for item in args.model_file:
        model,path=item.split("=",1); paths[model]=Path(path)
    if set(paths)!=set(selected): raise SystemExit(f"provide --model-file MODEL=PATH for {selected}")
    if args.pod_created_epoch is None or not args.sync_command or not args.stop_command:
        raise SystemExit("real run requires --pod-created-epoch, --sync-command and --stop-command (2.25h watchdog will sync then stop)")
    hard_stop_hours=args.hard_stop_hours
    deadline=args.pod_created_epoch+hard_stop_hours*3600
    def watchdog():
        remaining=deadline-time.time()
        if remaining>0 and stop_watch.wait(remaining): return
        print("SCRATCHPAD WATCHDOG: hard cap reached; syncing and stopping pod",flush=True)
        finalize(args.sync_command,args.stop_command)
        stop_watch.set()
    threading.Thread(target=watchdog,daemon=True).start()
    import atexit
    atexit.register(finalize,args.sync_command,args.stop_command)
    def on_signal(sig,frame):
        stop_watch.set(); finalize(args.sync_command,args.stop_command); raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,on_signal); signal.signal(signal.SIGINT,on_signal)
    sampling=json.loads((DATA/"sampling.json").read_text())["models"]
    arm_docs={a:{d["doc_id"]:(DATA/("code/documents" if a=="code" else "documents")/f"{d['doc_id']}.txt") for d in json.loads((DATA/("code/documents" if a=="code" else "documents")/"manifest.json").read_text())["documents"]} for a in qfiles}
    out=DATA/"scratchpad"; out.mkdir(parents=True,exist_ok=True)
    server=None
    try:
        # Preflight every selected model before the first main answer is generated.
        for model in selected:
            if time.time()>=deadline: raise SystemExit("budget stop before no-think preflight")
            preflight_model(args.llama_server,model,paths[model],qs,arm_docs,sampling,deadline)
        for model in selected:
            if time.time()>=deadline: raise SystemExit("budget stop before model")
            with socket.socket() as s: s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
            server,log_lines,reader,cmd=base.launch(args.llama_server,model,paths[model],131072,port)
            try:
                end=min(deadline,time.time()+900)
                while server.poll() is None and base.health(port)!=200 and time.time()<end: time.sleep(.4)
                if base.health(port)!=200: raise SystemExit(f"{model}: /health failed")
                time.sleep(.5)
                layers,kv,rs=base.parse_real_pass("".join(log_lines))
                if layers[0]<=0 or layers[0]!=layers[1]: raise SystemExit(f"{model}: 131072 fit check failed; CUDA placement={layers[0]}/{layers[1]}")
                print(f"FIT PASS {model}: context=131072 CUDA layers={layers[0]}/{layers[1]} KV={kv} MiB RS={rs} MiB",flush=True)
                # Run six arm/document groups; repeated questions reuse the document system prefix.
                for arm in ("prose","code"):
                    for doc_id,docpath in arm_docs[arm].items():
                        doc=docpath.read_text(errors="replace"); group=[q for q in qs[arm] if q["doc_id"]==doc_id]
                        for index,q in enumerate(group):
                            if time.time()>=deadline: raise SystemExit("hard stop mid-model; retaining completed answers")
                            params=sampling[model]; payload=build_payload(doc,q,model,params,max_tokens=1024)
                            started=time.monotonic(); response=base.request(port,payload); answer_s=time.monotonic()-started
                            choice=response["choices"][0]; msg=choice["message"]; body=msg.get("content","") or ""; usage=response.get("usage",{}) or {}; details=usage.get("prompt_tokens_details",{}) or {}; cached=details.get("cached_tokens",usage.get("cached_tokens",0)) or 0
                            raw={"question_id":q["question_id"],"model":model,"arm":arm,"content":body,"finish_reason":choice.get("finish_reason"),"usage":usage,"answer_s":round(answer_s,3)}
                            if "reasoning_content" in msg: raw["reasoning_content"]=msg["reasoning_content"]
                            durable_raw(INTERNAL/"responses"/f"{arm}-{model}.jsonl",raw)
                            row={"arm":arm,"model":model,"question_id":q["question_id"],"length_label":q["length_label"],"prompt_tokens":usage.get("prompt_tokens",0),"cached_prompt_tokens":cached,"generated_tokens":usage.get("completion_tokens",0),"answer_s":round(answer_s,3),"finish_reason":choice.get("finish_reason")}
                            durable_raw(INTERNAL/"progress.jsonl",row)
                            if index==1 and not cached: raise SystemExit(f"cache reuse not observed for {arm}/{doc_id} second question")
                            if stop_watch.is_set(): raise SystemExit("watchdog stopped the run")
            finally:
                base.stop(server); reader.join(timeout=3); server=None
            if model==selected[0] and len(selected)>1:
                # Use only main-run answer timings; preflight never enters progress.jsonl.
                progress=[json.loads(x) for x in (INTERNAL/"progress.jsonl").read_text().splitlines() if x.strip()]
                model_rows=[r for r in progress if r.get("model")==model]
                generated=[int(r.get("generated_tokens",0) or 0) for r in model_rows]
                estimate=json.loads((DATA/"code"/"phase0-estimate.json").read_text())
                remaining,by_model=project_remaining(progress,model,selected[1:],estimate)
                elapsed=time.time()-args.pod_created_epoch; projection=(elapsed+remaining)/3600
                (INTERNAL/"checkpoint.json").write_text(json.dumps({"after_first_model":model,"answers_counted":len(generated),"measured_mean_generated_tokens":round(sum(generated)/max(1,len(generated)),2),"elapsed_seconds":round(elapsed,1),"remaining_seconds_by_model":{k:round(v,1) for k,v in by_model.items()},"projection_basis":"measured per-length answer_s from completed model, scaled by pinned 003 decode-rate ratios, 1.35 safety factor, and 180s startup per remaining model; main progress only","projected_total_hours":round(projection,3),"hard_stop_hours":hard_stop_hours,"decision":"STOP" if projection>hard_stop_hours else "CONTINUE"},indent=2)+"\n")
                print(f"CHECKPOINT: projected {projection:.3f}h against {hard_stop_hours}h cap",flush=True)
                if projection>hard_stop_hours: raise SystemExit("checkpoint projection exceeds hard cap; stopping before next model")
        subprocess.run([sys.executable,str(ROOT/"scripts"/"scratchpad"/"score.py"),"--responses",str(INTERNAL/"responses"),"--out",str(out)],check=True)
    finally:
        if server is not None: base.stop(server)
        stop_watch.set(); finalize(args.sync_command,args.stop_command)

if __name__=="__main__": main()
