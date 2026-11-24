#!/usr/bin/env python3
"""Regenerate RTX 3090 result tables and captured-command catalog."""
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
def link(path):return f'[{Path(path).name}]({path})' if path else 'Unavailable'
def render():
    data=json.loads((ROOT/'results.json').read_text());rows=data['measurements']
    names={'rtx3090':'RTX 3090 / primary host','rtx3090-depth':'RTX 3090 / depth host'}
    models={'base':'Base UD-Q4_K_M','adq4':'Uncensored AD-Q4_K'}
    lines=['# RTX 3090 results','','Rates are llama-bench means in tokens per second. Sample standard deviations and sample arrays are reproduced from the captured JSON. Single-repetition results do not estimate variation.','','## Primary measurements','','| Artifact | Metric | Mean tok/s | Sample SD | Samples | Evidence |','|---|---|---:|---:|---|---|']
    for r in rows:
        if r['kind']!='primary':continue
        lines.append(f"| {models[r['model']]} | {r['metric']} | {r['mean_tok_s']:.6f} | {r['sample_stddev_tok_s']:.6f} | {', '.join(map(str,r['samples_tok_s']))} | {link(r['stdout'])} |")
    lines+=['','## Decode with existing synthetic context','','| Host | Artifact | Depth | Mean tok/s | Sample SD | Reps | KV | Batch / ubatch | Evidence |','|---|---|---:|---:|---:|---:|---|---|---|']
    for r in rows:
        if r['kind']!='depth':continue
        s=r['settings'];lines.append(f"| {names[r['system']]} | {models[r['model']]} | {r['depth_tokens']:,} | {r['mean_tok_s']:.6f} | {r['sample_stddev_tok_s']:.6f} | {r['repetitions']} | {s['type_k']}/{s['type_v']} | {s['n_batch']}/{s['n_ubatch']} | {link(r['stdout'])} |")
    lines+=['','The initial 128K depth attempts produced no result rows. The verified 128K/256K rerun used a separate RTX 3090 host and one repetition per setting. Cache precision and batch settings change with depth.','','## Context allocation and short generation','','The configured window was allocated and a short response requested. These checks do not score full-window recall.','','| Artifact | Attempt | Outcome | Metadata / command | Output |','|---|---|---|---|---|']
    for r in data['context_tests']:
        lines.append(f"| {models[r['model']]} | {r['name']} | {r['status']} | {link(r['metadata'])} | {link(r['stdout'])} |")
    lines+=['','See [FAILURES.md](FAILURES.md) for failed allocations, changed settings and the lost-pod correction. Full row settings are in [results.json](results.json); expanded invocations are in [COMMANDS.md](COMMANDS.md).','']
    commands=['# Captured RTX 3090 commands','','Private paths are normalized to `/study`. Substitute your local executable and model paths while preserving all workload flags. Each command is captured from per-run metadata; timestamps, exit status and associated diagnostics remain in the linked evidence.','']
    runs=json.loads((ROOT/'run-index.json').read_text())
    for i,r in enumerate(runs+data['context_tests'],1):
        name=r.get('id',r.get('name'))
        commands += [f"## {i}. {r['system']} / {r['model']} / {name}",'',f"Status: `{r['status']}`. Command provenance: `{r['command_provenance']}`. Metadata: {link(r['metadata'])}.",'','```text',r['command'],'```','']
    return {'RESULTS.md':'\n'.join(lines),'COMMANDS.md':'\n'.join(line.rstrip() for line in commands)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    for name,text in render().items():
        f=ROOT/name
        if a.check:
            if not f.exists() or f.read_text()!=text:raise SystemExit(f'{name} is not current')
        else:f.write_text(text)
    print('RTX 3090 tables and commands verified' if a.check else 'RTX 3090 tables and commands generated')
if __name__=='__main__':main()
