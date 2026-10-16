#!/usr/bin/env python3
"""Dependency-free integrity checks for the standalone package data."""
import csv, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read_csv(name):
    with (ROOT/'DATA'/name).open(newline='') as f:
        return list(csv.DictReader(f))
def read_json(name):
    return json.loads((ROOT/'DATA'/name).read_text())

def main():
    runs={
        'rtx3090':read_csv('rtx3090-canonical-runs.csv'),
        'rtx5090':read_csv('rtx5090-canonical-runs.csv'),
    }
    canonical={g:read_json(f'{g}-canonical-results.json') for g in runs}
    expected={'rtx3090':164,'rtx5090':155}
    all_keys={}
    for gpu,rows in runs.items():
        keys=[(r['model'],r['task_id'],r['repetition']) for r in rows]
        assert len(rows)==240 and len(set(keys))==240, (gpu,len(rows),len(set(keys)))
        successes=sum(int(r['success']) for r in rows)
        assert successes==expected[gpu]
        assert all(r['status']=='complete' for r in rows)
        assert canonical[gpu]['assignments']==240
        assert sum(m['successes'] for m in canonical[gpu]['models'].values())==successes
        all_keys[gpu]={k:r for k,r in zip(keys,rows)}
    assert set(all_keys['rtx3090'])==set(all_keys['rtx5090'])
    assert all(all_keys['rtx3090'][k]['seed']==all_keys['rtx5090'][k]['seed'] for k in all_keys['rtx3090'])
    paired=read_csv('paired-runs.csv')
    assert len(paired)==480
    assert len(read_csv('task-comparisons.csv'))==80
    assert len(read_csv('outcome-disagreements.csv'))==33
    p=read_json('paired-comparison.json')
    assert p['task_count']==40 and p['trials_per_model_per_gpu']==120
    assert p['overall_success']['rtx3090']['successes']==164
    assert p['overall_success']['rtx5090']['successes']==155
    assert p['task_level_agreement']['nemotron']['exact_outcome_agreement'] + p['task_level_agreement']['qwen']['exact_outcome_agreement']==207
    print('PASS: 480 assignments (240/GPU), 120/model/GPU; exact task/repetition/seed parity; 319 successes; 207/240 agreement; 33 assignment disagreements.')
if __name__=='__main__': main()
