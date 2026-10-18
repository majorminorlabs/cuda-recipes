#!/usr/bin/env python3
"""Rebuild primary answer-results.csv offline from captured JSONL responses."""
import argparse,csv,json
from pathlib import Path
from score import content_equal,equal,parse

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/"DATA"/"code"; INTERNAL=ROOT/"_internal"/"code"
COLS=["model","length_label","doc_id","question_id","task_type","position","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","correct","format_strict_correct","failure_class"]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--arm",default="primary"); ap.add_argument("--model",required=True); ap.add_argument("--output",type=Path,default=DATA/"answer-results.csv"); args=ap.parse_args()
    qmap={q["question_id"]:q for q in (json.loads(x) for x in (DATA/"questions.jsonl").read_text().splitlines() if x.strip())}
    path=INTERNAL/"responses"/f"{args.arm}-{args.model}.jsonl"
    if not path.exists(): raise SystemExit(f"missing response file: {path}")
    rows=[]
    for line in path.read_text().splitlines():
        response=json.loads(line); q=qmap[response["question_id"]]; obj=parse(response.get("content","")); strict=equal(obj,q["reference"],q["task_type"]); correct=content_equal(obj,q["reference"],q["task_type"])
        usage=response.get("usage") or {}; details=usage.get("prompt_tokens_details") or {}; finish=response.get("finish_reason")
        failure="" if correct else ("truncated" if finish=="length" else ("invalid_json" if obj is None else "wrong_answer"))
        rows.append({"model":args.model,"length_label":q["length_label"],"doc_id":q["doc_id"],"question_id":q["question_id"],"task_type":q["task_type"],"position":q["position"],"prompt_tokens":usage.get("prompt_tokens",0),"cached_prompt_tokens":details.get("cached_tokens",usage.get("cached_tokens",0)),"generated_tokens":usage.get("completion_tokens",0),"answer_s":response.get("answer_s",0),"correct":int(correct),"format_strict_correct":int(strict),"failure_class":failure})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    existing=[]
    if args.output.exists():
        with args.output.open(newline="") as f: existing=[r for r in csv.DictReader(f) if r.get("model")!=args.model]
    with args.output.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); w.writerows(existing); w.writerows(rows)
    print(f"Scored {len(rows)} responses from {path} -> {args.output}")

if __name__=="__main__": main()
