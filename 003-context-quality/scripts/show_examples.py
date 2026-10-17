#!/usr/bin/env python3
"""Print two long_64k examples per task with exact facts and local prose context."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/"DATA"
def context(text,needle):
    # Preserve exact inserted wording while showing adjacent sentences.
    spans=list(re.finditer(r"[^.!?]+[.!?](?:\s+|$)",text,re.S)); idx=next((i for i,m in enumerate(spans) if needle in m.group()),None)
    if idx is None: return needle
    return " ".join(m.group().strip() for m in spans[max(0,idx-1):min(len(spans),idx+2)])
def main():
    doc=(D/"documents/long_64k.txt").read_text(); insert=json.loads((D/"documents/long_64k-insertions.json").read_text())["insertions"]
    qs=[json.loads(x) for x in (D/"questions.jsonl").read_text().splitlines() if x and json.loads(x)["doc_id"]=="long_64k"]
    for task in ("single_retrieval","multi_retrieval","aggregation","multi_hop"):
        print(f"\n## {task}")
        for q in [x for x in qs if x["task_type"]==task][:2]:
            print(f"\n### {q['question_id']} — {q['prompt']}")
            keys={x.casefold() for x in q["entity_key"]}
            targets=[x for x in insert if x["key"].casefold() in keys and ((task=="single_retrieval" and x["role"]=="single_target") or (task=="multi_retrieval" and x["role"]=="multi_target") or (task=="aggregation" and x["role"]=="aggregation_target") or (task=="multi_hop" and x["role"].startswith("hop")))]
            show=[]
            for fact in targets:
                show.append(fact)
                if fact["role"] in ("single_target","multi_target"):
                    distrole="single_distractor" if task=="single_retrieval" else "multi_distractor"
                    distractors=[x for x in insert if x["role"]==distrole]
                    if distractors: show.append(min(distractors,key=lambda x:abs(x["fraction"]-fact["fraction"])))
                elif fact["role"]=="aggregation_target":
                    distractors=[x for x in insert if x["role"]=="aggregation_distractor" and abs(x["fraction"]-fact["fraction"])<.04]
                    if distractors: show.append(distractors[0])
            seen=set()
            for f in sorted(show,key=lambda x:x["char_offset"]):
                if f["ordinal"] in seen: continue
                seen.add(f["ordinal"]); print(f"- planted: {f['text']}")
                print(f"  context: {context(doc,f['text'])}")
if __name__=="__main__":main()
