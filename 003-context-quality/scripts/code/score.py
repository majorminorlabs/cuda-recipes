#!/usr/bin/env python3
"""Deterministic JSON scoring and frozen-dataset self-tests."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"DATA"/"code"
TOKEN=re.compile(r"[a-z0-9]+",re.I)
def norm(x):
    if isinstance(x,dict): return {str(k).strip().casefold():norm(v) for k,v in x.items()}
    if isinstance(x,list): return [norm(v) for v in x]
    if isinstance(x,str): return re.sub(r"\s+"," ",x).strip().casefold()
    return x
def parse(value):
    if isinstance(value,dict): return value
    if not isinstance(value,str): return None
    text=value.strip()
    decoder=json.JSONDecoder()
    # Prefer a whole response or an explicit code fence.
    try:
        out=json.loads(text)
        if isinstance(out,dict): return out
    except (ValueError,TypeError): pass
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```",text,re.I):
        try:
            out=json.loads(match.group(1).strip())
            if isinstance(out,dict): return out
        except (ValueError,TypeError): pass
    # Recover the last complete top-level object, ignoring braces in strings.
    found=[]; i=0
    while i<len(text):
        if text[i]!="{": i+=1; continue
        try: out,end=decoder.raw_decode(text[i:])
        except (ValueError,TypeError): i+=1; continue
        if isinstance(out,dict): found.append(out); i+=end
        else: i+=1
    return found[-1] if found else None
def equal(actual,expected,task):
    if not isinstance(actual,dict) or not isinstance(expected,dict): return False
    a,e=norm(actual),norm(expected)
    if task=="multi_retrieval":
        if set(a)!=set(e): return False
        return all(sorted(map(str,a[k]))==sorted(map(str,e[k])) if isinstance(a[k],list) and isinstance(e[k],list) else a[k]==e[k] for k in e)
    return a==e
def multi_retrieval_values(actual):
    """Return normalized answer strings from the prompt's ambiguous answers list."""
    if not isinstance(actual,dict) or not isinstance(actual.get("answers"),list): return None
    values=[]
    entity_keys={"entity","entity_name","name","shoal"}
    for item in actual["answers"]:
        if isinstance(item,str): values.append(item.strip().casefold())
        elif isinstance(item,dict):
            values.extend(v.strip().casefold() for k,v in item.items()
                          if isinstance(v,str) and str(k).strip().casefold() not in entity_keys)
    return values
def content_equal(actual,expected,task):
    if task!="multi_retrieval": return equal(actual,expected,task)
    vals=multi_retrieval_values(actual)
    ref=expected.get("answers") if isinstance(expected,dict) else None
    if vals is None or not isinstance(ref,list): return False
    return set(vals)=={str(v).strip().casefold() for v in ref}
def answer_values(q):
    ref=q["reference"]
    if q["task_type"]=="multi_retrieval": return [str(x) for x in ref["answers"]]
    return [str(v) for v in ref.values()]
def guessability(q):
    question=q["prompt"].casefold(); entities=q["entity_key"]
    et=set(t.casefold() for e in entities for t in TOKEN.findall(e))
    ed=set(d for e in entities for d in re.findall(r"\d+",e))
    checks=[]
    for ans in answer_values(q):
        at={t.casefold() for t in TOKEN.findall(ans)}; ad=set(re.findall(r"\d+",ans))
        absent=ans.casefold() not in question
        disjoint=not (at & et) and not (ad & ed)
        checks.append(absent and disjoint)
    return bool(checks) and all(checks),len(checks),sum(checks)
def self_test(questions):
    docs={q["doc_id"]:(DATA/"documents"/f"{q['doc_id']}.txt").read_text(encoding="utf-8").casefold() for q in questions}
    guess_checks=guess_pass=guess_q_pass=guess_q_fail=0
    for q in questions:
        assert equal(q["reference"],q["reference"],q["task_type"]),q["question_id"]
        assert not equal(q["negative_control"],q["reference"],q["task_type"]),q["question_id"]
        assert equal(parse(json.dumps(q["reference"])),q["reference"],q["task_type"]),q["question_id"]
        doc=docs[q["doc_id"]]; ref=q["reference"]
        if q["task_type"]=="single_retrieval": assert ref["value"].casefold() in doc,q["question_id"]
        elif q["task_type"]=="multi_retrieval": assert all(v.casefold() in doc for v in ref["answers"]),q["question_id"]
        elif q["task_type"]=="aggregation": assert doc.count(q["entity_key"][0].casefold()+"()")-1==ref["count"],q["question_id"]
        elif q["task_type"]=="multi_hop":
            assert all(e.casefold() in doc for e in q["entity_key"]),q["question_id"]
            assert ref["value"].casefold() in doc,q["question_id"]
        ok,n,p=guessability(q); guess_checks+=n; guess_pass+=p
        if ok: guess_q_pass+=1
        else: guess_q_fail+=1
    print(f"PASS: reference and negative-control self-test passed for {len(questions)} questions")
    print(f"GUESSABILITY: {guess_q_pass}/{len(questions)} questions pass, {guess_q_fail} fail; {guess_pass}/{guess_checks} reference-answer checks pass")
    if guess_q_fail: raise AssertionError("guessability check failed")
    return len(questions)
def main():
    qs=[json.loads(x) for x in (DATA/"questions.jsonl").read_text().splitlines() if x.strip()]
    self_test(qs)
    if len(sys.argv)>1:
        q=next(x for x in qs if x["question_id"]==sys.argv[1]); print("correct" if equal(parse(sys.argv[2]),q["reference"],q["task_type"]) else "incorrect")
if __name__=="__main__": main()
