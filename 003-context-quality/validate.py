#!/usr/bin/env python3
"""Validate the completed prose arm and pending/complete code arm."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent; D=ROOT/"DATA"; CODE=D/"code"; INTERNAL=ROOT/"_internal"
COLS={"fit-results.csv":["model","ctx_size","loaded_full_gpu","layers_on_cuda","layers_total","kv_buffer_mib","rs_buffer_mib","peak_vram_mib","error"],"prefill-results.csv":["model","length_label","doc_id","prompt_tokens","prefill_s","prefill_tps","peak_vram_mib"],"answer-results.csv":["model","length_label","doc_id","question_id","task_type","position","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","correct","format_strict_correct","failure_class"]}
FAILS={"","wrong_answer","invalid_json","truncated","error"}
def rows(folder,name,cols=None):
 with (folder/name).open(newline="") as f:
  r=csv.DictReader(f); assert r.fieldnames==(cols or COLS[name]),f"{folder/name}: header mismatch {r.fieldnames}"; return list(r)
def validate_prose():
 for n in COLS: rows(D,n)
 a=rows(D,"answer-results.csv"); fit=rows(D,"fit-results.csv"); pre=rows(D,"prefill-results.csv")
 e=D/"exploratory-thinking-on"; old=COLS["answer-results.csv"][:11]+["failure_class"]
 ea=rows(e,"answer-results.csv",old); rows(e,"fit-results.csv"); rows(e,"prefill-results.csv")
 if not ea or {r["model"] for r in ea}!={"qwen36_35b_a3b"}: raise AssertionError("exploratory arm malformed")
 if not a: raise AssertionError("prose primary answer CSV is empty")
 cfg=json.loads((D/"study-config.json").read_text()); qs=[json.loads(x) for x in (D/"questions.jsonl").read_text().splitlines() if x]; qids={q["question_id"] for q in qs}; required=set(cfg["models"]); errors=[]
 if {r["model"] for r in a}!=required: errors.append("prose primary models missing")
 for m in required:
  got=[r for r in a if r["model"]==m]
  if {r["question_id"] for r in got}!=qids: errors.append(f"{m}: incomplete prose question coverage")
  if m not in {r["model"] for r in fit}: errors.append(f"{m}: missing prose fit row")
  raw=INTERNAL/"responses"/f"primary-{m}.jsonl"; ids={json.loads(x).get("question_id") for x in raw.read_text().splitlines() if x} if raw.exists() else set()
  if {r["question_id"] for r in got}-ids: errors.append(f"{m}: missing raw responses")
 if errors: raise AssertionError("; ".join(errors))
 print(f"PASS: prose arm ({len(a)} answers, {len(fit)} fit rows, {len(pre)} prefill rows); exploratory arm separately validated ({len(ea)} answers).")
def validate_code():
 cfg=json.loads((D/"study-config.json").read_text())["arms"]["code"]; models=set(cfg["models"])
 ans=rows(CODE,"answer-results.csv"); fit=rows(CODE,"fit-results.csv"); pref=rows(CODE,"prefill-results.csv")
 if not ans:
  print("PENDING: code arm GPU CSVs are header-only."); return
 qs=[json.loads(x) for x in (CODE/"questions.jsonl").read_text().splitlines() if x]; qids={q["question_id"] for q in qs}; errors=[]
 if {r["model"] for r in ans}!=models: errors.append("code arm requires all three models")
 for m in models:
  got=[r for r in ans if r["model"]==m]
  if {r["question_id"] for r in got}!=qids: errors.append(f"{m}: incomplete code question coverage")
  if m not in {r["model"] for r in fit}: errors.append(f"{m}: missing code fit row")
  raw=INTERNAL/"code"/"responses"/f"primary-{m}.jsonl"; ids={json.loads(x).get("question_id") for x in raw.read_text().splitlines() if x} if raw.exists() else set()
  if {r["question_id"] for r in got}-ids: errors.append(f"{m}: missing code raw responses")
 if errors: raise AssertionError("; ".join(errors))
 print(f"PASS: code arm ({len(ans)} answers, {len(fit)} fit rows, {len(pref)} prefill rows) with raw response coverage.")
def main():
 try:
  validate_prose(); validate_code(); return 0
 except Exception as e:
  print(f"FAIL: {e}"); return 1
if __name__=="__main__": sys.exit(main())
