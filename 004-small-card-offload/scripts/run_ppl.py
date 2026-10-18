#!/usr/bin/env python3
"""Run llama-perplexity on Wikitext-2 test for each selected offload budget."""
import argparse,csv,hashlib,json,os,pathlib,re,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/"DATA";RAW=ROOT/"_internal"/"raw"
MODEL=os.environ.get("MODEL_FILE","");PPL=os.environ.get("LLAMA_PERPLEXITY","llama-perplexity");DATASET=os.environ.get("WIKITEXT_FILE","")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--timeout",type=int,default=1800);a=ap.parse_args()
 if not MODEL or not pathlib.Path(MODEL).is_file():ap.error("Set MODEL_FILE to the pinned GGUF")
 if not DATASET or not pathlib.Path(DATASET).is_file():ap.error("Set WIKITEXT_FILE to wikitext-2 test text")
 host=json.loads((DATA/"host.json").read_text())
 digest=hashlib.sha256(pathlib.Path(DATASET).read_bytes()).hexdigest()
 if host.get("wikitext_sha256")!=digest:ap.error("Wikitext-2 test file does not match host.json SHA-256")
 cal=list(csv.DictReader((DATA/"calibration.csv").open()));chosen={int(r["budget_gb"]):r for r in cal if r["chosen"]=="1"}
 fields=["budget_gb","n_cpu_moe","ctx","chunks","op_offload","ppl","ppl_err"]
 with (DATA/"ppl-results.csv").open("w",newline="") as f:
  csv.DictWriter(f,fieldnames=fields).writeheader()
 for b,r in sorted(chosen.items()):
  n=int(r["n_cpu_moe"]);op_offload=int(n==0)
  cmd=[PPL,"-m",MODEL,"-f",DATASET,"-c","2048","--chunks","8","-ngl","99","--n-cpu-moe",str(n),"-ctk","q8_0","-ctv","q8_0","-fa","on"]
  if n>0:cmd.append("--no-op-offload")
  RAW.mkdir(parents=True,exist_ok=True);start=time.monotonic()
  try:
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=a.timeout);stdout=p.stdout;stderr=p.stderr;rc=p.returncode
  except subprocess.TimeoutExpired as e:
   stdout=e.stdout or "";stderr=e.stderr or "";rc=-1
   if isinstance(stdout,bytes):stdout=stdout.decode(errors="replace")
   if isinstance(stderr,bytes):stderr=stderr.decode(errors="replace")
   stderr=(stderr+"\n" if stderr else "")+f"timed out after {a.timeout}s"
  (RAW/f"ppl-{b}gb.stdout").write_text(stdout);(RAW/f"ppl-{b}gb.stderr").write_text(stderr)
  allout=stdout+"\n"+stderr
  # This pinned build emits one cumulative [chunk]PPL value after each chunk.
  matches=list(re.finditer(r"\[\d+\]\s*([0-9]+(?:\.[0-9]+)?)\s*,|(?:perplexity|ppl)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)(?:\s*(?:\+/-|±)\s*([0-9]+(?:\.[0-9]+)?))?",allout,re.I))
  m=matches[-1] if matches else None
  value=float(next(g for g in m.groups()[:2] if g)) if m and rc==0 else ""
  unc=float(m.group(3)) if m and m.group(3) and rc==0 else ""
  err="" if rc==0 and m else (allout.strip().splitlines()[-1] if allout.strip() else f"exit {rc}; no perplexity parsed")
  with (DATA/"ppl-results.csv").open("a",newline="") as f:
   w=csv.DictWriter(f,fieldnames=fields)
   w.writerow(dict(budget_gb=b,n_cpu_moe=n,ctx=2048,chunks=8,op_offload=op_offload,ppl=value,ppl_err=unc if not err else err));f.flush()
  print(f"{b}GB perplexity={value} uncertainty={unc} elapsed={time.monotonic()-start:.1f}s",flush=True)
 return 0
if __name__=="__main__":sys.exit(main())
