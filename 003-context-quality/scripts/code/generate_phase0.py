#!/usr/bin/env python3
"""Freeze the 003 code haystacks, planted tasks, and provenance hashes."""
import ast, hashlib, json, random, re
from pathlib import Path
from tokenizers import Tokenizer

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'DATA'/'code'; DOCS=DATA/'documents'; INTERNAL=ROOT/'_internal'/'code'
SRC=INTERNAL/'source-repo'; MODIFIED=INTERNAL/'modified-source'
CFG=json.loads((ROOT/'DATA/study-config.json').read_text())['arms']['code']
MODELS=list(CFG['models'])
TOK={m:Tokenizer.from_file(str(INTERNAL/'tokenizers'/m/'tokenizer.json')) for m in MODELS}
TARGETS={'control':8192,'long_64k':65536,'long_128k':126000}
ALPHABET='abcdefghjkmnpqrstuvwxyz'


def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def token_counts(text): return {m:len(t.encode(text).ids) for m,t in TOK.items()}
def random_word(rng,n=8): return ''.join(rng.choice(ALPHABET) for _ in range(n))
def py_module(path):
    parts=Path(path).with_suffix('').parts
    if parts[-1]=='__init__': parts=parts[:-1]
    return '.'.join(parts)

def eligible_files():
    skip={'tests','test','migrations','vendor','vendored','_vendor','__pycache__','generated','locale','static','build','dist'}
    rows=[]
    for p in (SRC/'django').rglob('*.py'):
        rel=p.relative_to(SRC).as_posix(); parts={x.lower() for x in p.relative_to(SRC).parts}
        if parts & skip or p.name.lower().startswith('test') or p.name.endswith('_pb2.py') or 'generated' in p.name.lower(): continue
        text=p.read_text(encoding='utf-8').rstrip()
        if len(text.encode('utf-8'))<200: continue
        try: tree=ast.parse(text,filename=rel)
        except SyntaxError as exc: raise RuntimeError(f'pinned source does not parse at {rel}:{exc.lineno}: {exc.msg}')
        offsets=[]; line_end=0; line_offsets=[0]
        for line in text.splitlines(keepends=True):
            line_end+=len(line); line_offsets.append(line_end)
        for node in tree.body:
            end=getattr(node,'end_lineno',None)
            if end is not None: offsets.append(line_offsets[end])
        offsets=sorted(set(offsets))
        if not offsets: continue
        rows.append({'path':rel,'text':text,'bytes':len(text.encode('utf-8')),'boundaries':offsets})
    # Small-to-large byte order prevents a single large module from making a
    # whole-file target unreachable; path breaks ties reproducibly.
    rows.sort(key=lambda r:(r['bytes'],r['path']))
    root=next(r for r in rows if r['path']=='django/__init__.py')
    rows.remove(root); rows.insert(0,root)
    return rows


def make_plan(label):
    seed=390003+{'control':0,'long_64k':100,'long_128k':200}[label]
    rng=random.Random(seed); value_rng=random.Random(seed+900001)
    used=set(); value_suffixes=set(); questions=[]; events=[]; fact_links={}
    def ident(prefix):
        while True:
            value=f'{prefix}_{random_word(rng)}'
            suffix=value.rsplit('_',1)[-1].casefold()
            if value not in used and not any(suffix[:3]==v[:3] for v in value_suffixes):
                used.add(value); return value
    def value():
        while True:
            candidate=random_word(value_rng,10)
            if not any(candidate[:3]==ident.rsplit('_',1)[-1].casefold()[:3] for ident in used):
                value_suffixes.add(candidate); return candidate
    def add(eid,fraction,role,key,render,group=None,distinct=False,path=None):
        events.append({'id':eid,'fraction':float(fraction),'role':role,'key':key,'render':render,'group':group,'distinct':distinct,'path':path})
    def qrow(abbr,i,task,prompt,ref,neg,key,fractions):
        qid=f'003-code-{label}-{abbr}-{i+1:02d}'
        questions.append({'question_id':qid,'doc_id':label,'length_label':label,'task_type':task,
                          'position':'spread','prompt':prompt,'reference':ref,'negative_control':neg,
                          'entity_key':key,'fact_fractions':[]})
        fact_links[qid]=fractions
        return qid

    # One real Python decorator implementation per randomized registry. Target
    # and near-miss decorators are defined in django/__init__.py.
    decorator=ident('register'); registry_store=ident('_registry')
    # Single retrieval: 15 module-level constants with near-miss names/values.
    for i in range(15):
        target=ident('SETTING'); distractor=target+'_ALT'; answer=value(); decoy=value()
        while decoy==answer: decoy=value()
        fractions=([.05,.06,.07,.08,.09,.35,.39,.42,.45,.48,.91,.92,.93,.94,.95]
                   if label=='control' else
                   [.075,.12,.19,.24,.285,.365,.41,.47,.53,.615,.715,.765,.82,.885,.935])
        f=fractions[i]
        decoy_fraction=min(.95,f+.006)
        te=f'{label}-sr-{i+1:02}-target'; de=f'{label}-sr-{i+1:02}-decoy'
        add(te,f,'single_target',target,lambda path,t=target,v=answer:f"{t} = '{v}'",group=f'{label}-sr-{i+1:02}',distinct=True)
        add(de,decoy_fraction,'single_decoy',distractor,lambda path,t=distractor,v=decoy:f"{t} = '{v}'")
        pos='early' if i<5 else ('middle' if i<10 else 'late')
        qid=qrow('sr',i,'single_retrieval',
            f'Return one JSON object with this exact shape: {{"value": "string"}}. What string is assigned to the module-level constant {target}?',
            {'value':answer},{'value':decoy},[target],[te])
        questions[-1]['position']=pos

    # Multi retrieval: each question has four registered functions in separate
    # modules; nearby functions use a different decorator and are decoys.
    for i in range(15):
        tag=ident('tag'); near_tag=ident('tag_near')
        targets=[]; event_ids=[]
        zones=((.10,.22),(.31,.43),(.55,.67),(.76,.85))
        sampled_positions=[rng.uniform(lo,hi) for lo,hi in zones]
        for j,f in enumerate(sampled_positions):
            fn=ident('handle'); ans=value(); eid=f'{label}-mr-{i+1:02}-target-{j+1}'
            add(eid,f,'multi_target',tag,
                lambda path,fn=fn,tag=tag,reg=decorator,ans=ans:f"from django import {reg}\n\n@{reg}('{tag}')\ndef {fn}():\n    pass",
                group=f'{label}-mr-{i+1:02}',distinct=True)
            targets.append(fn); event_ids.append(eid)
        decoy_name=targets[0]+'_near'
        alt_value=value(); de=f'{label}-mr-{i+1:02}-decoy'
        add(de,rng.uniform(.10,.85),'multi_decoy',near_tag,
            lambda path,fn=decoy_name,tag=near_tag,reg=decorator,ans=alt_value:f"from django import {reg}\n\n@{reg}('{tag}')\ndef {fn}():\n    pass")
        qid=qrow('mr',i,'multi_retrieval',
            f'Return one JSON object with this exact shape: {{"answers": ["name1", "name2", "name3", "name4"]}}; every answers item must be a string. List the four function names decorated with @{decorator}(\'{tag}\').',
            {'answers':targets},{'answers':[ident('missing') for _ in range(4)]},[decorator,tag],event_ids)

    # Aggregation: exact AST call-site counts from 2 through 8, with similar
    # helper names and one or more decoy calls.
    for i in range(15):
        helper=ident('lookup'); decoy=helper+'_near'; n=2+(i%7)
        defn=f'{label}-ag-{i+1:02}-definition'; decdef=f'{label}-ag-{i+1:02}-decoy-definition'
        f=rng.uniform(.10,.85)
        add(defn,f,'aggregation_definition',helper,lambda path,h=helper:f'def {h}():\n    pass',group=f'{label}-ag-{i+1:02}',distinct=True)
        add(decdef,min(.94,f+.004),'aggregation_decoy_definition',decoy,lambda path,h=decoy:f'def {h}():\n    pass')
        calls=[]
        for j in range(n):
            cf=rng.uniform(.10,.85); eid=f'{label}-ag-{i+1:02}-call-{j+1}'
            caller=ident('call')
            add(eid,cf,'aggregation_call',helper,
                lambda path,h=helper,caller=caller:f'def {caller}():\n    return {h}()',
                group=f'{label}-ag-{i+1:02}',distinct=True, path=None)
            calls.append(eid)
        decoy_caller=ident('call'); de=f'{label}-ag-{i+1:02}-decoy-call'
        add(de,rng.uniform(.10,.85),'aggregation_decoy_call',decoy,
            lambda path,h=decoy,caller=decoy_caller:f'def {caller}():\n    return {h}()')
        qid=qrow('ag',i,'aggregation',
            f'Return one JSON object with this exact shape: {{"count": integer}}. In how many call expressions across the repository is the exact helper {helper} called? Do not count its definition or similarly named helpers.',
            {'count':n},{'count':n+1 if n<8 else n-1},[helper],[defn]+calls)

    # Multi-hop chains are connected by imports and span three distinct files.
    for i in range(15):
        fn_a=ident('resolve'); fn_b=ident('lookup'); const=ident('VALUE')
        answer=value(); alt=value()
        while alt==answer: alt=value()
        eids=[]
        fractions=tuple(rng.uniform(.10,.85) for _ in range(3))
        for kind,f in zip(('a','b','c'),fractions):
            eid=f'{label}-mh-{i+1:02}-{kind}'
            if kind=='a':
                add(eid,f,'hop_a',fn_a,lambda path,fa=fn_a,fb=fn_b:f'def {fa}():\n    return {fb}()',group=f'{label}-mh-{i+1:02}',distinct=True)
            elif kind=='b':
                add(eid,f,'hop_b',fn_b,lambda path,fb=fn_b,c=const:f'def {fb}():\n    return {c}',group=f'{label}-mh-{i+1:02}',distinct=True)
            else:
                add(eid,f,'hop_c',const,lambda path,c=const,v=answer:f"{c} = '{v}'",group=f'{label}-mh-{i+1:02}',distinct=True)
            eids.append(eid)
        dc=const+'_NEAR'; eid=f'{label}-mh-{i+1:02}-decoy'
        add(eid,rng.uniform(.10,.85),'hop_decoy_c',dc,lambda path,c=dc,v=alt:f"{c} = '{v}'")
        qid=qrow('mh',i,'multi_hop',
            f'Return one JSON object with this exact shape: {{"value": "string"}}. Starting from function {fn_a}, follow its call and the value read by that function. What string value does the call chain return?',
            {'value':answer},{'value':alt},[fn_a],eids)

    # The registry helpers live in an existing package initializer. Imports in
    # planted functions use the normal package path and are parseable Python.
    regtext=(f'{registry_store} = {{}}\n\ndef {decorator}(key):\n'
             f'    def decorate(function):\n'
             f'        {registry_store}.setdefault(key, []).append(function.__name__)\n'
             f'        return function\n'
             f'    return decorate')
    add(f'{label}-registry-definitions',.02,'registry_definitions','registry',lambda path,t=regtext:t,path='django/__init__.py')

    # Resolve paths. All desired fact positions are mapped to eligible source
    # modules; within each module insert only at an AST top-level boundary.
    return questions,events,fact_links


def make_candidate(files,n,label):
    selected=files[:n]
    if 'django/__init__.py' not in {x['path'] for x in selected}: return None
    base_parts=[]; offsets={}; char_cursor=0
    for row in selected:
        header=f"# file: {row['path']}\n"
        start=char_cursor+len(header)
        offsets[row['path']]={'header_start':char_cursor,'body_start':start,'body_end':start+len(row['text']),'row':row}
        base_parts.extend((header,row['text'],'\n\n'))
        char_cursor+=len(header)+len(row['text'])+2
    base=''.join(base_parts); base_len=len(base)
    questions,events,fact_links=make_plan(label)
    # Estimate injected character mass, then assign a concrete module to every
    # snippet in target-position order. Distinct facts in one question use
    # distinct modules.
    placeholders={e['id']:e['render']('django.contrib.placeholder.module') for e in events}
    est_total=sum(len(v)+2 for v in placeholders.values())
    group_paths={}; assigned=[]; cumulative=0
    ordered=sorted(events,key=lambda e:(e['fraction'],e['id']))
    for event in ordered:
        desired_source=event['fraction']*(base_len+est_total)-cumulative
        target=max(0,min(base_len,desired_source))/max(1,base_len)
        if event['path']:
            choices=[event['path']] if event['path'] in offsets else []
        else:
            choices=[]
            group=event['group']
            excluded=group_paths.setdefault(group,set()) if group and event['distinct'] else set()
            candidates=[]
            for path,info in offsets.items():
                if path=='django/__init__.py': continue
                if event['distinct'] and path in excluded: continue
                candidates.append(path)
            if not candidates:return None
            target_char=target*base_len
            # Prefer modules with an AST insertion boundary nearest the requested
            # character position. Ranking by module midpoint can send a target
            # to a distant file edge when whole-file boundaries are sparse.
            def boundary_distance(path):
                info=offsets[path]
                return min(abs(info['body_start']+b-target_char) for b in info['row']['boundaries'])
            choices=sorted(candidates,key=boundary_distance)
        if not choices:return None
        path=choices[0]
        if event['distinct'] and event['group']: group_paths.setdefault(event['group'],set()).add(path)
        text=event['render'](path)
        event['path']=path; event['text']=text
        assigned.append(event); cumulative+=len(text)+2
    # Resolve cross-file names with ordinary package imports so planted calls
    # form valid code relationships as well as valid syntax.
    aggregation_def={e['key']:e for e in assigned if e['role']=='aggregation_definition'}
    hop_nodes={(e['group'],e['role']):e for e in assigned if e['role'] in ('hop_a','hop_b','hop_c')}
    for event in assigned:
        dep=None
        if event['role']=='aggregation_call': dep=aggregation_def[event['key']]
        elif event['role']=='hop_a': dep=hop_nodes[(event['group'],'hop_b')]
        elif event['role']=='hop_b': dep=hop_nodes[(event['group'],'hop_c')]
        if dep and dep['path']!=event['path']:
            event['text']=f"from {py_module(dep['path'])} import *\n\n"+event['text']
    # Re-place with final snippet sizes (including cross-file imports) so the
    # intended character fractions account for all planted-code overhead.
    for _ in range(4):
        total=sum(len(e['text'])+2 for e in assigned)
        group_paths={}; cumulative=0; changed=False
        for event in sorted(assigned,key=lambda e:(e['fraction'],e['id'])):
            source_target=max(0,min(base_len,event['fraction']*(base_len+total)-cumulative))
            if event['role']=='registry_definitions':
                path='django/__init__.py'
            else:
                group=event['group']; excluded=group_paths.setdefault(group,set()) if group and event['distinct'] else set()
                candidates=[p for p in offsets if p!='django/__init__.py' and (not event['distinct'] or p not in excluded)]
                path=min(candidates,key=lambda p:min(abs(offsets[p]['body_start']+b-source_target) for b in offsets[p]['row']['boundaries']))
            if event['distinct'] and event['group']: group_paths.setdefault(event['group'],set()).add(path)
            if path!=event['path']: changed=True
            event['path']=path; cumulative+=len(event['text'])+2
        aggregation_def={e['key']:e for e in assigned if e['role']=='aggregation_definition'}
        hop_nodes={(e['group'],e['role']):e for e in assigned if e['role'] in ('hop_a','hop_b','hop_c')}
        for event in assigned:
            text=event['render'](event['path']); dep=None
            if event['role']=='aggregation_call': dep=aggregation_def[event['key']]
            elif event['role']=='hop_a': dep=hop_nodes[(event['group'],'hop_b')]
            elif event['role']=='hop_b': dep=hop_nodes[(event['group'],'hop_c')]
            if dep and dep['path']!=event['path']: text=f"from {py_module(dep['path'])} import *\n\n"+text
            event['text']=text
        if not changed: break
    ordered=sorted(assigned,key=lambda e:(e['fraction'],e['id']))
    boundaries=sorted((info['body_start']+b,path,b) for path,info in offsets.items() for b in info['row']['boundaries'])
    # Select among all top-level AST boundaries in document order. This keeps
    # actual insertion fractions stable after code/import overhead is counted.
    for _ in range(4):
        total_insert=sum(len(e['text'])+2 for e in ordered)
        cumulative=0; previous=-1; group_paths={}; path_changed=False; used_boundaries=[]; used_fact_files=set()
        for event in ordered:
            target=event['fraction']*(base_len+total_insert)-cumulative
            sr_match=re.fullmatch(r'control-sr-(\d{2})',event['group'] or '') if label=='control' and event['role'] in ('single_target','single_decoy') else None
            if label=='control':
                choices=[b for b in boundaries if b[0]>=previous and
                         (b[1]=='django/__init__.py' if event['role']=='registry_definitions' else b[1]!='django/__init__.py')]
                if sr_match and event['role']=='single_target':
                    index=int(sr_match.group(1))
                    band=('early' if index<=5 else ('middle' if index<=10 else 'late'))
                    projected=lambda b:(b[0]+cumulative)/(base_len+total_insert)
                    in_band=lambda f:(f<.34 if band=='early' else (0.33<=f<=.67 if band=='middle' else f>.66))
                    choices=[b for b in choices if in_band(projected(b))]
                    if not choices: raise RuntimeError(f'no monotonic in-band insertion boundary for {event["id"]}')
                fresh=[b for b in choices if b[0] not in used_boundaries]
                if fresh: choices=fresh
                if not choices: raise RuntimeError(f'no forward insertion boundary for {event["id"]}')
            elif event['role']=='registry_definitions': choices=[b for b in boundaries if b[1]=='django/__init__.py']
            else:
                excluded=group_paths.setdefault(event['group'],set()) if event['group'] and event['distinct'] else set()
                choices=[b for b in boundaries if b[1]!='django/__init__.py' and b[0]>=previous and (not event['distinct'] or b[1] not in excluded) and all(abs(b[0]-u)>250 for u in used_boundaries)]
            if not choices:
                choices=[b for b in boundaries if (event['role']=='registry_definitions' and b[1]=='django/__init__.py' or event['role']!='registry_definitions' and b[1]!='django/__init__.py') and (not event['distinct'] or b[1] not in excluded) and all(abs(b[0]-u)>0 for u in used_boundaries)]
            if not choices:
                choices=[b for b in boundaries if (event['role']=='registry_definitions' and b[1]=='django/__init__.py' or event['role']!='registry_definitions' and b[1]!='django/__init__.py') and (not event['distinct'] or b[1] not in excluded) and all(abs(b[0]-u)>0 for u in used_boundaries)]
            if not choices:
                choices=[b for b in boundaries if b[1]!='django/__init__.py' and all(abs(b[0]-u)>0 for u in used_boundaries)]
            if not choices:
                choices=[b for b in boundaries if (event['role']=='registry_definitions' and b[1]=='django/__init__.py' or event['role']!='registry_definitions' and b[1]!='django/__init__.py')]
            if event['distinct']:
                unused_near=[b for b in choices if b[1] not in used_fact_files and abs(b[0]-target)<=base_len*.05]
                if unused_near: choices=unused_near
            choice=min(choices,key=lambda b:abs(b[0]-target))
            if event['distinct']: used_fact_files.add(choice[1])
            used_boundaries.append(choice[0])
            if event['path']!=choice[1]: path_changed=True
            event['path']=choice[1]; event['local_offset']=choice[2]; previous=choice[0]
            if event['distinct'] and event['group']: group_paths.setdefault(event['group'],set()).add(event['path'])
            cumulative+=len(event['text'])+2
        aggregation_def={e['key']:e for e in ordered if e['role']=='aggregation_definition'}
        hop_nodes={(e['group'],e['role']):e for e in ordered if e['role'] in ('hop_a','hop_b','hop_c')}
        for event in ordered:
            text=event['render'](event['path']); dep=None
            if event['role']=='aggregation_call': dep=aggregation_def[event['key']]
            elif event['role']=='hop_a': dep=hop_nodes[(event['group'],'hop_b')]
            elif event['role']=='hop_b': dep=hop_nodes[(event['group'],'hop_c')]
            if dep and dep['path']!=event['path']: text=f"from {py_module(dep['path'])} import *\n\n"+text
            event['text']=text
        if not path_changed: break
    placed=ordered
    by_file={p:{} for p in offsets}
    for event in placed: by_file[event['path']].setdefault(event['local_offset'],[]).append(event)
    docs=[]; actual={}; modified_files={}
    for row in selected:
        path=row['path']; original=row['text']; insertions=by_file[path]
        pieces=[]; cursor=0
        header=f'# file: {path}\n'; doc_offset=sum(len(d)+2 for d in docs); pieces.append(header)
        file_event_starts={}
        for local in sorted(insertions):
            pieces.append(original[cursor:local]); current=''.join(pieces)
            if current and not current.endswith('\n'): pieces.append('\n'); current+='\n'
            if current and not current.endswith('\n\n'): pieces.append('\n')
            for event in sorted(insertions[local],key=lambda e:(e['fraction'],e['id'])):
                pieces.append(''); snippet=event['text'].strip(); start=len(''.join(pieces)); pieces.append(snippet); pieces.append('\n\n')
                file_event_starts[event['id']]=start
            cursor=local
        pieces.append(original[cursor:]); content=''.join(pieces)
        modified_files[path]=content; docs.append(content)
        for event_id,pos in file_event_starts.items(): actual[event_id]=doc_offset+pos
    document='\n\n'.join(docs).rstrip()+'\n'
    # Recompute offsets against final concatenation by unique snippet occurrence.
    for event in placed:
        if event['id'] not in actual:
            matches=[m.start() for m in re.finditer(re.escape(event['text'].strip()),document)]
            if not matches: raise RuntimeError(f"planted text missing: {event['id']}")
            actual[event['id']]=matches[0]
    fractions={eid:actual[eid]/len(document) for eid in actual}
    qby={q['question_id']:q for q in questions}
    for qid,ids in fact_links.items():
        q=qby[qid]; q['fact_fractions']=[round(fractions[x],6) for x in ids]
        # Preserve the nominal 5/5/5 labels. The recorded fractions are the
        # actual positions; sparse control-document boundaries can put a
        # nominal target just outside its band.
    return {'document':document,'questions':questions,'events':placed,'actual':fractions,'files':selected,'modified':modified_files,'counts':token_counts(document)}


def main():
    files=eligible_files()
    # Keep only substantial Python modules; pinned-repo tree counts are recorded separately.
    if sum(x['bytes'] for x in files)<600_000: raise RuntimeError('less than 600 KB of eligible first-party Python source')
    DOCS.mkdir(parents=True,exist_ok=True)
    all_questions=[]; docs_manifest=[]; all_events=[]
    for label,target in TARGETS.items():
        lo,hi=1,min(len(files),12) if label=='control' else len(files); best=None; best_n=0
        while lo<=hi:
            mid=(lo+hi)//2
            trial=make_candidate(files,mid,label)
            if trial is None:
                lo=mid+1; continue
            peak=max(trial['counts'].values())
            if peak<=target:
                best=trial; best_n=mid; lo=mid+1
            else: hi=mid-1
        if best is None: raise RuntimeError(f'no whole-file prefix with plants fits target {label}')
        # Final prompt allowance uses the longest frozen question under each tokenizer.
        qrows=best['questions']; qtokens={m:max(len(TOK[m].encode(q['prompt']).ids) for q in qrows) for m in MODELS}
        full={m:best['counts'][m]+qtokens[m]+512 for m in MODELS}
        headroom={m:CFG['ctx_size']-full[m] for m in MODELS}
        if min(headroom.values())<2048: raise RuntimeError(f'{label}: insufficient context headroom {headroom}')
        path=DOCS/f'{label}.txt'; path.write_text(best['document'],encoding='utf-8')
        import shutil
        out=MODIFIED/label
        if out.exists(): shutil.rmtree(out)
        for rel,text in best['modified'].items():
            target_path=out/rel; target_path.parent.mkdir(parents=True,exist_ok=True); target_path.write_text(text+'\n',encoding='utf-8')
            try: ast.parse((text+'\n'),filename=rel)
            except SyntaxError as exc: raise RuntimeError(f'planted source failed ast.parse: {label}/{rel}:{exc.lineno}: {exc.msg}')
        max_doc=max(best['counts'].values())
        if max_doc<target*.88: print(f'NOTE {label}: whole-file boundary ended at {max_doc}, below 88% of target {target}')
        for event in best['events']:
            qm=re.match(r'(control|long_64k|long_128k)-(sr|mr|ag|mh)-(\d+)',event['id'])
            qid=f"003-code-{label}-{qm.group(2)}-{qm.group(3)}" if qm else None
            all_events.append({'doc_id':label,'event_id':event['id'],'question_id':qid,'role':event['role'],'key':event['key'],'path':event['path'],'insertion_offset':event['local_offset'],'fraction':round(best['actual'][event['id']],6),'source_snippet':event['text']})
        all_questions.extend(best['questions'])
        positions={p:sum(q['task_type']=='single_retrieval' and q['position']==p for q in best['questions']) for p in ('early','middle','late')}
        if list(positions.values())!=[5,5,5]: raise RuntimeError(f'{label}: single-retrieval position balance failed: {positions}')
        docs_manifest.append({'doc_id':label,'path':f'documents/{label}.txt','length_label':label,
            'target_max_tokens':target,'file_count':best_n,'ordered_files':[r['path'] for r in best['files']],
            'source_file_list_sha256':sha_bytes('\n'.join(r['path'] for r in best['files']).encode()),
            'bytes':path.stat().st_size,'sha256':sha_bytes(path.read_bytes()),'token_counts_document_only':best['counts'],
            'max_question_tokens':qtokens,'estimated_full_prompt_tokens_with_512_template_allowance':full,
            'context_headroom_tokens':headroom,'single_retrieval_position_counts':positions})
        print(f'{label}: {best_n} whole files, {best["counts"]}, headroom={headroom}')
    qpath=DATA/'questions.jsonl'; qpath.write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in all_questions),encoding='utf-8')
    boundary_usage={label:{'events':sum(e['doc_id']==label for e in all_events),'unique_file_offsets':len({(e['path'],e['insertion_offset']) for e in all_events if e['doc_id']==label}),'events_reusing_offsets':sum(e['doc_id']==label for e in all_events)-len({(e['path'],e['insertion_offset']) for e in all_events if e['doc_id']==label})} for label in TARGETS}
    planting=INTERNAL/'planting-map.json'; planting.write_text(json.dumps({'study':'003-code','seed_rule':'name/position RNG seed = 390003 + {control: 0, long_64k: 100, long_128k: 200}; independent value RNG adds 900001','value_generation':'independent value stream with rejection of any 3-character prefix shared with a generated identifier','insertion_boundary_usage':boundary_usage,'facts':all_events},indent=2)+'\n',encoding='utf-8')
    manifest={'study':'CUDA Recipes 003: Long-Context Quality on Prose and Code (24GB) — Code arm','frozen':True,
        'repository':{'name':'Django','url':'https://github.com/django/django','commit':'d430084791a61b31cecec132bce3dca19194f7f2','license':'BSD-3-Clause',
          'eligible_python_files':len(files),'eligible_first_party_python_bytes':sum(r['bytes'] for r in files),
          'file_order':'ascending source-file byte length, then repository-relative path; django/__init__.py first; only whole files included',
          'exclusions':['tests','migrations','locale data','vendored/generated/static/build files','Python modules below 200 bytes']},
        'documents':docs_manifest,'insertion_boundary_usage':boundary_usage,'questions':{'path':'questions.jsonl','count':len(all_questions),'sha256':sha_bytes(qpath.read_bytes()),
          'count_by_length_and_task':{label:{t:sum(q['doc_id']==label and q['task_type']==t for q in all_questions) for t in CFG['task_types']} for label in TARGETS}},
        'planting_map':{'path':'_internal/code/planting-map.json','sha256':sha_bytes(planting.read_bytes()),'event_count':len(all_events)},
        'tokenizers':{'sources':json.loads((ROOT/'DATA/documents/manifest.json').read_text())['tokenizers']['sources'],
          'count_method':'pinned upstream tokenizer.json files copied unchanged from 003; document-only tokens are exact tokenizer encode counts; prompt estimate adds the longest question plus 512 template allowance'},
        'value_generation':'independent PRNG stream; 3-character prefix overlap rejection against identifiers','planting':{'all_modified_files_ast_parse':'passed','single_retrieval':'15 per length, five per nominal third, control actual fractions constrained to each nominal band',
          'other_task_positions':'sampled independently per question/fact within 5–95%; multi-retrieval uses four disjoint spread zones','file_diversity':'main facts prefer a source file unused by another question within a 5% character window of target; reuse protects position when no nearby unused file is available' ,'placement_spacing':'distinct AST boundaries are used before reuse; the compact control has fewer boundaries than inserted events, so repeated offsets there are unavoidable; 64K and 128K do not reuse offsets','prompts':'explicit JSON shape and item types'}}
    mpath=DOCS/'manifest.json'; mpath.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    CFG['status']='phase0_frozen'; CFG['frozen']=True; CFG['repository']=manifest['repository']
    # The integrated study config is maintained at DATA/study-config.json; do not overwrite it here.
    print(f'questions={len(all_questions)} sha256={manifest["questions"]["sha256"]} planting_map_sha256={manifest["planting_map"]["sha256"]}')

if __name__=='__main__': main()
