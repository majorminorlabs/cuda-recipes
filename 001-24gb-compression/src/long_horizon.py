"""Checkpointed repository-task runner for long_horizon_v1.

Model-visible tools are an allowlist: file listing/reading/search, git-apply
patches, fixed test commands, and git diff. No arbitrary shell tool is exposed.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from src.run import Telemetry
from benchmark.long_horizon_v1.freeze import verify as verify_long_horizon_freeze


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmark/long_horizon_v1"
MODELS = {"nemotron": 40, "qwen": 20}
MAX_PATCH_BYTES = 100_000
MAX_READ_BYTES = 50_000


def api_request(api, payload, timeout=1800):
    req = urllib.request.Request(api.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def clean_relative(root, value):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("path must be a non-empty relative string")
    p = Path(value)
    if p.is_absolute() or any(part in ("..", "") for part in p.parts):
        raise ValueError("path must stay inside the task workspace")
    target = root / p
    resolved = target.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("path resolves outside the task workspace")
    current = root
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink traversal is not permitted")
    return target


class Workspace:
    def __init__(self, task, path, cache, case_root, python, deadline):
        self.task = task
        self.path = path
        self.path.mkdir(parents=True,exist_ok=True)
        self.python = python
        self.deadline = deadline
        self.case = case_root / task["id"]
        repo = cache / {"more-itertools":"more-itertools", "requests":"requests", "packaging":"packaging", "click":"click", "attrs":"attrs"}[task["repo"]]
        revision = task["repository"]["revision"]
        archive = subprocess.Popen(["git", "archive", revision], cwd=repo, stdout=subprocess.PIPE)
        result = subprocess.run(["tar", "-x", "-C", str(path)], stdin=archive.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        archive.stdout.close()
        if archive.wait() or result.returncode:
            raise RuntimeError("pinned source checkout failed")
        self._patch((self.case / "starter.patch").read_text(), optional=True)
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "benchmark@localhost"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.name", "benchmark"], cwd=path, check=True)
        subprocess.run(["git", "add", "-A"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-qm", "frozen task starter"], cwd=path, check=True)
        self.test_relpath = task["test_file"]
        self.source_relpath = task["source_file"]
        self.py_path = path if task["repo"] == "more-itertools" else path / "src"

    def _patch(self, patch, optional=False):
        if not patch.strip():
            return {"applied":False,"empty":True} if optional else {"applied":False,"error":"empty patch"}
        check = subprocess.run(["git","apply","--check","-"],cwd=self.path,input=patch,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        if check.returncode:
            raise RuntimeError("frozen starter patch did not apply: "+check.stderr[:1000])
        subprocess.run(["git","apply","-"],cwd=self.path,input=patch,text=True,check=True,timeout=10)
        return {"applied":True}

    def _env(self):
        safe = {"PATH":os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONPATH":str(self.py_path),
                "PYTHONDONTWRITEBYTECODE":"1", "HOME":str(self.path / ".task-home"),
                "LANG":"C.UTF-8", "LC_ALL":"C.UTF-8", "TMPDIR":str(self.path/".tmp"),
                "TMP":str(self.path/".tmp"), "TEMP":str(self.path/".tmp")}
        Path(safe["HOME"]).mkdir(exist_ok=True)
        Path(safe["TMPDIR"]).mkdir(exist_ok=True)
        return safe

    def _clear_bytecode(self):
        for path in self.path.rglob("__pycache__"):
            shutil.rmtree(path, ignore_errors=True)

    def list_files(self, path="."):
        folder = clean_relative(self.path, path) if path != "." else self.path
        if not folder.is_dir():
            raise ValueError("directory not found")
        entries = []
        for child in sorted(folder.iterdir()):
            if child.name == ".git":
                continue
            entries.append({"path":str(child.relative_to(self.path)),"type":"directory" if child.is_dir() else "file"})
            if len(entries) >= 200:
                break
        return {"entries":entries}

    def read_file(self, path, start_line=1, end_line=250):
        target = clean_relative(self.path, path)
        if not target.is_file():
            raise ValueError("file not found")
        if target.stat().st_size > MAX_READ_BYTES:
            raise ValueError("file exceeds 50 KB; read a smaller source file")
        lines = target.read_text(errors="replace").splitlines()
        start = max(1, int(start_line)); end = min(len(lines), int(end_line))
        if end < start or end - start > 500:
            raise ValueError("line range must be between 1 and 500 lines")
        return {"path":path,"start_line":start,"line_count":len(lines),"text":"\n".join(f"{n}: {lines[n-1]}" for n in range(start,end+1))}

    def search(self, pattern, path="."):
        if not isinstance(pattern, str) or not pattern or len(pattern) > 160:
            raise ValueError("search pattern must be 1..160 characters")
        folder = clean_relative(self.path, path) if path != "." else self.path
        try:
            expression = re.compile(pattern)
        except re.error as exc:
            return {"matches":"","exit_code":2,"error":str(exc)[:300]}
        matches = []
        for target in sorted(folder.rglob("*")):
            if not target.is_file() or target.is_symlink() or ".git" in target.relative_to(self.path).parts:
                continue
            try:
                if target.stat().st_size > 1_000_000:
                    continue
                lines = target.read_text(errors="replace").splitlines()
            except OSError:
                continue
            per_file = 0
            for line_number, line in enumerate(lines, 1):
                if expression.search(line):
                    matches.append(f"{target}:{line_number}:{line}")
                    per_file += 1
                    if per_file >= 20 or len(matches) >= 200:
                        break
            if len(matches) >= 200:
                break
        text = "\n".join(matches)[:12000]
        return {"matches":text,"exit_code":0 if matches else 1}

    def apply_patch(self, patch):
        if not isinstance(patch, str) or len(patch.encode()) > MAX_PATCH_BYTES:
            raise ValueError("patch must be text under 100 KB")
        for file_path in re.findall(r"^(?:\+\+\+|---) [ab]/([^\t\n]+)", patch, re.M):
            clean_relative(self.path, file_path)
        check = subprocess.run(["git", "apply", "--check", "-"], cwd=self.path, input=patch, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if check.returncode:
            return {"applied":False,"error":check.stderr[:3000]}
        subprocess.run(["git", "apply", "-"], cwd=self.path, input=patch, text=True, check=True, timeout=10)
        self._clear_bytecode()
        return {"applied":True}

    def run_tests(self):
        self._clear_bytecode()
        # The fixed command selected by the task is the only executable tool.
        target, selector = self.task["upstream_targeted_tests"].split(" -k ", 1)
        cmd = [self.python,"-m","pytest","-q","--disable-warnings",target,"-k",selector]
        remaining=self.deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError("trial wall limit reached")
        run = subprocess.run(cmd, cwd=self.path, env=self._env(), text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=min(120,remaining))
        return {"exit_code":run.returncode,"passed":run.returncode == 0,"output":run.stdout[-7000:]}

    def diff(self):
        res = subprocess.run(["git","diff","--no-ext-diff","--"], cwd=self.path, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        names = subprocess.run(["git","diff","--name-only"], cwd=self.path, text=True,
                               stdout=subprocess.PIPE, check=True).stdout.splitlines()
        return {"changed_paths":names,"diff":res.stdout[:MAX_PATCH_BYTES]}

    def score(self, challenge_test):
        diff = self.diff()
        paths = set(diff["changed_paths"])
        changed = self.source_relpath in paths and self.test_relpath in paths
        self._clear_bytecode()
        env = self._env()
        remaining=self.deadline-time.monotonic()
        if remaining <= 0: return {"success":False,"required_paths_changed":changed,"error":"trial wall limit reached before scoring","changed_paths":sorted(paths),"diff":diff["diff"]}
        challenge = subprocess.run([self.python,"-m","pytest","-q","--disable-warnings",str(challenge_test)],
                                   cwd=self.path, env=env, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=min(120,remaining))
        return {"success":bool(changed and challenge.returncode == 0),"required_paths_changed":changed,
                "challenge_exit_code":challenge.returncode,"challenge_output":challenge.stdout[-7000:],
                "changed_paths":sorted(paths),"diff":diff["diff"]}


TOOLS = [
    {"type":"function","function":{"name":"list_files","description":"List files in the repository workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"read_file","description":"Read a bounded line range from a repository file.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start_line":{"type":"integer"},"end_line":{"type":"integer"}},"required":["path"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"search_code","description":"Search repository text with a regular expression.","parameters":{"type":"object","properties":{"pattern":{"type":"string"},"path":{"type":"string"}},"required":["pattern"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"apply_patch","description":"Apply a unified git patch to repository files.","parameters":{"type":"object","properties":{"patch":{"type":"string"}},"required":["patch"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"run_tests","description":"Run only the task's fixed repository regression test command.","parameters":{"type":"object","properties":{},"additionalProperties":False}}},
    {"type":"function","function":{"name":"git_diff","description":"Show changed file paths and the current patch.","parameters":{"type":"object","properties":{},"additionalProperties":False}}},
]


def run_trial(api, served_model, model, task, assignment, args, db):
    tid = f"{model}:{task['id']}:{assignment['repetition']}"
    rawpath = args.raw_dir / (tid.replace(":","_") + ".json")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="lh-" + task["id"].lower() + "-", dir=args.work_dir))
    case_root=Path(getattr(args,"case_root",SUITE/"cases"))
    deadline=time.monotonic()+900
    messages = [{"role":"user","content":f"{task['prompt']}\nRepository: {task['repository']['origin']} at {task['repository']['revision']}.\nTarget implementation: {task['source_file']}. Add your regression test to: {task['test_file']}. Workspace path is the repository root. Inspect the failing behavior, make the smallest correct implementation change, run the fixed tests, inspect your diff, then state when finished. Only use the provided workspace tools."}]
    trace = {"trial":{"trial_id":tid,**assignment},"task":task,"requests":[],"tool_trace":[],"tool_errors":[],"started_at":time.time(),"workspace_path":str(work),"status":"running"}
    db.execute("INSERT INTO trials(trial_id,model,task_id,repetition,seed,status,started_at) VALUES(?,?,?,?,?,?,?)",
               (tid,model,task["id"],assignment["repetition"],assignment["seed"],"running",time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())))
    db.commit(); atomic_json(rawpath,trace)
    prompt_tokens = completion_tokens = 0; turns = 0; timings=[]; final_text=""; error=None
    prompt_tps = decode_tps = peak_vram = peak_ram = None
    ws = None; success = 0; scored = {"success":False,"error":"workspace_not_initialized"}
    try:
        ws = Workspace(task, work, args.repo_cache, case_root, args.python, deadline)
        terminated = False
        with Telemetry() as telemetry:
            for turn in range(16):
                remaining=deadline-time.monotonic()
                if remaining <= 0: raise TimeoutError("trial wall limit reached")
                payload={"model":served_model,"messages":messages,"tools":TOOLS,"tool_choice":"auto","temperature":1.0,
                         "top_p":0.95,"top_k":MODELS[model],"seed":assignment["seed"]+turn,"max_tokens":1024,
                         "stream":False,"chat_template_kwargs":{"enable_thinking":True}}
                response=api_request(api,payload,timeout=min(1800,remaining)); turns+=1; trace["requests"].append({"request":payload,"response":response})
                usage=response.get("usage") or {}; prompt_tokens+=int(usage.get("prompt_tokens",0) or 0); completion_tokens+=int(usage.get("completion_tokens",0) or 0)
                choice=response["choices"][0]; msg=choice["message"]; timings.append(response.get("timings") or {})
                trace["usage"]={"prompt_tokens":prompt_tokens,"completion_tokens":completion_tokens}; atomic_json(rawpath,trace)
                calls=msg.get("tool_calls") or []
                if not calls:
                    final_text=msg.get("content") or ""; terminated=True; break
                assistant={"role":"assistant","content":msg.get("content"),"tool_calls":calls}
                if msg.get("reasoning_content") is not None:
                    assistant["reasoning_content"]=msg["reasoning_content"]
                messages.append(assistant)
                for i,call in enumerate(calls):
                    call_id=call.get("id") or f"malformed-{turn}-{i}"
                    fn=call.get("function") or {}; name=fn.get("name")
                    try:
                        params=json.loads(fn.get("arguments") or "{}")
                        if not isinstance(params,dict): raise ValueError("arguments must be an object")
                        if name=="list_files": out=ws.list_files(**params)
                        elif name=="read_file": out=ws.read_file(**params)
                        elif name=="search_code": out=ws.search(**params)
                        elif name=="apply_patch": out=ws.apply_patch(**params)
                        elif name=="run_tests": out=ws.run_tests()
                        elif name=="git_diff": out=ws.diff()
                        else: raise ValueError("unsupported workspace tool")
                        ok=True
                    except Exception as exc:
                        out={"error":type(exc).__name__+": "+str(exc)[:500]}; ok=False
                        trace["tool_errors"].append({"tool":name,"error":out["error"]})
                    event={"tool":name,"arguments":fn.get("arguments"),"result":out,"ok":ok}
                    trace["tool_trace"].append(event)
                    messages.append({"role":"tool","tool_call_id":call_id,"content":json.dumps(out,ensure_ascii=False)[:12000]})
                    atomic_json(rawpath,trace)
                trace["last_turn"]=turn+1
            peak_vram=telemetry.peak_vram; peak_ram=telemetry.peak_ram
        prompt_ms=sum(float(t.get("prompt_ms",0) or 0) for t in timings)
        decode_ms=sum(float(t.get("predicted_ms",0) or 0) for t in timings)
        prompt_tps=(prompt_tokens*1000/prompt_ms) if prompt_ms else None
        decode_tps=(completion_tokens*1000/decode_ms) if decode_ms else None
        if not terminated:
            error="tool_turn_limit"
        scored=ws.score(case_root / task["id"] / "challenge_test.py")
        trace["scoring"]=scored; success=int(scored["success"])
        if not success:
            error="missing_required_files" if not scored.get("required_paths_changed") else "challenge_tests_failed"
        trace["telemetry"]={"prompt_tps":prompt_tps,"decode_tps":decode_tps,"peak_vram_mib":peak_vram,"peak_ram_kib":peak_ram}
    except KeyboardInterrupt:
        success=0; error="interrupted_process"; trace["error"]=error; trace["status"]="interrupted"
        scored={"success":False,"error":error}
        raise
    except Exception as exc:
        success=0; error=type(exc).__name__+": "+str(exc)[:700]
        trace["error"]=error; scored={"success":False,"error":error}
        if "telemetry" in locals():
            peak_vram=telemetry.peak_vram; peak_ram=telemetry.peak_ram
            trace["telemetry"]={"prompt_tps":prompt_tps,"decode_tps":decode_tps,"peak_vram_mib":peak_vram,"peak_ram_kib":peak_ram}
    finally:
        ended=time.time(); elapsed=ended-trace["started_at"]
        trace["finished_at"]=ended; trace["elapsed_s"]=elapsed; trace["final_text"]=final_text
        if trace.get("status") != "interrupted": trace["status"]="complete"
        trace["scoring"]=scored if "scored" in locals() else {"success":False,"error":error}
        atomic_json(rawpath,trace)
        status="failed" if error == "interrupted_process" else "complete"
        db.execute("UPDATE trials SET status=?,success=?,wall_s=?,prompt_tokens=?,completion_tokens=?,turns=?,tool_calls=?,prompt_tps=?,decode_tps=?,peak_vram_mib=?,peak_ram_kib=?,failure_class=?,raw_path=?,response=?,ended_at=? WHERE trial_id=?",
                   (status,success,elapsed,prompt_tokens,completion_tokens,turns,len(trace["tool_trace"]),prompt_tps,decode_tps,peak_vram,peak_ram,error,str(rawpath),final_text,time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(ended)),tid)); db.commit()
        if error != "interrupted_process":
            shutil.rmtree(work,ignore_errors=True)
    print(json.dumps({"trial":tid,"success":success,"wall_s":round(elapsed,2),"prompt_tokens":prompt_tokens,"completion_tokens":completion_tokens,"turns":turns,"tool_calls":len(trace["tool_trace"]),"error":error}),flush=True)


def main():
    verify_long_horizon_freeze()
    ap=argparse.ArgumentParser()
    ap.add_argument("--api",required=True); ap.add_argument("--model",choices=sorted(MODELS),required=True)
    ap.add_argument("--repo-cache",type=Path,required=True); ap.add_argument("--db",type=Path,required=True)
    ap.add_argument("--raw-dir",type=Path,required=True); ap.add_argument("--work-dir",type=Path,required=True)
    ap.add_argument("--python",default="python3"); ap.add_argument("--pilot",action="store_true")
    args=ap.parse_args()
    args.raw_dir.mkdir(parents=True,exist_ok=True); args.work_dir.mkdir(parents=True,exist_ok=True); args.db.parent.mkdir(parents=True,exist_ok=True)
    schedule=json.loads((SUITE/("pilot-schedule.json" if args.pilot else "schedule.json")).read_text())
    tasks={t["id"]:t for t in json.loads((SUITE/"tasks.json").read_text())["tasks"]}
    db=sqlite3.connect(args.db)
    db.execute("CREATE TABLE IF NOT EXISTS trials(trial_id TEXT PRIMARY KEY,model TEXT,task_id TEXT,repetition INTEGER,seed INTEGER,status TEXT,success INTEGER,wall_s REAL,prompt_tokens INTEGER,completion_tokens INTEGER,turns INTEGER,tool_calls INTEGER,prompt_tps REAL,decode_tps REAL,peak_vram_mib INTEGER,peak_ram_kib INTEGER,failure_class TEXT,raw_path TEXT,response TEXT,started_at TEXT,ended_at TEXT)"); db.commit()
    models_req=urllib.request.Request(args.api.rstrip("/")+"/models")
    with urllib.request.urlopen(models_req,timeout=15) as r: served=json.loads(r.read())["data"][0]["id"]
    for assignment in schedule["trials"]:
        if assignment["model"]!=args.model: continue
        tid=f"{args.model}:{assignment['task_id']}:{assignment['repetition']}"
        exists=db.execute("SELECT status FROM trials WHERE trial_id=?",(tid,)).fetchone()
        if exists and exists[0] in ("complete","failed","interrupted"):
            continue
        if exists and exists[0]=="running":
            prior=db.execute("SELECT raw_path FROM trials WHERE trial_id=?",(tid,)).fetchone()
            interrupted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
            if prior and prior[0] and Path(prior[0]).exists():
                raw=Path(prior[0]); payload=json.loads(raw.read_text()); payload["status"]="interrupted"; payload["recovered_at"]=interrupted_at
                payload["failure_class"]="interrupted_process"; atomic_json(raw,payload)
                partial=Path(payload.get("workspace_path",""))
                if partial.is_dir():
                    target=args.raw_dir/"interrupted-workspaces"/tid.replace(":","_")
                    target.parent.mkdir(parents=True,exist_ok=True)
                    if target.exists(): shutil.rmtree(target,ignore_errors=True)
                    shutil.move(str(partial),str(target)); payload["workspace_archive"]=str(target); atomic_json(raw,payload)
            db.execute("UPDATE trials SET status='interrupted',success=0,failure_class='interrupted_process',ended_at=? WHERE trial_id=?",
                       (interrupted_at,tid)); db.commit(); continue
        run_trial(args.api,served,args.model,tasks[assignment["task_id"]],assignment,args,db)
    db.close()


if __name__=="__main__": main()
