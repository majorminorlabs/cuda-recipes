#!/usr/bin/env python3
"""Offline scorer for the aggregation scratchpad addendum; existing 003 scoring is untouched."""
import argparse, csv, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "DATA"
INTERNAL = ROOT / "_internal" / "scratchpad"
ANSWER_FIELDS = ["arm","model","question_id","length_label","task_type","prompt_tokens","cached_prompt_tokens","generated_tokens","answer_s","finish_reason","final_count_correct","listed_items","matched_planted","missed_planted","matched_decoy","ambiguous","extra_items","unmatched","list_count_consistent","failure_class","repetition_loop","followed_format"]
ITEM_FIELDS = ["arm","model","question_id","item_index","found_number","listed_text","match_class","matched_event_id","in_document"]
FOUND = re.compile(r"^\s*(?:(?:[-+>]\s*|\*\*\s*|__\s*|\*\s*|\d+[.)]\s*|[`'\"]\s*)*)(?:\*\*|__)?found\s+(\d+|N)\s*:\s*(?:(?:\*\*|__)\s*)?(.*?)\s*(?:(?:\*\*|__)\s*)?$", re.I | re.M)

def normalize(s):
    return re.sub(r"\s+", " ", str(s)).strip().casefold()

def normalize_compact(s):
    """Canonical form for searching extracted text across indentation/newline changes."""
    return re.sub(r"\s+", "", str(s)).casefold()

def is_in_document(line, document, document_events=()):
    needle=normalize_compact(line)
    compact_doc=normalize_compact(document)
    if needle and needle in compact_doc: return True
    # Models sometimes append commentary or concatenate adjacent facts to a
    # copied source line. Count it as document text only when a recorded source
    # candidate occurs both in that answer line and in the raw document.
    line_norm=normalize(line)
    for event in document_events:
        for candidate in event_candidates(event):
            c=normalize(candidate)
            if c and c in line_norm and c in normalize(document): return True
    return False

def parse(value):
    """003's lenient extraction: bare object, fenced object, or last top-level object."""
    if isinstance(value, dict): return value
    if not isinstance(value, str): return None
    text = value.strip(); dec = json.JSONDecoder()
    try:
        x = json.loads(text)
        if isinstance(x, dict): return x
    except (ValueError, TypeError): pass
    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, re.I):
        try:
            x = json.loads(m.group(1).strip())
            if isinstance(x, dict): return x
        except (ValueError, TypeError): pass
    found=[]; i=0
    while i < len(text):
        if text[i] != "{": i += 1; continue
        try: x,end=dec.raw_decode(text[i:])
        except (ValueError, TypeError): i += 1; continue
        if isinstance(x,dict): found.append((x,i,i+end)); i += end
        else: i += 1
    return found[-1][0] if found else None

def events_for(arm, q, events):
    doc=q["doc_id"]
    if arm == "prose":
        key=q["entity_key"][0].casefold()
        relevant=[e for e in events if e.get("doc_id",doc)==doc and str(e.get("role","")).startswith("aggregation_")]
        targets=[e for e in relevant if e.get("role")=="aggregation_target" and str(e.get("key","")).casefold()==key]
        decoys=[e for e in relevant if e.get("role")=="aggregation_distractor"]
    else:
        relevant=[e for e in events if e.get("question_id")==q["question_id"]]
        targets=[e for e in relevant if e.get("role")=="aggregation_call"]
        decoys=[e for e in relevant if e.get("role") in {"aggregation_decoy_call","aggregation_definition","aggregation_decoy_definition"}]
    return targets,decoys

def event_candidates(e):
    raw=e.get("text") or e.get("source_snippet") or ""
    key=str(e.get("key", ""))
    lines=[x.strip() for x in raw.splitlines() if x.strip()]
    # Keep exact inserted prose sentences and source lines that contain the named key.
    if e.get("text"): return [raw.strip()]
    return [line for line in lines if key.casefold().replace("_near", "") in line.casefold()]

def clean_listed_line(value):
    return value.strip().strip("`'\"“”‘’* ")

def extract_listed(tally, targets, decoys):
    """Read explicit found labels, code continuations, or exact source quotes.

    Some responses put only the first line of a code snippet after ``found N:``
    and indent the actual call on the next line. Others quote exact document
    lines without any label. Recover those source lines, but do not infer a list
    from generic prose or from a final JSON count alone.
    """
    matches=list(FOUND.finditer(tally))
    if matches:
        listed=[]
        lines=tally.splitlines(keepends=True)
        offsets=[]; p=0
        for line in lines:
            offsets.append((p,p+len(line),line)); p+=len(line)
        for i,m in enumerate(matches):
            body=clean_listed_line(m.group(2))
            # Include adjacent code lines that continue the quoted snippet.
            line_end=tally.find("\n",m.end())
            if line_end < 0: line_end=len(tally)
            continuation=[]
            cursor=line_end+1
            next_marker=matches[i+1].start() if i+1<len(matches) else len(tally)
            for raw in tally[cursor:next_marker].splitlines():
                stripped=raw.strip()
                if not stripped: break
                if raw[:1].isspace() or re.match(r"^(?:def |return |from |import |@|class |pass\b)",stripped):
                    continuation.append(raw)
                else: break
            if continuation: body=(body+"\n"+"\n".join(continuation)).strip()
            number=m.group(1)
            listed.append((int(number) if number.isdigit() else len(listed)+1,clean_listed_line(body)))
        return listed, True

    # Label-free tallies are accepted only when they contain source text from
    # this question's recorded planted/decoy lines. This handles bare quoted
    # prose lines and numbered/code-block explanations without treating generic
    # reasoning as a tally.
    normalized=normalize(tally)
    candidates={}
    for event in [*targets,*decoys]:
        for candidate in event_candidates(event):
            c=normalize(candidate)
            if c: candidates.setdefault(c,candidate.strip())
    hits=[]
    for c,original in candidates.items():
        start=0
        while True:
            pos=normalized.find(c,start)
            if pos<0: break
            hits.append((pos,-len(c),c,original)); start=pos+len(c)
    hits.sort()
    selected=[]; end=-1
    for pos,neglen,c,original in hits:
        if pos < end: continue
        selected.append((pos,original)); end=pos-neglen
    selected.sort()
    return [(i,clean_listed_line(line)) for i,(_,line) in enumerate(selected,1)], False

def find_matches(listed, pool):
    """Return all remaining planted candidates matched under the conservative quote rule."""
    n=normalize(listed)
    candidates=[]
    for index,e in enumerate(pool):
        for candidate in event_candidates(e):
            c=normalize(candidate)
            # A copied line may include surrounding document text, but must contain the full planted line.
            if c and c in n:
                candidates.append(index); break
    if candidates: return candidates
    for index,e in enumerate(pool):
        key=normalize(str(e.get("key", "")).replace("_near", ""))
        for candidate in event_candidates(e):
            c=normalize(candidate)
            if not n or not c or n not in c or len(n)/len(c) < .8: continue
            remainder=n.replace(key,"",1).strip() if key else n
            if re.search(r"[a-z0-9]",remainder): candidates.append(index); break
    return candidates

def score_one(arm,model,q,content,finish_reason,doc_text,events):
    targets,decoys=events_for(arm,q,events)
    parsed=parse(content)
    # Limit tally parsing to text before the final JSON object, preventing JSON text from looking like a tally.
    text=content if isinstance(content,str) else ""
    obj_start=text.rfind("{") if parsed is not None else len(text)
    # Find the final object start safely, including nested objects and braces in strings.
    if parsed is not None:
        dec=json.JSONDecoder(); candidates=[]; i=0
        while i<len(text):
            if text[i]!="{": i+=1; continue
            try: obj,end=dec.raw_decode(text[i:])
            except (ValueError,TypeError): i+=1; continue
            if isinstance(obj,dict): candidates.append(i); i+=end
            else: i+=1
        if candidates: obj_start=candidates[-1]
    tally=text[:obj_start]
    listed,followed_format=extract_listed(tally,targets,decoys)
    used_t=set(); used_d=set(); item_rows=[]; unmatched=[]; review=[]; matched_t=matched_d=ambiguous=extra=0
    norm_doc=normalize(doc_text)
    for idx,(number,line) in enumerate(listed,1):
        avail_t=[j for j in range(len(targets)) if j not in used_t]
        avail_d=[j for j in range(len(decoys)) if j not in used_d]
        target_matches=find_matches(line,[targets[j] for j in avail_t])
        decoy_matches=find_matches(line,[decoys[j] for j in avail_d])
        all_matches=[("target",avail_t[j]) for j in target_matches]+[("decoy",avail_d[j]) for j in decoy_matches]
        ev=None
        # Identical inserted lines are separate occurrences. Consume them one at a
        # time; ambiguity only exists when a quote could refer to different text.
        matched_texts=set()
        for typ,orig in all_matches:
            pool=targets if typ=="target" else decoys
            candidates=event_candidates(pool[orig])
            matched_texts.add(normalize(candidates[0] if candidates else ""))
        if len(matched_texts)>1:
            cls="ambiguous"; ambiguous+=1; extra+=1
        elif all_matches and any(x[0]=="target" for x in all_matches):
            _,orig=next(x for x in all_matches if x[0]=="target"); used_t.add(orig); matched_t+=1; cls="planted"; ev=targets[orig]
        elif all_matches:
            _,orig=all_matches[0]; used_d.add(orig); matched_d+=1; cls="decoy"; ev=decoys[orig]
        else: cls="other"
        in_doc=is_in_document(line,doc_text,[e for e in events if e.get("doc_id",q.get("doc_id"))==q.get("doc_id")])
        if cls in {"other","ambiguous"}: review.append({"line":line,"in_document":bool(in_doc),"match_class":cls})
        if cls=="other" and in_doc: cls="extra_item"; extra+=1
        elif cls=="other" and not in_doc: cls="unmatched"; unmatched.append(line)
        item_rows.append({"arm":arm,"model":model,"question_id":q["question_id"],"item_index":idx,"found_number":number,"listed_text":line,"match_class":cls,"matched_event_id":(ev or {}).get("event_id",""),"in_document":int(in_doc)})
    missed=max(0,len(targets)-matched_t)
    count=parsed.get("count") if isinstance(parsed,dict) else None
    ref=q.get("reference",{}).get("count")
    final_correct=isinstance(parsed,dict) and normalize(json.dumps(parsed,sort_keys=True))==normalize(json.dumps(q.get("reference"),sort_keys=True))
    consistent=count==len(listed) if isinstance(count,int) else False
    if finish_reason=="length": failure="truncated"
    elif parsed is None: failure="invalid_json"
    elif not listed: failure="no_list"
    elif matched_d: failure="decoy_included"
    elif extra: failure="extra_item"
    elif missed: failure="missed_items"
    elif not final_correct or not consistent: failure="miscount_of_list"
    else: failure="correct"
    target_line_counts=Counter(normalize(candidate) for event in targets for candidate in event_candidates(event))
    listed_line_counts=Counter(normalize(line) for _,line in listed)
    repeats=any(listed_line_counts[line]-target_line_counts[line]>=2 for line in listed_line_counts)
    row={"arm":arm,"model":model,"question_id":q["question_id"],"length_label":q["length_label"],"task_type":"aggregation","final_count_correct":int(final_correct),"listed_items":len(listed),"matched_planted":matched_t,"missed_planted":missed,"matched_decoy":matched_d,"ambiguous":ambiguous,"extra_items":extra,"unmatched":len(unmatched),"list_count_consistent":int(consistent),"failure_class":failure,"repetition_loop":int(repeats),"followed_format":int(followed_format)}
    return row,item_rows,unmatched,review

def load_events(arm):
    if arm=="prose":
        out=[]
        for p in sorted((DATA/"documents").glob("*-insertions.json")):
            d=json.loads(p.read_text()); out.extend({**x,"doc_id":d.get("doc_id",p.stem.replace("-insertions",""))} for x in d["insertions"])
        return out
    return json.loads((ROOT/"_internal"/"code"/"planting-map.json").read_text())["facts"]

def run(responses, out_dir, doc_roots=None):
    questions={}
    for arm,path in [("prose",DATA/"questions.jsonl"),("code",DATA/"code"/"questions.jsonl")]:
        for line in path.read_text().splitlines():
            if line.strip():
                q=json.loads(line)
                if q["task_type"]=="aggregation": questions[(arm,q["question_id"])]=q
    maps={arm:load_events(arm) for arm in ("prose","code")}
    answer_rows=[]; item_rows=[]; unmatched_rows=[]; review_rows=[]
    for path in sorted(Path(responses).glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip(): continue
            r=json.loads(line)
            if "preflight_pass" in r: continue
            arm=r["arm"]; q=questions[(arm,r["question_id"])]
            if doc_roots and arm in doc_roots: doc_path=Path(doc_roots[arm])/f"{q['doc_id']}.txt"
            else: doc_path=DATA/("code/documents" if arm=="code" else "documents")/f"{q['doc_id']}.txt"
            row,items,unmatched,review=score_one(arm,r["model"],q,r.get("content",""),r.get("finish_reason"),doc_path.read_text(errors="replace"),maps[arm])
            usage=r.get("usage",{}) or {}; details=usage.get("prompt_tokens_details",{}) or {}
            row.update({"prompt_tokens":usage.get("prompt_tokens",0),"cached_prompt_tokens":details.get("cached_tokens",usage.get("cached_tokens",0)) or 0,"generated_tokens":usage.get("completion_tokens",0),"answer_s":r.get("answer_s",""),"finish_reason":r.get("finish_reason","")})
            answer_rows.append(row); item_rows.extend(items)
            unmatched_rows.extend({"arm":arm,"model":r["model"],"question_id":q["question_id"],"line":x} for x in unmatched)
            review_rows.extend({"arm":arm,"model":r["model"],"question_id":q["question_id"],**x} for x in review)
    out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    for name,fields,rows in [("answer-results.csv",ANSWER_FIELDS,answer_rows),("items.csv",ITEM_FIELDS,item_rows)]:
        with (out_dir/name).open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    INTERNAL.mkdir(parents=True,exist_ok=True)
    (INTERNAL/"unmatched-lines.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in review_rows))
    print(f"Scored {len(answer_rows)} responses; emitted {len(item_rows)} listed items; unmatched lines: {len(unmatched_rows)}")
    return answer_rows,item_rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--responses",default=str(INTERNAL/"responses")); ap.add_argument("--out",default=str(DATA/"scratchpad")); args=ap.parse_args()
    run(args.responses,args.out)
if __name__=="__main__": main()
