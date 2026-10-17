#!/usr/bin/env python3
"""Validate frozen 003 inputs, exploratory artifacts, and primary-arm outputs."""
import csv,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent; D=ROOT/"DATA"; INTERNAL=ROOT/"_internal"
COLS={"fit-results.csv":["model","ctx_size","loaded_full_gpu","layers_on_cuda","layers_total","kv_buffer_mib","rs_buffer_mib","peak_vram_mib","error"],"prefill-results.csv":["model","length_label","doc_id","prompt_tokens","prefill_s","prefill_tps","peak_vram_mib"],"answer-results.csv":["model","length_label","doc_id","question_id","task_type","position","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","correct","format_strict_correct","failure_class"]}
FAILS={"","wrong_answer","invalid_json","truncated","error"}

def read_csv(folder,name,expected=None):
    with (folder/name).open(newline="") as f:
        r=csv.DictReader(f); wanted=expected or COLS[name]; assert r.fieldnames==wanted,f"{folder/name}: header mismatch {r.fieldnames}"; return list(r)

def validate_exploratory():
    folder=D/"exploratory-thinking-on"; old_answer_cols=COLS["answer-results.csv"][:11]+["failure_class"]; a=read_csv(folder,"answer-results.csv",old_answer_cols); f=read_csv(folder,"fit-results.csv"); p=read_csv(folder,"prefill-results.csv")
    if not a: raise AssertionError("exploratory arm has no answer rows")
    if {r["model"] for r in a}!={"qwen36_35b_a3b"}: raise AssertionError("exploratory arm should contain only Qwen3.6")
    print(f"PASS: exploratory-thinking-on separately validated ({len(a)} answers, {len(f)} fit rows, {len(p)} prefill rows; raw responses intentionally unavailable).")

def main():
    cfg=json.loads((D/"study-config.json").read_text()); primary={n:read_csv(D,n) for n in COLS}; validate_exploratory()
    ans=primary["answer-results.csv"]
    if not ans:
        print("PENDING: primary arm has no answers yet; results must include all three models and matching raw responses."); return 0
    qpath=D/"questions.jsonl"; questions=[json.loads(l) for l in qpath.read_text().splitlines() if l.strip()]; qids={q["question_id"] for q in questions}; errors=[]
    if len(qids)!=len(questions): errors.append("duplicate question_id in frozen questions")
    need=cfg["questions_per_task_type_per_length_min"]
    for length in cfg["lengths"]:
        for task in cfg["task_types"]:
            count=sum(q["length_label"]==length and q["task_type"]==task for q in questions)
            if count<need: errors.append(f"{length}/{task}: {count} questions < {need}")
    required=set(cfg["models"]); present={r["model"] for r in ans}
    if present!=required: errors.append(f"primary models present {sorted(present)} != required {sorted(required)}")
    fits={r["model"] for r in primary["fit-results.csv"]}; pref={r["model"] for r in primary["prefill-results.csv"]}
    for model in required:
        if model not in fits: errors.append(f"{model}: no fit rows")
        got=[r for r in ans if r["model"]==model]; counts={}
        for row in got: counts[row["question_id"]]=counts.get(row["question_id"],0)+1
        if qids-set(counts): errors.append(f"{model}: {len(qids-set(counts))} questions without answers")
        if any(n>1 for n in counts.values()): errors.append(f"{model}: duplicate question answers")
        for row in got:
            if row["question_id"] not in qids: errors.append(f"{model} {row['question_id']}: unknown question id"); continue
            if row["correct"] not in ("0","1") or row["failure_class"] not in FAILS: errors.append(f"{model} {row['question_id']}: invalid outcome fields")
            if row["format_strict_correct"] not in ("0","1"): errors.append(f"{model} {row['question_id']}: invalid format_strict_correct")
            if (row["correct"]=="1")!=(row["failure_class"]==""): errors.append(f"{model} {row['question_id']}: correct/failure mismatch")
            if row["doc_id"] not in {p["doc_id"] for p in primary["prefill-results.csv"] if p["model"]==model}: errors.append(f"{model} {row['question_id']}: missing prefill row")
        response_path=INTERNAL/"responses"/f"primary-{model}.jsonl"
        responses=set()
        if response_path.exists():
            for line in response_path.read_text().splitlines():
                if line.strip():
                    raw=json.loads(line)
                    if raw.get("model")==model and raw.get("arm")=="primary": responses.add(raw.get("question_id"))
        missing_raw={r["question_id"] for r in got}-responses
        if missing_raw: errors.append(f"{model}: {len(missing_raw)} answer rows lack a raw-response line")
    for model in required:
        for doc in {r["doc_id"] for r in ans if r["model"]==model}:
            subset=[r for r in ans if r["model"]==model and r["doc_id"]==doc]
            if len(subset)>1 and sum(int(r["cached_prompt_tokens"] or 0)>0 for r in subset)<len(subset)-1: errors.append(f"{model} {doc}: prompt cache not reused on follow-up questions")
    if errors: print("FAIL:"); [print("  -",e) for e in errors]; return 1
    print(f"PASS: primary arm has {len(ans)} answers for all three models; every answer has a raw response."); return 0

if __name__=="__main__": sys.exit(main())
