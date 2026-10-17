#!/usr/bin/env python3
"""On-pod no-thinking preflight for all models; exits before main run on any failure."""
import argparse,hashlib,json,re,socket,sys
from pathlib import Path
from run_phase1 import CFG,DATA,INTERNAL,MODELS,health,launch,request,stop
from score import parse

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--llama-server",default="llama-server"); ap.add_argument("--model-file",action="append",required=True,help="MODEL=PATH; provide all three"); args=ap.parse_args()
    paths={}
    for item in args.model_file:
        model,path=item.split("=",1); paths[model]=Path(path)
    if set(paths)!=set(MODELS): raise SystemExit(f"provide --model-file MODEL=PATH for each of {MODELS}")
    qs=[json.loads(x) for x in (DATA/"questions.jsonl").read_text().splitlines() if x]; controls=[q for q in qs if q["length_label"]=="control"][:3]
    if len(controls)!=3: raise SystemExit("fewer than three frozen control questions")
    sampling=json.loads((DATA/"sampling.json").read_text())["models"]
    for model in MODELS:
        with socket.socket() as s: s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
        proc,lines,thread,cmd=launch(args.llama_server,model,paths[model],16384,port)
        try:
            import time
            deadline=time.monotonic()+900
            while time.monotonic()<deadline and proc.poll() is None and health(port)!=200: time.sleep(.4)
            if health(port)!=200: raise RuntimeError(f"{model}: health gate failed")
            for q in controls:
                params=sampling[model]; seed=int(hashlib.sha256(q["question_id"].encode()).hexdigest()[:8],16)
                payload={"model":model,"messages":[{"role":"system","content":(DATA/"documents/control.txt").read_text()},{"role":"user","content":q["prompt"]}],"max_tokens":128,"seed":seed,"temperature":params["temperature"],"top_p":params["top_p"],"chat_template_kwargs":{"enable_thinking":False}}
                for key in ("top_k","min_p","presence_penalty","repetition_penalty"):
                    if key in params: payload["repeat_penalty" if key=="repetition_penalty" else key]=params[key]
                result=request(port,payload); choice=result["choices"][0]; msg=choice["message"]; content=msg.get("content","") or ""; reason=msg.get("reasoning_content","") or ""; usage=result.get("usage",{}) or {}; generated=usage.get("completion_tokens"); generated=int(generated) if generated is not None else -1; ok=not reason and not re.search(r"<\s*think\b",content,re.I) and parse(content) is not None and 0<generated<128
                raw={"question_id":q["question_id"],"model":model,"arm":"preflight","content":content,"finish_reason":choice.get("finish_reason"),"usage":usage,"preflight_pass":ok}
                if "reasoning_content" in msg: raw["reasoning_content"]=msg["reasoning_content"]
                out=INTERNAL/"responses"/f"preflight-{model}.jsonl"; out.parent.mkdir(parents=True,exist_ok=True)
                with out.open("a",encoding="utf-8") as f: f.write(json.dumps(raw,ensure_ascii=False)+"\n")
                print(f"{model} {q['question_id']}: {'PASS' if ok else 'FAIL'} generated_tokens={generated}")
                if not ok: raise RuntimeError(f"{model}: no-thinking/parser/token preflight failed; main run must not start")
        finally:
            stop(proc); thread.join(timeout=3)
    print("PASS: all models passed no-thinking preflight; main run may start.")

if __name__=="__main__": main()
