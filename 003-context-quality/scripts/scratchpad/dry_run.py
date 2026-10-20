#!/usr/bin/env python3
"""CPU-only fake-response scorer dry run; writes all generated artifacts privately."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"scratchpad"))
import score

def main():
    q=next(json.loads(x) for x in (ROOT/"DATA/questions.jsonl").read_text().splitlines() if '"task_type": "aggregation"' in x)
    events=score.load_events("prose"); targets,decoys=score.events_for("prose",q,events)
    doc=(ROOT/"DATA/documents"/f"{q['doc_id']}.txt").read_text()
    lines=[e["text"] for e in targets]; decoy=next(e["text"] for e in decoys)
    cases={"perfect":("\n".join(f"found {i}: {s}" for i,s in enumerate(lines,1))+f'\n{{"count": {q["reference"]["count"]}}}',"stop"),
           "missed":("\n".join(f"found {i}: {s}" for i,s in enumerate(lines[1:],1))+f'\n{{"count": {q["reference"]["count"]}}}',"stop"),
           "decoy":("\n".join(f"found {i}: {s}" for i,s in enumerate(lines+[decoy],1))+f'\n{{"count": {q["reference"]["count"]}}}',"stop"),
           "miscount":("\n".join(f"found {i}: {s}" for i,s in enumerate(lines,1))+f'\n{{"count": {q["reference"]["count"]+1}}}',"stop")}
    rows=[]; private=ROOT/"_internal"/"scratchpad"; private.mkdir(parents=True,exist_ok=True)
    fake_dir=private/"dry-run-input"; fake_dir.mkdir(parents=True,exist_ok=True)
    fake=fake_dir/"fake-responses.jsonl"
    with fake.open("w") as f:
        for name,(content,finish) in cases.items():
            r={"question_id":q["question_id"],"arm":"prose","model":"fake","content":content,"finish_reason":finish,"usage":{"completion_tokens":32}}
            f.write(json.dumps(r)+"\n")
            row,_,_,_=score.score_one("prose","fake",q,content,finish,doc,events); rows.append((name,row["failure_class"]))
    expected={"perfect":"correct","missed":"missed_items","decoy":"decoy_included","miscount":"miscount_of_list"}
    assert dict(rows)==expected,(rows,expected)
    dry_out=private/"dry-run-output"
    scored,_=score.run(fake_dir,dry_out)
    # Only this isolated directory is scanned; progress/raw-response JSONL is ignored.
    assert len(scored)==4, f"expected four scored fake records, got {len(scored)}"
    reread={}
    import csv
    with (dry_out/"answer-results.csv").open() as f:
        reread={r["failure_class"] for r in csv.DictReader(f)}
    assert reread==set(expected.values()),reread
    report={"fake_responses":str(fake.relative_to(ROOT)),"expected_failure_classes":expected,"observed":dict(rows),"status":"PASS"}
    (private/"dry-run-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("DRY RUN PASS: fake response classes " + ", ".join(f"{k}={v}" for k,v in rows))
    print("Private fixtures/report: _internal/scratchpad/dry-run-input/, dry-run-report.json")
if __name__=="__main__": main()
