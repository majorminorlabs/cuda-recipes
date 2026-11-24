#!/usr/bin/env python3
"""Check public evidence integrity, numerical provenance and study invariants."""
from pathlib import Path
import gzip, hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/name).read_text())
def require(condition,message):
    if not condition:raise SystemExit(message)
data=load('results.json');manifest=load('evidence-manifest.json');runs=load('run-index.json')
models=load('models.json');systems=load('systems.json');contents={}
require(set(systems)=={'rtx3090','rtx3090-depth'},'Unexpected hardware scope')
require(set(models)=={'base','adq4'},'Expected the two Q4 artifacts')
require(systems['rtx3090']['hardware']['gpu_vram_mib']==24576,'Incorrect primary GPU capacity')
require(systems['rtx3090-depth']['hardware']['gpu_vram_mib']==24576,'Incorrect depth GPU capacity')
for entry in manifest['files']:
    p=ROOT/entry['path'];encoded=p.read_bytes();raw=gzip.decompress(encoded)
    require(hashlib.sha256(encoded).hexdigest()==entry['gzip_sha256'],f'Compressed hash: {p}')
    require(hashlib.sha256(raw).hexdigest()==entry['public_content_sha256'],f'Content hash: {p}')
    require(len(raw)==entry['public_bytes'],f'Content size: {p}')
    contents[entry['path']]=raw
actual={p.relative_to(ROOT).as_posix() for p in (ROOT/'evidence').rglob('*') if p.is_file()}
require(set(contents)==actual,'Evidence directory and manifest differ')
ids=[r['id'] for r in data['measurements']]
require(len(ids)==len(set(ids)),'Duplicate measurement IDs')
require(len(runs)==len({r['id'] for r in runs}),'Duplicate run IDs')
run_map={r['id']:r for r in runs}
for row in data['measurements']:
    require(row['system'] in systems and row['model'] in models,'Unknown machine/model')
    require(row['run'] in run_map,'Missing run command record')
    raw=json.loads(contents[row['stdout']].decode())
    found=[r for r in raw if r['n_depth']==row['depth_tokens'] and r['n_prompt']==row['settings']['n_prompt'] and r['n_gen']==row['settings']['n_gen']]
    require(len(found)==1,f'Raw row missing/ambiguous: {row["id"]}')
    r=found[0]
    for key,source in [('mean_tok_s','avg_ts'),('sample_stddev_tok_s','stddev_ts'),('samples_tok_s','samples_ts')]:
        require(row[key]==r[source],f'Numerical mismatch: {row["id"]} / {key}')
    require(row['repetitions']==len(r['samples_ts']),'Incorrect repetition count')
    require(r['build_commit']==data['llama_cpp_commit'][:len(r['build_commit'])],'Unexpected source commit')
    require(models[row['model']]['filename'] in r['model_filename'],'Wrong model assignment')
    for key,value in row['settings'].items():require(r[key]==value,f'Settings mismatch: {row["id"]}')
for r in runs+data['context_tests']:
    for field in ['stdout','stderr','metadata']:
        if r.get(field):require(r[field] in contents,f'Missing evidence: {r[field]}')
    require(r.get('command') or r['status']=='no_measurement',f'Missing command: {r.get("id")}')
selected=[r for r in data['measurements'] if r['kind'] in {'primary','tuning'} and r['selection']=='selected']
require(len(selected)==4,f'Expected four selected primary rows, found {len(selected)}')
require(len({(r['system'],r['model'],r['metric']) for r in selected})==4,'Duplicate selected primary')
deep=[r for r in data['measurements'] if r['system']=='rtx3090-depth']
require(len(deep)==4 and all(r['repetitions']==1 for r in deep),'Expected four one-rep verified deep rows')
require(len(data['measurements'])==12,'Expected twelve measurement rows')
require(len(runs)==14,'Expected fourteen timing/behavior run records')
require(all(r['system'] in systems and r['model'] in models for r in runs+data['context_tests']),'Unexpected run scope')
require(len(data['context_tests'])==14,'Expected fourteen context attempts')
require(sum(r['status']=='failed_oom' for r in data['context_tests'])==10,'Expected ten context allocation failures')
require(sum(r['status']=='passed' for r in data['context_tests'])==4,'Expected four successful context loads')
require(len(contents)==274,'Expected 274 evidence files')
require(sum(r['status']=='no_measurement' for r in runs)==2,'Expected two incomplete initial depth attempts')
expected={
    ('base','pp512',0):1411.470954,('base','tg128',0):59.106860,
    ('adq4','pp512',0):1454.322674,('adq4','tg128',0):58.713510,
    ('base','decode128',131072):36.646339,('adq4','decode128',131072):36.685906,
    ('base','decode128',262144):24.842185,('adq4','decode128',262144):25.018935,
}
for key,value in expected.items():
    found=[r for r in data['measurements'] if (r['model'],r['metric'],r['depth_tokens'])==key]
    require(len(found)==1 and found[0]['mean_tok_s']==value,f'Required result mismatch: {key}')
for row in data['measurements']:
    require(row['repetitions']==(1 if row['system']=='rtx3090-depth' else 3),'Unexpected repetition count')
for r in data['context_tests']:
    captured=(contents[r['stdout']]+contents[r['stderr']]).decode()
    failed=bool(re.search(r'out of memory|failed to allocate|OutOfMemory',captured,re.I))
    require(failed==(r['status']=='failed_oom'),f'Context classification mismatch: {r["name"]}')
figures=load('CHARTS/figure-data.json')
require(set(figures)=={'overview','decode-depth'},'Unexpected figure set')
measurement_map={r['id']:r for r in data['measurements']}
for figure in figures.values():
    require(figure['measurement_ids']==[v['id'] for v in figure['values']],'Figure IDs do not match values')
    for value in figure['values']:
        require(value['id'] in measurement_map,'Unknown plotted row')
        for key,number in value.items():require(number==measurement_map[value['id']][key],'Plotted value mismatch')
for suffix in ['png','svg']:
    require({p.stem for p in (ROOT/'CHARTS').glob('*.'+suffix)}==set(figures),'Chart files do not match declared figures')
private=re.compile(r'/Use[r]s/|/Volu[m]es/|C:(?:\\+)(?:Users|Research)(?:\\+)|DESKTOP-[A-Z0-9]+|100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.|(?:gh[pousr]_|hf_)[A-Za-z0-9]{20,}|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----')
for rel,raw in contents.items():require(not private.search(raw.decode()),f'Unsanitized evidence: {rel}')
for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix in {'.png','.ttf','.gz'} or '.git' in p.parts:continue
    text=p.read_text()
    # The scanner itself necessarily contains detection patterns.
    if p.name!='validate.py':require(not private.search(text),f'Unsanitized public file: {p.relative_to(ROOT)}')
    require(not re.search(r'\b(?:gh[pousr]_|hf_)[A-Za-z0-9]{20,}\b',text),f'Credential-shaped string: {p}')
print(f'PASS: {len(contents)} evidence files; {len(data["measurements"])} measurements; {len(data["context_tests"])} context attempts; public paths and source values verified')
