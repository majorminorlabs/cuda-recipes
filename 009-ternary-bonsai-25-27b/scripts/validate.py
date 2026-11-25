#!/usr/bin/env python3
import csv, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
summary=json.loads((root/'DATA/quality-summary.json').read_text())
assert summary['bonsai_plain']['assignments']==120
assert summary['bonsai_mtp']['assignments']==120
assert summary['bonsai_plain']['strict_success']==81
assert summary['bonsai_mtp']['strict_success']==79
with (root/'DATA/trials.csv').open(newline='') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==240, len(rows)
for arm in ('bonsai_plain','bonsai_mtp'):
    assert sum(r['model']==arm for r in rows)==120
models=json.loads((root/'models.json').read_text())['artifacts']
assert all(len(m['sha256'])==64 for m in models)
assert json.loads((root/'systems.json').read_text())['runtimes']
# Chart inputs must agree with the frozen quality summaries and benchmark evidence.
figure=json.loads((root/'CHARTS/figure-data.json').read_text())
plain=summary['bonsai_plain']; mtp=summary['bonsai_mtp']
for arm_name,figure_index in (('bonsai_plain',1),('bonsai_mtp',2)):
    arm=figure['quality']['arms'][figure_index]
    detail=summary[arm_name]
    assert sum(arm['successes'])==detail['strict_success']
    assert arm['strict_total']==detail['strict_success_fraction']
    assert arm['successes']==[detail['category_scores'][k]['successes'] for k in ('coding','terminal_system','tool_use','structured_data','multi_step')]
    assert arm['assignments']==[detail['category_scores'][k]['assignments'] for k in ('coding','terminal_system','tool_use','structured_data','multi_step')]
bench=json.loads((root/'evidence/benchmark-results.json').read_text())
for row in figure['speed']['rows']:
    runs=[r for r in bench if r['model_file']==row['model'] and r['build']==('prism-fork' if row['build']=='Prism fork' else 'stock-mainline') and r['depth'] is None]
    assert len(runs)==1, (row['label'],len(runs))
    measures={y['n_prompt']:y['avg_ts'] for y in runs[0]['results'] if y['n_prompt']}
    decode={y['n_gen']:y['avg_ts'] for y in runs[0]['results'] if y['n_gen']}
    assert measures[512]==row['pp512'] and decode[128]==row['tg128'], row['label']
for name in ('overview','quality-categories','speed-builds','filled-context','mtp-check'):
    assert (root/'CHARTS'/f'{name}.svg').is_file() and (root/'CHARTS'/f'{name}.png').is_file()
print('PASS: 240 Bonsai trials, quality categories, chart data, model digests, runtime manifest, and rendered assets are consistent.')
