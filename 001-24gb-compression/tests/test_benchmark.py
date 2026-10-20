import json, unittest, threading, tempfile, sys, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from src.validate import ROOT, score, validate
from src.tools import execute_actions
from src.run import main as run_main, recover_started_trial

class BenchmarkChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.tasks = json.loads((ROOT / "benchmark/tasks.json").read_text())
    def test_full_suite_positive_and_negative_controls(self): validate()
    def test_all_eight_simulated_tool_actions_execute(self):
        tasks = [t for t in self.tasks if t["category"] == "tool_use"]
        self.assertEqual(len(tasks), 8)
        for task in tasks:
            trace=execute_actions(task["expected_calls"],task["id"])
            self.assertTrue(score(task,task["reference_response"],trace))
            self.assertFalse(score(task,task["reference_response"],execute_actions(task["negative_control"],task["id"])))
    def test_all_six_multi_step_workflows_reach_expected_state(self):
        tasks=[t for t in self.tasks if t["category"]=="multi_step"]
        self.assertEqual(len(tasks),6)
        for task in tasks:
            self.assertTrue(score(task,task["reference_response"],execute_actions(task["expected_calls"],task["id"])),task["id"])
            self.assertFalse(score(task,task["reference_response"],execute_actions(task["negative_control"],task["id"])),task["id"])
    def test_simulator_rejects_mutations_and_unknown_calls(self):
        for call in ([{"tool":"close","id":"T-204"}], [{"tool":"execute","sql":"DELETE FROM orders;"}]):
            self.assertFalse(execute_actions(call,"TO03")[0]["ok"])
    def test_candidate_code_rejects_imports_and_attributes(self):
        task = next(t for t in self.tasks if t.get("kind") == "python_function")
        self.assertFalse(score(task, {"code":"import os\ndef solve(xs): return []"}))
        self.assertFalse(score(task, {"code":"def solve(xs): return xs.__class__"}))

    def test_terminal_equivalent_forms_and_structured_direct_values(self):
        tasks={t["id"]:t for t in self.tasks}
        self.assertTrue(score(tasks["TE01"], {"result":"ls -a -l"}))
        self.assertFalse(score(tasks["TE01"], {"result":"ls -l"}))
        self.assertTrue(score(tasks["ST01"], [{"name":"Ada","score":9},{"name":"Lin","score":8}]))
        self.assertFalse(score(tasks["ST01"], {"result":[{"name":"Ada","score":9},{"name":"Lin","score":8}]}))
        self.assertTrue(score(tasks["ST05"], 5))
        self.assertFalse(score(tasks["ST05"], True))
        self.assertFalse(score(tasks["ST05"], "NaN"))

    def test_interrupted_trial_is_terminal_and_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); raw=root/"raw"; raw.mkdir(); db=sqlite3.connect(root/"checkpoint.sqlite3")
            db.execute("CREATE TABLE trials (trial_id TEXT PRIMARY KEY,status TEXT,started_at TEXT,success INTEGER,wall_s REAL,failure_class TEXT,raw_path TEXT,response TEXT,ended_at TEXT)")
            db.execute("INSERT INTO trials VALUES (?,?,?,?,?,?,?,?,?)",("nemotron:CO01:1","running","2026-10-15T21:00:00Z",None,None,None,None,None,None)); db.commit()
            assignment={"model":"nemotron","task_id":"CO01","repetition":1,"seed":101}
            self.assertTrue(recover_started_trial(db,"nemotron:CO01:1",assignment,raw))
            values=db.execute("SELECT status,success,failure_class FROM trials").fetchone()
            self.assertEqual(values,("failed",0,"interrupted_process"))
            trace=json.loads(next(raw.glob("*.json")).read_text())
            self.assertIn("not retried",trace["note"])
            self.assertTrue(recover_started_trial(db,"nemotron:CO01:1",assignment,raw))
            self.assertEqual(len(list(raw.glob("*.json"))),1)
            db.close()

    def test_checkpointed_runner_against_openai_compatible_fixture(self):
        task = next(t for t in self.tasks if t["id"] == "CO01")
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                body = {"data":[{"id":"fixture-model"}]}
                self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(body).encode())
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                prompt=next(m["content"] for m in payload["messages"] if m["role"]=="user")
                if "calculator tool" in prompt:
                    target=next(t for t in self_test_tasks if t["id"]=="TO02"); sequence=target["expected_calls"]
                elif "shipment needs five cable units" in prompt:
                    target=next(t for t in self_test_tasks if t["id"]=="MU01"); sequence=target["expected_calls"]
                elif "hidden and non-hidden files" in prompt:
                    target=next(t for t in self_test_tasks if t["id"]=="TE01"); sequence=[]
                elif "convert rows" in prompt:
                    target=next(t for t in self_test_tasks if t["id"]=="ST01"); sequence=[]
                else:
                    target=task; sequence=[]
                tool_messages=[m for m in payload["messages"] if m["role"]=="tool"]
                if sequence and len(tool_messages)<len(sequence):
                    action=sequence[len(tool_messages)]
                    call={"id":f"fixture-{len(tool_messages)}","type":"function","function":{"name":action["tool"],"arguments":json.dumps({k:v for k,v in action.items() if k!="tool"})}}
                    message={"tool_calls":[call],"content":None}; finish="tool_calls"; answer=None
                else:
                    answer=json.dumps(target["reference_response"]); message={"content":answer}; finish="stop"
                body={"choices":[{"message":message,"finish_reason":finish}],"usage":{"prompt_tokens":12,"completion_tokens":8}}
                self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(body).encode())
        self_test_tasks=self.tasks
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                schedule=Path(tmp)/"schedule.json"; schedule.write_text(json.dumps({"trials":[{"model":"nemotron","task_id":"CO01","repetition":1,"seed":101},{"model":"nemotron","task_id":"TE01","repetition":1,"seed":102},{"model":"nemotron","task_id":"ST01","repetition":1,"seed":103},{"model":"nemotron","task_id":"TO02","repetition":1,"seed":104},{"model":"nemotron","task_id":"MU01","repetition":1,"seed":105}]}))
                db=Path(tmp)/"checkpoint.sqlite3"; raw=Path(tmp)/"raw"
                argv=["src.run","--api",f"http://127.0.0.1:{server.server_port}/v1","--model","nemotron","--schedule",str(schedule),"--db",str(db),"--raw-dir",str(raw)]
                with patch("sys.argv",argv), patch("src.run.verify_freeze",lambda:None): run_main()
                rows=sqlite3.connect(db).execute("SELECT task_id,status,success FROM trials ORDER BY task_id").fetchall()
                self.assertEqual(rows,[("CO01","complete",1),("MU01","complete",1),("ST01","complete",1),("TE01","complete",1),("TO02","complete",1)])
                self.assertEqual(len(list(raw.glob("*.json"))),5)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

if __name__ == "__main__": unittest.main()
