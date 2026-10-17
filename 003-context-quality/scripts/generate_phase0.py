#!/usr/bin/env python3
"""Regenerate frozen Phase 0 documents and questions from study-config.json."""
import hashlib, json, random, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; D=ROOT/"DATA"; DOCS=D/"documents"; INTERNAL=ROOT/"_internal"
sys.path.insert(0,str(ROOT/"_internal/venv/lib/python3.13/site-packages"))
from tokenizers import Tokenizer

CFG=json.loads((D/"study-config.json").read_text()); RNG=random.Random(390003)
TOK={m:Tokenizer.from_file(str(INTERNAL/"tokenizers"/m/"tokenizer.json")) for m in CFG["models"]}
SYL=["bela","cavo","dorin","fela","goran","havi","juno","kesta","lumo","maren","navi","orla","pavo","queni","ravo","sela","tovin","ulma","vesta","wero","xali","yorin","zema"]
USED=set()
def name():
    while True:
        x=" ".join(RNG.sample(SYL,2)).title()
        if x.casefold() not in USED: USED.add(x.casefold()); return x
def code(entity):
    parts=set(re.findall(r"[a-z0-9]+",entity.casefold()))
    while True:
        s="".join(RNG.choice("abcdefghjkmnpqrstuvwxyz") for _ in range(15))
        if not any(p in s or s in p for p in parts): return s
def sha(b): return hashlib.sha256(b).hexdigest()
def tokens(text): return {m:len(t.encode(text).ids) for m,t in TOK.items()}
def body_source():
    raw=(INTERNAL/"moby-dick.txt").read_text(encoding="utf-8")
    start=raw.find("*** START OF THE PROJECT GUTENBERG EBOOK")
    if start<0: start=raw.find("*** START OF THIS PROJECT GUTENBERG EBOOK")
    end=raw.find("*** END OF THE PROJECT GUTENBERG EBOOK")
    if end<0: end=raw.find("*** END OF THIS PROJECT GUTENBERG EBOOK")
    raw=raw[raw.find("\n",start)+1:end]
    # Gutenberg includes a contents entry and front matter before the narrative.
    # The second CHAPTER 1 occurrence is the actual opening chapter.
    starts=[m.start() for m in re.finditer(r"(?m)^CHAPTER 1\. Loomings\.?\s*$",raw)]
    if len(starts)<2: raise RuntimeError("could not locate narrative opening after front matter")
    raw=raw[starts[1]:]
    paras=[re.sub(r"\s+"," ",p).strip() for p in re.split(r"\n\s*\n",raw) if p.strip()]
    return paras

def make_items(doc_id):
    questions=[]; inserts=[]; phrases=[]; serial=0
    def add(frac, sentence, role, key):
        nonlocal serial
        serial+=1
        # Map all generated positions to a 5–95% spread, with single retrieval
        # targets deliberately balanced across the requested three bands.
        if role.startswith("single_"):
            band=min(2,int(frac*3)); within=(frac*3)%1
            frac=[.05,.35,.70][band]+within*[.25,.30,.25][band]
        else: frac=.05+.90*frac
        inserts.append({"fraction":frac,"ordinal":serial,"text":sentence,"role":role,"key":key})
    # Single retrieval: each target and same-type near miss has an unrelated answer.
    inlets=[name() for _ in range(15)]; vals=[code(e) for e in inlets]
    for i,(e,v) in enumerate(zip(inlets,vals)):
        f=(i+.5)/15
        add(f,f"The harbor pilot said that {e} was known for the quiet call {v}.","single_target",e)
        de=name(); dv=code(de)
        add(f+.002,f"Sailors approaching {de} listened for the quiet call {dv}.","single_distractor",de)
        pos=["early","middle","late"][i//5]
        questions.append({"question_id":f"{doc_id}-sr-{i+1:02}","doc_id":doc_id,"length_label":doc_id,"task_type":"single_retrieval","position":pos,"prompt":f'Return JSON {{"answer":"..."}}. What quiet call is associated with inlet {e}?',"reference":{"answer":v},"negative_control":{"answer":code(e)},"entity_key":[e]})
    # Multi retrieval uses exact shoal names plus same-type decoys.
    shoals=[name() for _ in range(15)]; shoalvals=[code(e) for e in shoals]
    for i,(e,v) in enumerate(zip(shoals,shoalvals)):
        f=(i+.25)/15
        add(f,f"The lookout remembered {e} by the tide phrase {v}.","multi_target",e)
        de=name(); dv=code(de)
        add(f+.004,f"Another watch kept {de} in mind for the tide phrase {dv}.","multi_distractor",de)
    for i in range(15):
        ix=[(i*3+j*4)%15 for j in range(4)]; ents=[shoals[j] for j in ix]
        questions.append({"question_id":f"{doc_id}-mr-{i+1:02}","doc_id":doc_id,"length_label":doc_id,"task_type":"multi_retrieval","position":"spread","prompt":"Return JSON {\"answers\":[...]}. Give the tide phrase for each shoal: "+", ".join(ents)+".","reference":{"answers":[shoalvals[j] for j in ix]},"negative_control":{"answers":[code(e) for e in ents]},"entity_key":ents})
    # Aggregation: target counts cycle 2..8, while unrelated markers occur 1..3 times.
    markers=[name() for _ in range(15)]; counts=[2+(i%7) for i in range(15)]
    count_phrases=["while the ship's stores were being tallied","as the crew checked the remaining provisions","before the next watch took its place","during the morning inventory of the hold","while the deckhands prepared the cargo list","as the purser checked the barrels","before the vessel left the harbor","during an evening count of the supplies"]
    distractor_phrases=["during the same voyage","as the deck crew changed watches","while the ship crossed open water"]
    for i,(e,n) in enumerate(zip(markers,counts)):
        for k in range(n): add((i+(k+.5)/n)/15,f"The purser mentioned {e} {count_phrases[k]}.","aggregation_target",e)
        dec=name()
        for k in range(1+i%3): add((i+.12+k*.015)/15,f"A passing sailor also spoke of {dec} {distractor_phrases[k]}.","aggregation_distractor",dec)
        questions.append({"question_id":f"{doc_id}-ag-{i+1:02}","doc_id":doc_id,"length_label":doc_id,"task_type":"aggregation","position":"spread","prompt":f'Return JSON {{"count":N}}. How many times is {e} mentioned in the shipboard account?',"reference":{"count":n},"negative_control":{"count":n+1 if n<8 else n-1},"entity_key":[e]})
    # Three-link chains: three distinct randomized names; hops occupy distant regions.
    for i in range(15):
        person, berth, cove=name(),name(),name(); seal=code(cove)
        add(.10+(i%5)*.012,f"The boatswain {person} was assigned to berth {berth} before dawn.","hop1",person)
        add(.48+(i%5)*.012,f"Berth {berth} opened onto cove {cove} when the tide turned.","hop2",berth)
        add(.88+(i%5)*.012,f"At cove {cove}, the crew used the signal {seal} to find the lantern boat.","hop3",cove)
        questions.append({"question_id":f"{doc_id}-mh-{i+1:02}","doc_id":doc_id,"length_label":doc_id,"task_type":"multi_hop","position":"spread","prompt":f'Return JSON {{"signal":"..."}}. Which signal was used at the cove assigned through boatswain {person}?',"reference":{"signal":seal},"negative_control":{"signal":code(cove)},"entity_key":[person,berth,cove]})
    inserts=sorted(inserts,key=lambda x:x["fraction"])
    # Stratify the complete insertion set over the document so deciles remain
    # balanced even though task types contribute different numbers of facts.
    for i,item in enumerate(inserts): item["fraction"]=.05+.90*(i+.5)/len(inserts)
    return questions, inserts

def main():
    source=body_source(); source_hash=sha((INTERNAL/"moby-dick.txt").read_bytes()); docs=[]; allq=[]
    targets={"control":8192,"long_64k":65536,"long_128k":126000}
    for doc_id,target in targets.items():
        qs,ins=make_items(doc_id); allq.extend(qs)
        # Find the largest narrative prefix whose full prose + interleaved facts meets target
        # while leaving the required >=2,048-token context reserve at 128K.
        lo,hi=1,len(source); best=""; best_ins=[]; best_counts={}
        while lo<=hi:
            n=(lo+hi)//2; selected=source[:n]; base="\n\n".join(selected)
            # Candidate sentence boundaries are restricted to narrative prose,
            # away from chapter headings/title lines.
            boundaries=[]
            headings=[m.start() for m in re.finditer(r"(?m)^CHAPTER\s+\d+\.",base)]
            for pm in re.finditer(r"(?m)(?<!\n)([^\n]+)",base):
                line=pm.group(1)
                if re.match(r"^(CHAPTER\s+\d+\.|[A-Z][A-Z .,'’()-]{5,})",line): continue
                for sm in re.finditer(r"[.!?](?:[\"'’)]*)\s+",line):
                    b=pm.start()+sm.end()
                    if all(abs(b-h)>=200 for h in headings): boundaries.append(b)
            emitted=[]; inserts_at={}
            for f in ins:
                desired=int(f["fraction"]*len(base))
                if f["role"].startswith("single_"):
                    band=min(2,(f["ordinal"]-1)//10); low,high=[(.05,.30),(.35,.65),(.70,.95)][band]
                else: low,high=.05,.95
                candidates=[b for b in boundaries if low<=b/len(base)<=high and abs(b-desired)<2500]
                if not candidates: candidates=[b for b in boundaries if low<=b/len(base)<=high]
                at=min(candidates,key=lambda b:abs(b-desired)) if candidates else desired
                inserts_at.setdefault(at,[]).append(f)
            text=base
            for at,fs in sorted(inserts_at.items(),reverse=True):
                text=text[:at]+" "+" ".join(f["text"] for f in fs)+text[at:]
            counts=tokens(text); peak=max(counts.values())
            for f in ins:
                item=dict(f); item["char_offset"]=text.find(f["text"]); item["actual_fraction"]=item["char_offset"]/len(text); item["paragraph_index"]=text[:item["char_offset"]].count("\n\n"); emitted.append(item)
            if peak<=target: best,best_ins,best_counts=text,emitted,counts; lo=n+1
            else: hi=n-1
        if not best: raise RuntimeError(f"could not fit any source for {doc_id}")
        # final exact prompt reserve audit: largest question + conservative 512 template tokens
        qmax=max(max(tokens(q["prompt"]).values()) for q in qs)
        full={m:best_counts[m]+qmax+512 for m in TOK}
        if doc_id=="long_128k" and max(full.values())>CFG["ctx_size"]-2048: raise RuntimeError(f"128K headroom violated: {full}")
        p=DOCS/f"{doc_id}.txt"; p.write_text(best+"\n",encoding="utf-8")
        ip=DOCS/f"{doc_id}-insertions.json"; ip.write_text(json.dumps({"doc_id":doc_id,"insertions":best_ins},indent=2)+"\n")
        docs.append({"doc_id":doc_id,"path":f"documents/{doc_id}.txt","length_label":doc_id,"source":"Moby-Dick with plain-language planted maritime facts","license":"Public domain text; planted fact sentences CC0-1.0","bytes":p.stat().st_size,"sha256":sha(p.read_bytes()),"insertions_path":f"documents/{doc_id}-insertions.json","insertions_sha256":sha(ip.read_bytes()),"token_counts_document_only":best_counts,"full_prompt_token_count_estimate_including_512_template_allowance":full,"question_token_max":qmax})
    # Enforce exactly 5 single-retrieval questions in each third for every length.
    for did in targets:
        ps=[q["position"] for q in allq if q["doc_id"]==did and q["task_type"]=="single_retrieval"]
        if [ps.count(x) for x in ("early","middle","late")] != [5,5,5]: raise RuntimeError(f"single position balance failed: {did} {ps}")
    qpath=D/"questions.jsonl"; qpath.write_text("".join(json.dumps(q,ensure_ascii=False)+"\n" for q in allq))
    position_counts={did:{pos:sum(1 for q in allq if q["doc_id"]==did and q["task_type"]=="single_retrieval" and q["position"]==pos) for pos in ("early","middle","late")} for did in targets}
    task_counts={did:{task:sum(1 for q in allq if q["doc_id"]==did and q["task_type"]==task) for task in CFG["task_types"]} for did in targets}
    manifest={"source":{"title":"Moby-Dick; Or, The Whale","author":"Herman Melville","url":"https://www.gutenberg.org/cache/epub/2701/pg2701.txt","license":"Public domain in the United States; Project Gutenberg License applies to the distributed eBook wrapper/edition","source_sha256":source_hash,"normalization":"Extracted between Project Gutenberg markers; Unicode text; whitespace collapsed per source paragraph"},"documents":docs,"questions":{"path":"questions.jsonl","count":len(allq),"sha256":sha(qpath.read_bytes()),"count_by_length_and_task":task_counts,"single_retrieval_position_counts":position_counts},"synthetic_facts":{"method":"deterministic seeded random entities and answer codes; plain sentences interleaved at recorded source-text positions","count_by_role":{r:sum(1 for d in docs for x in json.loads((D/d["insertions_path"]).read_text())["insertions"] if x["role"]==r) for r in sorted({x["role"] for d in docs for x in json.loads((D/d["insertions_path"]).read_text())["insertions"]})},"positions":"fraction, paragraph index, and character offset in per-document insertion maps"},"tokenizers":{"sources":json.loads((D/"documents/manifest.json").read_text()).get("tokenizers",{}).get("sources",{}),"count_method":"Pinned upstream tokenizer.json; exact llama.cpp prompt token counts are authoritative at run time"}}
    (DOCS/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"questions":len(allq),"documents":[{"doc_id":d["doc_id"],"sha256":d["sha256"],"tokens":d["token_counts_document_only"],"full_prompt_estimate":d["full_prompt_token_count_estimate_including_512_template_allowance"]} for d in docs],"questions_sha256":manifest["questions"]["sha256"]},indent=2))
if __name__=="__main__": main()
