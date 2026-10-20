#!/usr/bin/env bash
set -euo pipefail
cd /workspace/005
python3 -m pip install --break-system-packages -U 'huggingface_hub[hf_xet]' > logs/hf_install.log 2>&1
REV=$(curl -fsSL https://huggingface.co/api/models/unsloth/Ornith-1.5-122B-GGUF | jq -r .sha)
test -n "$REV" && test "$REV" != null
printf '%s\n' "$REV" > receipts/unsloth_rev.txt
mkdir -p /workspace/models
(time hf download unsloth/Ornith-1.5-122B-GGUF --revision "$REV" --include 'UD-Q4_K_XL/*' --local-dir /workspace/models) > logs/dl_q4.log 2>&1
(time hf download unsloth/Ornith-1.5-122B-GGUF --revision "$REV" --include 'UD-Q3_K_XL/*' --local-dir /workspace/models) > logs/dl_q3.log 2>&1
for q in UD-Q4_K_XL UD-Q3_K_XL; do
  curl -fsSL "https://huggingface.co/api/models/unsloth/Ornith-1.5-122B-GGUF/tree/$REV/$q" | jq -r '.[]|select(.lfs)|"\(.lfs.oid)  \(.path)"' >> receipts/expected_sha256.txt
done
sha256sum /workspace/models/UD-Q*/*.gguf > receipts/actual_sha256.txt
python3 - <<'PY'
from pathlib import Path
expected = {line.split(None, 1)[1].split('/')[-1]: line.split()[0] for line in Path('receipts/expected_sha256.txt').read_text().splitlines() if line.strip()}
actual = {line.split(None, 1)[1].split('/')[-1]: line.split()[0] for line in Path('receipts/actual_sha256.txt').read_text().splitlines() if line.strip()}
missing = sorted(expected.keys() - actual.keys())
extra = sorted(actual.keys() - expected.keys())
mismatch = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
Path('receipts/hash_check.txt').write_text(f'missing={missing}\nextra={extra}\nmismatch={mismatch}\n')
if missing or mismatch:
    raise SystemExit('STOP: quant file hash mismatch or missing files')
PY
