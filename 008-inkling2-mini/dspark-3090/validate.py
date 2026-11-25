#!/usr/bin/env python3
"""Verify the published DSpark numerical evidence without a GPU or network."""
from pathlib import Path
import collections
import gzip
import hashlib
import json
import statistics

ROOT=Path(__file__).resolve().parent
def read(name):return json.loads((ROOT/name).read_text())
rows=read('results-per-run.json')
summaries=read('results-summary.json')
native=[json.loads(s) for s in (ROOT/'native-timings.jsonl').read_text().splitlines()]
requests=read('requests.json')
commands=read('commands.json')['cells']
manifest=read('manifest.json')
assert len(rows)==len(native)==len(requests)==manifest['rows']==336
assert len(summaries)==len(commands)==manifest['cells']==28
assert len({(r['cell'],r['prompt'],r['rep']) for r in rows})==336
for name,expected in manifest['tasks_sha256'].items():
    assert hashlib.sha256((ROOT/'tasks'/name).read_bytes()).hexdigest()==expected
paired={};groups=collections.defaultdict(list)
for row,excerpt,request in zip(rows,native,requests):
    identity=(row['cell'],row['prompt'],row['rep'])
    assert identity==(excerpt['cell'],excerpt['task'],excerpt['rep'])==(request['cell'],request['task'],request['rep'])
    groups[row['cell']].append(row)
    timing=excerpt['timings'];body=request['request'];settings=excerpt['generation_settings']
    assert timing['predicted_n']==body['n_predict']==row['requested_tokens']
    assert timing['cache_n']==0 and not excerpt['truncated']
    assert excerpt['stop_type']=='limit'
    assert body['ignore_eos'] is True and body['cache_prompt'] is False
    assert body['seed']==4241+row['rep'] and row['rep'] in [1,2,3]
    for key in ['temperature','top_k','top_p','min_p','seed','ignore_eos','n_predict']:
        assert settings[key]==body[key]
    for key,value in timing.items():assert row['timing_'+key]==value
    if row['nmax'] is not None:
        assert 0<=timing['draft_n_accepted']<=timing['draft_n']
        assert row['acceptance_rate']==timing['draft_n_accepted']/timing['draft_n']
    key=(row['build'],row['sampler'],row['requested_tokens'],row['prompt'],row['rep'])
    if key in paired:assert paired[key]==body
    else:paired[key]=body
for summary in summaries:
    group=groups[summary['cell']]
    assert len(group)==12 and len({r['prompt'] for r in group})==4
    assert summary['mean_generated_tok_s']==statistics.mean(r['timing_predicted_per_second'] for r in group)
    assert summary['mean_prompt_tok_s']==statistics.mean(r['timing_prompt_per_second'] for r in group)
    off=next(s for s in summaries if s['build']==summary['build'] and s['sampler']==summary['sampler'] and s['requested_tokens']==summary['requested_tokens'] and s['nmax'] is None)
    assert summary['speedup_vs_same_build_off']==summary['mean_generated_tok_s']/off['mean_generated_tok_s']
    command=commands[summary['cell']]; stripped=[];i=0
    while i<len(command):
        if command[i] in ['-md','--spec-type','--spec-draft-n-max','-ngld']:i+=2
        else:stripped.append(command[i]);i+=1
    assert stripped==commands[off['cell']]
    assert '-devd' not in command and '--mtp' not in command
for log in manifest['server_logs']:
    assert hashlib.sha256(gzip.decompress((ROOT/log['path']).read_bytes())).hexdigest()==log['public_uncompressed_sha256']
for line in (ROOT/'SHA256SUMS').read_text().splitlines():
    digest,path=line.split('  ',1)
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
print('PASS: 336 measurements, 28 cells; native timings, settings, requests, same-build ratios, logs and file hashes verified.')
