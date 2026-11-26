"""Verify frozen tasks, paired assignments, scores, metrics, and release hashes."""
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'suite'))
from src.validate import validate, score, strict_json_loads

def read(name):
    return json.loads((ROOT / name).read_text())

def main():
    validate()
    tasks = {t['id']: t for t in read('suite/DATA/tasks.json')}
    schedule = read('suite/schedule-paired.json')['trials']
    assert len(schedule) == 240
    expected = {}
    for i in range(0, len(schedule), 2):
        a, b = schedule[i:i+2]
        assert {a['model'], b['model']} == {'base', 'adapter'}
        assert all(a[k] == b[k] for k in ('task_id', 'repetition', 'seed'))
        for row in (a, b):
            tid = f"{row['model']}:{row['task_id']}:{row['repetition']}"
            assert tid not in expected
            expected[tid] = row
    rows = read('DATA/trials.json')
    assert len(rows) == len({r['trial_id'] for r in rows}) == 240
    assert {r['trial_id'] for r in rows} == set(expected)
    summary = read('DATA/summary.json')
    evidence = list((ROOT / 'evidence').glob('*.json'))
    assert len(evidence) == 240
    for r in rows:
        tid = r['trial_id']; assignment = expected[tid]
        assert r['status'] == 'complete'
        assert all(r[k] == assignment[k] for k in ('model', 'task_id', 'repetition', 'seed'))
        d = read('evidence/' + tid.replace(':', '_') + '.json')
        assert d['trial'] == assignment
        assert d['task'] == tasks[r['task_id']]
        try:
            parsed = strict_json_loads(d['content'])
            result = int(score(d['task'], parsed, d['tool_trace'] if d['task'].get('expected_calls') is not None else None))
        except (ValueError, TypeError):
            result = 0
        if d['finish_reason'] in ('length', 'max_tool_turns'):
            result = 0
        assert result == d['success'] == r['success'], tid
        assert d['failure_class'] == r['failure_class']
        assert d['usage']['completion_tokens'] == r['completion_tokens']
        assert d['usage']['prompt_tokens'] == r['prompt_tokens']
        assert math.isclose(d['interaction']['decode_tps'], r['decode_tps'])
        assert math.isclose(d['interaction']['prompt_tps'], r['prompt_tps'])
    for arm in ('base', 'adapter'):
        selected = [r for r in rows if r['model'] == arm]
        assert len(selected) == summary['counts'][arm]['trials'] == 120
        assert sum(r['success'] for r in selected) == summary['counts'][arm]['successes']
        assert summary['counts'][arm]['errors'] == 0
        failure = collections.Counter(r['failure_class'] for r in selected if not r['success'])
        assert dict(failure) == summary['failures'][arm]
        for category, cell in summary['categories'][arm].items():
            group = [r for r in selected if tasks[r['task_id']]['category'] == category]
            assert len(group) == cell['n']
            assert sum(r['success'] for r in group) == cell['successes']
        for col, metric in (('wall_s', 'wall_s'), ('decode_tps', 'decode_tok_s'), ('prompt_tps', 'prompt_tok_s'), ('peak_vram_mib','peak_vram_mib'), ('peak_ram_kib','peak_ram_kib')):
            values = [r[col] for r in selected]
            for key, function in (('mean', statistics.mean), ('median',statistics.median), ('max',max)):
                assert math.isclose(function(values), summary['speed'][arm][metric][key], rel_tol=1e-9)
        assert math.isclose(sum(r['wall_s'] for r in selected), summary['speed'][arm]['total_trial_wall_s'])
        ttft = [r['ttft_ms'] for r in read('DATA/ttft.json') if r['arm'] == arm]
        assert len(ttft) == 3
        assert math.isclose(statistics.median(ttft),summary['ttft_ms'][arm])
    paired = collections.Counter()
    by_id = {r['trial_id']:r for r in rows}
    for a in (schedule[i] for i in range(0, len(schedule), 2)):
        suffix = f"{a['task_id']}:{a['repetition']}"
        b, l = (by_id[f'{arm}:{suffix}']['success'] for arm in ('base','adapter'))
        paired['both_pass' if b and l else 'both_fail' if not b and not l else 'base_only_pass' if b else 'adapter_only_pass'] += 1
    assert dict(paired) == {k:v for k,v in summary['paired'].items() if k != 'pairs'}
    assert sum(paired.values()) == summary['paired']['pairs'] == 120
    for line in (ROOT/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ',1)
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    print('PASS: 240 assignments and re-scored outputs; category, paired, timing, memory and checksum checks')

if __name__ == '__main__':
    main()
