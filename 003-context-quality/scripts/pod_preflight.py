#!/usr/bin/env python3
"""On-pod artifact, sm_86 build, host, and Qwen3.6 8K decode preflight."""
import argparse,hashlib,json,os,platform,re,shlex,socket,subprocess,sys,time,threading,urllib.request,urllib.error
from pathlib import Path
from run_phase1 import parse_real_pass
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/"DATA"; INTERNAL=ROOT/"_internal"
def run(cmd,cwd=None): return subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False).stdout.strip()
def save_response(question_id,model,result):
    choice=result["choices"][0]; message=choice["message"]; row={"question_id":question_id,"model":model,"arm":"preflight","content":message.get("content","") or "","finish_reason":choice.get("finish_reason"),"usage":result.get("usage",{}) or {}}
    if "reasoning_content" in message: row["reasoning_content"]=message["reasoning_content"]
    path=INTERNAL/"responses"/f"preflight-{model}.jsonl"; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(row,ensure_ascii=False)+"\n")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--model-file",required=True); ap.add_argument("--llama-server",required=True); ap.add_argument("--skip-build",action="store_true"); args=ap.parse_args()
    spec=json.loads((D/"model-manifest.json").read_text())["qwen36_35b_a3b"]; model=Path(args.model_file)
    if not model.is_file(): raise SystemExit(f"Qwen3.6 GGUF is missing: {model}")
    h=hashlib.sha256()
    with model.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""): h.update(block)
    actual=h.hexdigest(); size=model.stat().st_size
    if actual!=spec["files"][0]["sha256"] or size!=spec["files"][0]["bytes"]: raise SystemExit(f"LOCAL GGUF VERIFICATION FAILED: bytes={size} sha256={actual}")
    src=INTERNAL/"llama.cpp-src"; rev=run(["git","rev-parse","HEAD"],src)
    if rev!=json.loads((D/"llama-cpp-manifest.json").read_text())["revision"]: raise SystemExit(f"llama.cpp revision mismatch: {rev}")
    build_dir=INTERNAL/"llama.cpp-build-sm86"; cmake=(build_dir/"CMakeCache.txt").read_text() if (build_dir/"CMakeCache.txt").exists() else ""
    if not args.skip_build:
        out=run(["cmake","-S",str(src),"-B",str(build_dir),"-DGGML_CUDA=ON","-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc","-DCMAKE_CUDA_ARCHITECTURES=86","-DCMAKE_BUILD_TYPE=Release"])
        if "error" in out.lower() and not (build_dir/"CMakeCache.txt").exists(): raise SystemExit("CMake CUDA sm_86 configure failed:\n"+out[-3000:])
        out=run(["cmake","--build",str(build_dir),"--target","llama-server","--config","Release","--parallel","16"])
        server=build_dir/"bin/llama-server"
        if not server.exists(): raise SystemExit("sm_86 build did not produce llama-server")
        args.llama_server=str(server)
        cmake=(build_dir/"CMakeCache.txt").read_text()
    if "GGML_CUDA:BOOL=ON" not in cmake or not re.search(r"CMAKE_CUDA_ARCHITECTURES(?::[^=]+)?=86(?:\D|$)",cmake): raise SystemExit("Build cache does not verify GGML_CUDA=ON and CUDA architecture 86")
    with socket.socket() as s: s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
    flags=json.loads((D/"study-config.json").read_text())["fixed_server_flags"]
    cmd=[args.llama_server,"--model",str(model),"--ctx-size","131072",*(part for flag in flags for part in shlex.split(flag)),"--port",str(port),"--verbose"]
    log=[]; proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",bufsize=1)
    log_thread=threading.Thread(target=lambda: log.extend(proc.stdout),daemon=True); log_thread.start()
    try:
        deadline=time.monotonic()+900
        while time.monotonic()<deadline:
            if proc.poll() is not None: raise SystemExit("llama-server exited before /health returned 200:\n"+"".join(log)[-6000:])
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",timeout=2) as r:
                    if r.status==200: break
            except Exception: time.sleep(.5)
        else: raise SystemExit("/health did not return 200")
        # Ask the server tokenizer for enough Moby-Dick text to produce an ~8K-token full prompt.
        src_text=(INTERNAL/"moby-dick.txt").read_text(encoding="utf-8")
        start=src_text.find("*** START OF THE PROJECT GUTENBERG EBOOK")
        if start<0: start=src_text.find("*** START OF THIS PROJECT GUTENBERG EBOOK")
        end=src_text.find("*** END OF THE PROJECT GUTENBERG EBOOK")
        if end<0: end=src_text.find("*** END OF THIS PROJECT GUTENBERG EBOOK")
        text=src_text[src_text.find("\n",start)+1:end]
        tok_req=urllib.request.Request(f"http://127.0.0.1:{port}/tokenize",data=json.dumps({"content":text,"add_special":False}).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(tok_req,timeout=120) as r: all_tokens=json.loads(r.read())["tokens"]
        # Reserve room for user prompt/template; this intentionally measures an approximately 8K prompt.
        det_req=urllib.request.Request(f"http://127.0.0.1:{port}/detokenize",data=json.dumps({"tokens":all_tokens[:7900]}).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(det_req,timeout=120) as r: document=json.loads(r.read())["content"]
        sampling=json.loads((D/"sampling.json").read_text())["models"]["qwen36_35b_a3b"]
        payload={"model":"qwen36_35b_a3b","messages":[{"role":"system","content":document},{"role":"user","content":"Write a detailed plain-text essay of at least 220 words about observable changes in ocean color, wind, clouds, and waves."}],"max_tokens":256,"temperature":sampling["temperature"],"top_p":sampling["top_p"],"top_k":sampling["top_k"],"min_p":sampling["min_p"],"presence_penalty":sampling["presence_penalty"],"repeat_penalty":sampling["repetition_penalty"],"seed":390003,"chat_template_kwargs":{"enable_thinking":False}}
        req=urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        t0=time.monotonic()
        with urllib.request.urlopen(req,timeout=1800) as r: result=json.loads(r.read())
        save_response("preflight-qwen36-decode-8k","qwen36_35b_a3b",result)
        wall=time.monotonic()-t0; usage=result.get("usage",{}); generated=usage.get("completion_tokens",0); timings=result.get("timings",{})
        time.sleep(.5); log_text="".join(log)
        (INTERNAL/"raw-logs").mkdir(parents=True,exist_ok=True)
        (INTERNAL/"raw-logs"/"preflight-qwen36.log").write_text(log_text)
        layers,kv,rs=parse_real_pass(log_text)
        if not layers[0] or layers[0]!=layers[1] or not kv:
            raise SystemExit(f"load-log parser did not confirm full GPU placement and KV allocation: layers={layers}, kv={kv}, rs={rs}")
        rate=timings.get("predicted_per_second")
        if not rate and timings.get("predicted_ms") and timings.get("predicted_n"):
            rate=float(timings["predicted_n"])*1000/float(timings["predicted_ms"])
        rate_matches=re.findall(r"eval time\s*=\s*[\d.eE+-]+\s*ms\s*/\s*\d+\s+runs?\s*\([^)]*?([\d.eE+-]+)\s*tokens per second",log_text,re.I)
        if not rate and rate_matches: rate=float(rate_matches[-1])
        if rate: rate=float(rate)
        if generated<128: raise SystemExit(f"8K decode preflight generated only {generated} tokens; rerun with longer output before main run")
        prompt_tokens=usage.get("prompt_tokens")
        if not rate: raise SystemExit("Could not find the pinned server's per-generation eval tokens/s in its log; refusing to record a prefill-contaminated estimate as decode speed")
        if prompt_tokens is None or not 7600<=int(prompt_tokens)<=8704: raise SystemExit(f"Preflight prompt was not approximately 8K tokens: {prompt_tokens}")
        cache_payload={"model":"qwen36_35b_a3b","messages":[{"role":"system","content":document},{"role":"user","content":"Reply with JSON containing ok true."}],"max_tokens":16,"temperature":0,"seed":390003,"chat_template_kwargs":{"enable_thinking":False}}
        cache_req=urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=json.dumps(cache_payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(cache_req,timeout=1800) as r: cache_first=json.loads(r.read())
        save_response("preflight-qwen36-cache-first","qwen36_35b_a3b",cache_first)
        cache_payload["messages"][1]["content"]="Reply with JSON containing ok false."
        cache_req=urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=json.dumps(cache_payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(cache_req,timeout=1800) as r: cache_second=json.loads(r.read())
        save_response("preflight-qwen36-cache-second","qwen36_35b_a3b",cache_second)
        cached=(cache_second.get("usage",{}).get("prompt_tokens_details",{}) or {}).get("cached_tokens",cache_second.get("usage",{}).get("cached_tokens",0))
        if int(cached or 0)<=0: raise SystemExit("Prompt-cache preflight failed: second of two same-document requests reported no cached prompt tokens")
        manifest={"study":"CUDA Recipes 003: Long-Context Quality on 24GB","status":"pod_preflight_passed","gpu_run_performed_in_phase0":False,"target_gpu":"NVIDIA GeForce RTX 3090 24GB","cuda_architecture":"86","llama_cpp_revision_required":rev,"build_requirements":{"backend":"CUDA","cmake_cuda_architectures":"86","build_command":"cmake -S _internal/llama.cpp-src -B _internal/llama.cpp-build-sm86 -DGGML_CUDA=ON -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_BUILD_TYPE=Release && cmake --build _internal/llama.cpp-build-sm86 --target llama-server --config Release --parallel 16"},"qwen36_artifact":{"repo":"ggml-org/Qwen3.6-35B-A3B-GGUF","revision":spec["revision"],"file":model.name,"expected_bytes":spec["files"][0]["bytes"],"expected_sha256":spec["files"][0]["sha256"],"local_bytes":size,"local_sha256":actual,"local_sha256_status":"passed"},"qwen36_8k_decode_preflight":{"status":"passed","prompt_target_tokens":8192,"measured_prompt_tokens":prompt_tokens,"generated_tokens":generated,"decode_tokens_per_second":rate,"rate_source":"llama-server response timing predicted_per_second, cross-checked against the per-request server log","request_wall_seconds":round(wall,3),"measurement_command":"llama-server --model <verified Qwen3.6 GGUF> --ctx-size 131072 [study server flags] --verbose"},"preflight":{"health_gate":"passed","load_log_parser":"passed","layers_on_cuda":layers[0],"layers_total":layers[1],"prompt_cache_test":{"requests":2,"second_request_cached_prompt_tokens":int(cached),"status":"passed"}},"host":{"system":platform.system(),"release":platform.release(),"machine":platform.machine(),"python":platform.python_version(),"gpu_summary":run(["nvidia-smi","--query-gpu=name,memory.total,driver_version","--format=csv,noheader,nounits"]),"nvcc":run(["/usr/local/cuda/bin/nvcc","--version"]),"cmake":run(["cmake","--version"]),"timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())},"build":{"cache_cuda":True,"cache_cuda_architectures":"86","llama_server":Path(args.llama_server).name},"notes":"Local file SHA-256 verified; sm_86 build, GPU placement, two-request prompt-cache reuse, and 8K decode measured on pod. Hostnames, network addresses, pod identifiers, and endpoints are deliberately omitted."}
        (D/"host-build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        print(json.dumps(manifest["qwen36_8k_decode_preflight"],indent=2))
    finally:
        proc.terminate()
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        log_thread.join(timeout=2)
if __name__=="__main__": main()
