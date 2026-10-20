#!/usr/bin/env python3
"""Validate the completed prose arm and pending/complete code arm."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent; D=ROOT/"DATA"; CODE=D/"code"; INTERNAL=ROOT/"_internal"
COLS={"fit-results.csv":["model","ctx_size","loaded_full_gpu","layers_on_cuda","layers_total","kv_buffer_mib","rs_buffer_mib","peak_vram_mib","error"],"prefill-results.csv":["model","length_label","doc_id","prompt_tokens","prefill_s","prefill_tps","peak_vram_mib"],"answer-results.csv":["model","length_label","doc_id","question_id","task_type","position","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","correct","format_strict_correct","failure_class"]}
FAILS={"","wrong_answer","invalid_json","truncated","error"}
SCRATCH_ANSWER_COLS=["arm","model","question_id","length_label","task_type","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","finish_reason","final_count_correct","listed_items","matched_planted","missed_planted","matched_decoy","ambiguous","extra_items","unmatched","list_count_consistent","failure_class","repetition_loop","followed_format"]
SCRATCH_ITEM_COLS=["arm","model","question_id","item_index","found_number","listed_text","match_class","matched_event_id","in_document"]
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
 cfg=json.loads((D/"study-config.json").read_text()); qs=[json.loads(x) for x in (D/"questions.jsonl").read_text().splitlines() if x]; qids={q["question_id"] for q in qs}; required=set(cfg["models"]); errors=[]; raw_checks=0
 if {r["model"] for r in a}!=required: errors.append("prose primary models missing")
 for m in required:
  got=[r for r in a if r["model"]==m]
  if {r["question_id"] for r in got}!=qids: errors.append(f"{m}: incomplete prose question coverage")
  if m not in {r["model"] for r in fit}: errors.append(f"{m}: missing prose fit row")
  raw=INTERNAL/"responses"/f"primary-{m}.jsonl"
  if raw.exists():
   raw_checks+=1
   ids={json.loads(x).get("question_id") for x in raw.read_text().splitlines() if x}
   if {r["question_id"] for r in got}-ids: errors.append(f"{m}: missing raw responses")
 if errors: raise AssertionError("; ".join(errors))
 raw_note="raw-response coverage verified" if raw_checks else "private raw responses excluded"
 print(f"PASS: prose arm ({len(a)} answers, {len(fit)} fit rows, {len(pre)} prefill rows; {raw_note}); exploratory arm separately validated ({len(ea)} answers).")
def validate_code():
 cfg=json.loads((D/"study-config.json").read_text())["arms"]["code"]; models=set(cfg["models"])
 ans=rows(CODE,"answer-results.csv"); fit=rows(CODE,"fit-results.csv"); pref=rows(CODE,"prefill-results.csv"); raw_checks=0
 if not ans:
  print("PENDING: code arm GPU CSVs are header-only."); return
 qs=[json.loads(x) for x in (CODE/"questions.jsonl").read_text().splitlines() if x]; qids={q["question_id"] for q in qs}; errors=[]
 if {r["model"] for r in ans}!=models: errors.append("code arm requires all three models")
 for m in models:
  got=[r for r in ans if r["model"]==m]
  if {r["question_id"] for r in got}!=qids: errors.append(f"{m}: incomplete code question coverage")
  if m not in {r["model"] for r in fit}: errors.append(f"{m}: missing code fit row")
  raw=INTERNAL/"code"/"responses"/f"primary-{m}.jsonl"
  if raw.exists():
   raw_checks+=1
   ids={json.loads(x).get("question_id") for x in raw.read_text().splitlines() if x}
   if {r["question_id"] for r in got}-ids: errors.append(f"{m}: missing code raw responses")
 if errors: raise AssertionError("; ".join(errors))
 raw_note="raw-response coverage verified" if raw_checks else "private raw responses excluded"
 print(f"PASS: code arm ({len(ans)} answers, {len(fit)} fit rows, {len(pref)} prefill rows; {raw_note}).")
def validate_scratchpad():
 folder=D/"scratchpad"
 ans=rows(folder,"answer-results.csv",SCRATCH_ANSWER_COLS); items=rows(folder,"items.csv",SCRATCH_ITEM_COLS)
 cfg=json.loads((folder/"study-config.json").read_text())
 models=set(cfg["scope"]["models"]); arms=set(cfg["scope"]["arms"]); lengths=set(cfg["scope"]["lengths"])
 if len(ans)!=270: raise AssertionError(f"scratchpad must contain 270 answers, got {len(ans)}")
 if {r["model"] for r in ans}!=models: raise AssertionError("scratchpad model coverage mismatch")
 if {r["arm"] for r in ans}!=arms: raise AssertionError("scratchpad arm coverage mismatch")
 if any(r["task_type"]!="aggregation" for r in ans): raise AssertionError("scratchpad includes a non-aggregation row")
 for m in models:
  for a in arms:
   for l in lengths:
    group=[r for r in ans if (r["model"],r["arm"],r["length_label"])==(m,a,l)]
    if len(group)!=15: raise AssertionError(f"scratchpad cell {m}/{a}/{l}: expected 15 answers, got {len(group)}")
 valid_failures={"truncated","invalid_json","no_list","decoy_included","extra_item","missed_items","miscount_of_list","correct"}
 if any(r["failure_class"] not in valid_failures for r in ans): raise AssertionError("unknown scratchpad failure class")
 if any(r["repetition_loop"] not in {"0","1"} or r["followed_format"] not in {"0","1"} for r in ans): raise AssertionError("scratchpad flags must be binary")
 answer_keys={(r["arm"],r["model"],r["question_id"]) for r in ans}
 if any((r["arm"],r["model"],r["question_id"]) not in answer_keys for r in items): raise AssertionError("scratchpad item row lacks answer row")
 raw_dir=INTERNAL/"scratchpad"/"responses"; raw_keys=set(); raw_files=list(raw_dir.glob("*.jsonl")) if raw_dir.exists() else []
 for path in raw_files:
  if path.name.startswith("preflight-"): continue
  for line in path.read_text().splitlines():
   if line.strip():
    r=json.loads(line); raw_keys.add((r.get("arm"),r.get("model"),r.get("question_id")))
 if raw_files and raw_keys!=answer_keys: raise AssertionError(f"scratchpad raw-response coverage mismatch ({len(raw_keys)} raw keys, {len(answer_keys)} answer rows)")
 if cfg.get("max_generated_tokens")!=1024 or not cfg.get("prompt_suffix"): raise AssertionError("scratchpad prompt/cap missing from config")
 if cfg.get("budget_gpu_hours",{}).get("actual_gpu_hours")!=1.421 or cfg.get("budget_gpu_hours",{}).get("estimated_cost_usd")!=0.71: raise AssertionError("scratchpad actual GPU time/cost missing")
 if not (folder/"SCHEMA.md").is_file(): raise AssertionError("scratchpad SCHEMA.md missing")
 charts=[ROOT/"CHARTS"/f"scratchpad-{n}.png" for n in ("final-count-baseline","failure-classes","planted-recall")]
 for chart in charts:
  if not chart.is_file() or chart.read_bytes()[:8]!=b"\x89PNG\r\n\x1a\n": raise AssertionError(f"scratchpad chart missing or invalid: {chart.name}")
 raw_note="raw-response coverage" if raw_files else "public metadata (raw responses excluded)"
 print(f"PASS: scratchpad ({len(ans)} answers, {len(items)} extracted items, 3 charts, {raw_note}).")
def main():
 try:
  validate_prose(); validate_code(); validate_scratchpad(); return 0
 except Exception as e:
  print(f"FAIL: {e}"); return 1
if __name__=="__main__": sys.exit(main())
