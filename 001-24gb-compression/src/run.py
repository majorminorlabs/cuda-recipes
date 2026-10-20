"""Checkpointed single-model HTTP runner for llama.cpp's OpenAI-compatible API."""
import argparse, csv, json, os, sqlite3, subprocess, threading, time, urllib.error, urllib.request
from pathlib import Path
from .validate import ROOT, score, strict_json_loads
from .tools import Simulator
from .verify_freeze import verify as verify_freeze

PRIVATE = Path(os.environ.get("NEMOTRON_PRIVATE_DIR", Path.home() / ".local/share/nemotron-compression"))

class Telemetry:
    def __init__(self, interval=0.5):
        self.interval, self.peak_vram, self.peak_ram = interval, None, None
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)
    def _sample(self):
        while not self.stop_event.is_set():
            try:
                v = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], stderr=subprocess.DEVNULL, text=True, timeout=2)
                values = [int(x.strip()) for x in v.splitlines() if x.strip()]
                if values: self.peak_vram = max(values) if self.peak_vram is None else max(self.peak_vram, max(values))
            except Exception: pass
            try:
                # On the Pod, cgroup usage measures this benchmark container;
                # host-wide /proc/meminfo would include unrelated workloads.
                current = Path("/sys/fs/cgroup/memory.current")
                if current.exists():
                    used = int(current.read_text().strip()) // 1024
                else:
                    total = available = 0
                    for line in Path("/proc/meminfo").read_text().splitlines():
                        if line.startswith("MemTotal:"): total = int(line.split()[1])
                        if line.startswith("MemAvailable:"): available = int(line.split()[1])
                    used = total - available
                self.peak_ram = max(used, self.peak_ram or 0)
            except Exception: pass
            self.stop_event.wait(self.interval)
    def __enter__(self): self.thread.start(); return self
    def __exit__(self, *args): self.stop_event.set(); self.thread.join(timeout=3)

def request(url, payload):
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=1800) as response: return json.loads(response.read())

def model_id(url):
    req = urllib.request.Request(url.rstrip("/") + "/models")
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read())
    if not data.get("data"):
        raise RuntimeError("llama.cpp server returned no loaded model")
    return data["data"][0]["id"]

def recover_started_trial(db, tid, row, rawdir):
    """Finalize an interrupted at-most-once trial, never silently drop or retry it."""
    prior = db.execute("SELECT status,started_at FROM trials WHERE trial_id=?", (tid,)).fetchone()
    if prior is None:
        return False
    if prior[0] in ("complete", "failed"):
        return True
    if prior[0] != "running":
        raise RuntimeError(f"unexpected checkpoint state for {tid}: {prior[0]}")
    ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rawpath = rawdir / (tid.replace(":", "_") + "_interrupted.json")
    rawpath.write_text(json.dumps({"trial_id":tid,"assignment":row,"status":"failed","failure_class":"interrupted_process","started_at":prior[1],"ended_at":ended,"note":"No response was persisted before interruption; this exposed assignment is not retried."}, indent=2)+"\n")
    db.execute("UPDATE trials SET status='failed',success=0,wall_s=NULL,failure_class='interrupted_process',raw_path=?,response=NULL,ended_at=? WHERE trial_id=? AND status='running'", (str(rawpath),ended,tid))
    db.commit()
    return True

def interact(api, served_model, model, task, seed):
    use_tools=task.get("expected_calls") is not None
    messages=[{"role":"user","content":task["prompt"]}]
    simulator=Simulator(task["id"])
    trace=[]; bodies=[]; usage={"prompt_tokens":0,"completion_tokens":0}; timings=[]; content=""; finish=None
    turns=6 if use_tools else 1
    for turn in range(turns):
        body={"model":served_model,"messages":messages,"temperature":1.0,"top_p":0.95,"top_k":20 if model=="qwen" else 40,"seed":seed+turn,"max_tokens":512 if use_tools else 2048,"stream":False,"chat_template_kwargs":{"enable_thinking":True}}
        if use_tools: body["tools"]=task["tool_definitions"]
        result=request(api,body); bodies.append({"request":body,"response":result})
        for key in usage:
            usage[key]+=int((result.get("usage") or {}).get(key,0) or 0)
        timings.append(result.get("timings") or {})
        choice=result["choices"][0]; msg=choice["message"]; finish=choice.get("finish_reason")
        calls=msg.get("tool_calls") or []
        if calls:
            if not use_tools: raise RuntimeError("unexpected tool call for non-tool task")
            assistant={"role":"assistant","content":msg.get("content"),"tool_calls":calls}
            messages.append(assistant)
            for call_i,call in enumerate(calls):
                call_id=call.get("id") or f"malformed-{turn}-{call_i}"
                function=call.get("function") or {}; name=function.get("name") or ""
                action={"tool":name}
                try:
                    args=strict_json_loads(function.get("arguments") or "{}")
                    if not isinstance(args,dict) or "tool" in args: raise ValueError("invalid function arguments")
                    action={"tool":name,**args}; output,ok=simulator.step(action)
                except Exception as exc:
                    output={"error":str(exc)}; ok=False
                trace.append({"action":action,"result":output,"ok":ok,"tool_call_id":call_id})
                messages.append({"role":"tool","tool_call_id":call_id,"content":json.dumps(output,ensure_ascii=False)})
            continue
        content=msg.get("content") or ""
        break
    else:
        finish="max_tool_turns"
    prompt_n=usage["prompt_tokens"]; completion_n=usage["completion_tokens"]
    prompt_ms=sum(float(t.get("prompt_ms",0) or 0) for t in timings)
    decode_ms=sum(float(t.get("predicted_ms",0) or 0) for t in timings)
    prompt_tps=(prompt_n*1000/prompt_ms) if prompt_ms>0 else None
    decode_tps=(completion_n*1000/decode_ms) if decode_ms>0 else None
    return {"content":content,"finish_reason":finish,"responses":bodies,"messages":messages,"tool_trace":trace,"usage":usage,"timings":timings,"prompt_tps":prompt_tps,"decode_tps":decode_tps}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True, help="OpenAI-compatible base URL, ending in /v1")
    ap.add_argument("--model", choices=["nemotron", "qwen"], required=True)
    ap.add_argument("--schedule", default="benchmark/schedule.json")
    ap.add_argument("--db", default=str(PRIVATE / "results/checkpoint.sqlite3"))
    ap.add_argument("--raw-dir", default=str(PRIVATE / "traces/raw"))
    ap.add_argument("--pilot", action="store_true", help="run only the five unscored pilot trials for this model")
    args = ap.parse_args()
    verify_freeze()
    schedule_path = ROOT / ("benchmark/pilot-schedule.json" if args.pilot else args.schedule)
    schedule = json.loads(schedule_path.read_text())
    tasks = {t["id"]: t for t in json.loads((ROOT / "benchmark/tasks.json").read_text())}
    pilot = json.loads((ROOT / "benchmark/pilot.json").read_text())
    dbpath = ROOT / args.db; dbpath.parent.mkdir(parents=True, exist_ok=True)
    rawdir = ROOT / args.raw_dir; rawdir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(dbpath)
    db.execute("CREATE TABLE IF NOT EXISTS trials (trial_id TEXT PRIMARY KEY, model TEXT, task_id TEXT, repetition INTEGER, seed INTEGER, status TEXT, success INTEGER, wall_s REAL, prompt_tokens INTEGER, completion_tokens INTEGER, prompt_tps REAL, decode_tps REAL, peak_vram_mib INTEGER, peak_ram_kib INTEGER, failure_class TEXT, raw_path TEXT, response TEXT, started_at TEXT, ended_at TEXT)")
    db.commit()
    served_model = model_id(args.api)
    for row in schedule["trials"]:
        if row["model"] != args.model: continue
        if args.pilot and row["task_id"] not in pilot["task_ids"]: continue
        tid = f"{row['model']}:{row['task_id']}:{row['repetition']}"
        if recover_started_trial(db, tid, row, rawdir): continue
        task = tasks[row["task_id"]]; started = time.time(); rawpath = rawdir / (tid.replace(":", "_") + ".json")
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))
        db.execute("INSERT INTO trials (trial_id,model,task_id,repetition,seed,status,started_at) VALUES (?,?,?,?,?,?,?)", (tid,args.model,task["id"],row["repetition"],row["seed"],"running",stamp)); db.commit()
        failure = None; failure_detail=None; content = ""; status = "failed"; tool_trace = []; finish_reason = None; interaction=None
        with Telemetry() as telemetry:
            try:
                interaction=interact(args.api,served_model,args.model,task,row["seed"])
                content=interaction["content"]; finish_reason=interaction["finish_reason"]; tool_trace=interaction["tool_trace"]; usage=interaction["usage"]
                try:
                    parsed = strict_json_loads(content)
                    success = int(score(task, parsed, tool_trace if task.get("expected_calls") is not None else None))
                    if not success:
                        failure = "tool_action_or_final_mismatch" if task.get("expected_calls") is not None else "code_tests_failed" if task.get("kind")=="python_function" else "incorrect_command" if task["category"]=="terminal_system" else "incorrect_structured_result" if task["category"]=="structured_data" else "incorrect_task_response"
                except Exception:
                    parsed = None; success = 0; failure = "invalid_json"
                if finish_reason == "length": success = 0; failure = "truncated"
                if finish_reason == "max_tool_turns": success = 0; failure = "tool_turn_limit"
                status = "complete"
            except Exception as exc:
                success = 0; failure_detail=type(exc).__name__+": "+str(exc)[:500]; detail=failure_detail.lower(); tool_trace=[]
                if "timeout" in detail: failure="transport_timeout"
                elif any(s in detail for s in ("out of memory","cuda error","ggml_alloc","failed to allocate")): failure="engine_memory_or_cuda_error"
                elif any(s in detail for s in ("httperror","urlerror","connection refused","connection reset")): failure="transport_or_http_error"
                else: failure="engine_or_api_error"
        elapsed = time.time() - started
        p = usage.get("prompt_tokens"); c = usage.get("completion_tokens")
        raw = {"trial":row,"task":task,"interaction":interaction,"finish_reason":finish_reason,"content":content,"tool_trace":tool_trace,"usage":usage,"success":success,"failure_class":failure,"failure_detail":failure_detail}
        rawpath.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
        p_tps = (interaction.get("prompt_tps") if interaction else None) or (p/elapsed if p else None)
        d_tps = (interaction.get("decode_tps") if interaction else None) or (c/elapsed if c else None)
        db.execute("INSERT OR REPLACE INTO trials VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (tid,args.model,task["id"],row["repetition"],row["seed"],status,success,elapsed,p,c,p_tps,d_tps,telemetry.peak_vram,telemetry.peak_ram,failure,str(rawpath),content,time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(started)),time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())))
        db.commit()
        print(json.dumps({"trial":tid,"status":status,"success":success,"wall_s":round(elapsed,2),"prompt_tokens":p,"completion_tokens":c,"peak_vram_mib":telemetry.peak_vram}, ensure_ascii=False), flush=True)
    db.close()

if __name__ == "__main__": main()
