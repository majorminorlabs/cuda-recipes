#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
for line in (root/'SHA256SUMS').read_text().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for model,total in [('edge0',16),('qwen',37),('raon',36)]:
    data=json.loads((root/f'DATA/quality/scores-{model}.json').read_text())
    assert len(data['rows'])==60
    assert len({r['item_id'] for r in data['rows']})==60
    assert sum(r['score'] for r in data['rows'])==data['total']['score']==total
    for cat,cell in data['categories'].items():
        rows=[r for r in data['rows'] if r['category']==cat]
        assert len(rows)==cell['items'] and sum(r['score'] for r in rows)==cell['score']
print('PASS: checksums, 180 scored items and category totals')
