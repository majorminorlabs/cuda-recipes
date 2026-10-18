#!/usr/bin/env python3
"""GPU-free scorer, auto-checkpoint, and combined-validator smoke test."""
import csv,json,shutil,subprocess,sys,tempfile,time
from pathlib import Path
import run_phase1
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"DATA"/"code"
def main():
 subprocess.run([sys.executable,str(ROOT/"scripts/code/score.py")],check=True)
 qs=[json.loads(x) for x in (DATA/"questions.jsonl").read_text().splitlines() if x]
 with tempfile.TemporaryDirectory(prefix="003-code-checkpoint-") as td:
  scratch=Path(td); shutil.copytree(DATA,scratch/"DATA") ; sd=scratch/"DATA"; (sd/"answer-results.csv").write_text("model,question_id,generated_tokens\n"+"".join(f"qwen36_35b_a3b,{q['question_id']},24\n" for q in qs))
  original=run_phase1.DATA; run_phase1.DATA=sd
  try:
   cp=scratch/"budget-checkpoint.json"; run_phase1.make_checkpoint("qwen36_35b_a3b",time.time(),cp)
   assert cp.exists() and (scratch/"budget-checkpoint-decision.txt").exists(),"checkpoint auto-write failed"
  finally: run_phase1.DATA=original
 result=subprocess.run([sys.executable,str(ROOT/"validate.py")],cwd=ROOT,text=True,capture_output=True,check=True)
 if "PENDING: code arm GPU CSVs are header-only." not in result.stdout: raise AssertionError(result.stdout)
 print("PASS: scratch checkpoint auto-write; combined validator reports prose PASS and code PENDING.")
if __name__=="__main__": main()
