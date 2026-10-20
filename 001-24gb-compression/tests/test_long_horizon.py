import json
import os
import http.server
import sqlite3
import subprocess
import threading
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.long_horizon import Workspace, clean_relative, run_trial

ROOT=Path(__file__).resolve().parents[1]
SUITE=ROOT/"benchmark/long_horizon_v1"


def test_frozen_schedule_is_complete_and_paired():
    scored=json.loads((SUITE/"schedule.json").read_text())["trials"]
    pilot=json.loads((SUITE/"pilot-schedule.json").read_text())["trials"]
    assert len(scored)==60 and len(pilot)==10
    assert len({(r["model"],r["task_id"],r["repetition"]) for r in scored})==60
    left={(r["task_id"],r["repetition"]):r["seed"] for r in scored if r["model"]=="qwen"}
    right={(r["task_id"],r["repetition"]):r["seed"] for r in scored if r["model"]=="nemotron"}
    assert left==right and len(left)==30
    assert not ({r["seed"] for r in scored}&{r["seed"] for r in pilot})


def test_workspace_allowlist_patch_tests_and_outcome_score(tmp_path):
    cache=tmp_path/"cache"/"attrs"; cache.mkdir(parents=True)
    (cache/"src").mkdir(); (cache/"tests").mkdir()
    (cache/"src/example.py").write_text("VALUE = 1\n")
    (cache/"tests/test_candidate.py").write_text("def test_project_fixture():\n    assert True\n")
    subprocess.run(["git","init","-q"],cwd=cache,check=True)
    subprocess.run(["git","config","user.email","unit@test"],cwd=cache,check=True)
    subprocess.run(["git","config","user.name","unit"],cwd=cache,check=True)
    subprocess.run(["git","add","-A"],cwd=cache,check=True)
    subprocess.run(["git","commit","-qm","fixture"],cwd=cache,check=True)
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=cache,text=True).strip()
    case_root=tmp_path/"cases"; case=case_root/"SYN01"; case.mkdir(parents=True)
    (case/"starter.patch").write_text("")
    challenge=case/"challenge_test.py"
    challenge.write_text("import example\ndef test_hidden_outcome():\n    assert example.VALUE == 2\n")
    task={"id":"SYN01","repo":"attrs","repository":{"revision":revision},"source_file":"src/example.py",
          "test_file":"tests/test_candidate.py","upstream_targeted_tests":"tests/test_candidate.py -k project_fixture"}
    ws=Workspace(task,tmp_path/"work",tmp_path/"cache",case_root,os.sys.executable,deadline=__import__("time").monotonic()+120)
    assert ws.list_files("src")["entries"][0]["path"]=="src/example.py"
    assert "VALUE = 1" in ws.read_file("src/example.py")["text"]
    assert "VALUE" in ws.search("VALUE")["matches"]
    assert ws.run_tests()["passed"]
    patch="""--- a/src/example.py
+++ b/src/example.py
@@ -1 +1 @@
-VALUE = 1
+VALUE = 2
--- a/tests/test_candidate.py
+++ b/tests/test_candidate.py
@@ -1,2 +1,6 @@
 def test_project_fixture():
     assert True
+
+def test_regression_value():
+    import example
+    assert example.VALUE == 2
"""
    assert ws.apply_patch(patch)["applied"]
    result=ws.score(challenge)
    assert result["success"] and result["required_paths_changed"]


def test_workspace_paths_reject_escape_and_symlink(tmp_path):
    root=tmp_path/"root"; root.mkdir(); outside=tmp_path/"outside"; outside.write_text("secret")
    (root/"escape").symlink_to(outside)
    with pytest.raises(ValueError): clean_relative(root,"../outside")
    with pytest.raises(ValueError): clean_relative(root,"escape")


def test_checkpointed_agent_loop_executes_tools_and_preserves_reasoning(tmp_path):
    cache=tmp_path/"cache"/"attrs"; cache.mkdir(parents=True)
    (cache/"src").mkdir(); (cache/"tests").mkdir()
    (cache/"src/example.py").write_text("VALUE = 2\n")
    (cache/"tests/test_candidate.py").write_text("def test_base_case():\n    assert True\n")
    subprocess.run(["git","init","-q"],cwd=cache,check=True)
    subprocess.run(["git","config","user.email","unit@test"],cwd=cache,check=True)
    subprocess.run(["git","config","user.name","unit"],cwd=cache,check=True)
    subprocess.run(["git","add","-A"],cwd=cache,check=True)
    subprocess.run(["git","commit","-qm","fixture"],cwd=cache,check=True)
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=cache,text=True).strip()
    case_root=tmp_path/"cases"; case=case_root/"SYN02"; case.mkdir(parents=True)
    starter="""--- a/src/example.py
+++ b/src/example.py
@@ -1 +1 @@
-VALUE = 2
+VALUE = 1
"""
    reference="""--- a/src/example.py
+++ b/src/example.py
@@ -1 +1 @@
-VALUE = 1
+VALUE = 2
--- a/tests/test_candidate.py
+++ b/tests/test_candidate.py
@@ -1,2 +1,6 @@
 def test_base_case():
     assert True
+
+def test_regression_case():
+    from example import VALUE
+    assert VALUE == 2
"""
    (case/"starter.patch").write_text(starter)
    (case/"reference.patch").write_text(reference)
    challenge=case/"challenge_test.py"
    challenge.write_text("from example import VALUE\ndef test_hidden_goal():\n    assert VALUE == 2\n")
    task={"id":"SYN02","repo":"attrs","repository":{"origin":"local","revision":revision},
          "source_file":"src/example.py","test_file":"tests/test_candidate.py","prompt":"Fix example value.",
          "upstream_targeted_tests":"tests/test_candidate.py -k base_case"}
    responses=[]; payloads=[]; tool_patch=reference
    def completion(call=None,reasoning="step reasoning"):
        if call:
            message={"role":"assistant","content":"","reasoning_content":reasoning,"tool_calls":[{"id":f"call-{len(payloads)}","type":"function","function":{"name":call,"arguments":json.dumps({"patch":tool_patch} if call=="apply_patch" else {})}}]}
            finish="tool_calls"
        else:
            message={"role":"assistant","content":"Finished implementation."}; finish="stop"
        return {"choices":[{"index":0,"finish_reason":finish,"message":message}],"usage":{"prompt_tokens":12,"completion_tokens":5},"timings":{"prompt_ms":20,"predicted_ms":30}}
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            size=int(self.headers.get("Content-Length","0")); payload=json.loads(self.rfile.read(size)); payloads.append(payload)
            sequence=["apply_patch","run_tests","git_diff",None]
            response=completion(sequence[len(payloads)-1])
            encoded=json.dumps(response).encode(); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    db=sqlite3.connect(tmp_path/"runs.sqlite3")
    db.execute("CREATE TABLE trials(trial_id TEXT PRIMARY KEY,model TEXT,task_id TEXT,repetition INTEGER,seed INTEGER,status TEXT,success INTEGER,wall_s REAL,prompt_tokens INTEGER,completion_tokens INTEGER,turns INTEGER,tool_calls INTEGER,prompt_tps REAL,decode_tps REAL,peak_vram_mib INTEGER,peak_ram_kib INTEGER,failure_class TEXT,raw_path TEXT,response TEXT,started_at TEXT,ended_at TEXT)")
    args=SimpleNamespace(raw_dir=tmp_path/"raw",work_dir=tmp_path/"work",repo_cache=tmp_path/"cache",python=os.sys.executable,case_root=case_root)
    try:
        run_trial(f"http://127.0.0.1:{server.server_port}/v1","fake-model","qwen",task,{"task_id":"SYN02","repetition":1,"seed":7},args,db)
    finally:
        server.shutdown(); thread.join(timeout=2); server.server_close()
    row=db.execute("SELECT success,turns,tool_calls,prompt_tokens,completion_tokens FROM trials").fetchone(); db.close()
    assert row==(1,4,3,48,20)
    assert "reasoning_content" in payloads[1]["messages"][-2]
    trace=json.loads(next((tmp_path/"raw").glob("*.json")).read_text())
    assert trace["scoring"]["success"] is True and all(x["ok"] for x in trace["tool_trace"])
