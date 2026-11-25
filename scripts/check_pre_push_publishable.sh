#!/bin/sh
set -eu
cd "$(git rev-parse --show-toplevel)"
push_input=$(cat)
python3 - "$push_input" <<'PY'
import re, subprocess, sys

patterns = {
    'credential/token': re.compile(rb'(?i)(?:sk-[A-Za-z0-9_-]{20,}|(?:gh[pousr])_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{16,}|AKIA[0-9A-Z]{16}|(?:[A-Z0-9_]*(?:API_?KEY|ACCESS_TOKEN|SECRET|TOKEN|AUTHKEY|KEY)\s*[:=]\s*[^\s]{8,}|Bearer\s+[A-Za-z0-9._~+/-]{16,}))'),
    'private path': re.compile(rb'(?i)(?:/' + b'Vol' + b'umes/|/' + b'Us' + b'ers/|/' + b'ho' + b'me/[^\s]+)'),
    'private marker': re.compile(rb'(?i)\b(?:' + b'in' + b'ternal|' + b'hand' + b'off)\b'),
    'pod identifier': re.compile(rb'(?i)\bpod[_ -]?id\b\s*[:=]?\s*[a-z0-9][a-z0-9-]{7,}'),
    'IP address': re.compile(rb'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])'),
    'IPv6 address': re.compile(rb'(?i)(?<![0-9a-f:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:]{0,4}(?![0-9a-f:])'),
    'email address': re.compile(rb'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'),
}
bad=[]
def inspect(path, blob):
    if blob.returncode or b'\0' in blob.stdout[:8192]: return
    for category,pattern in patterns.items():
        matches=pattern.findall(blob.stdout)
        if category == 'IPv6 address': matches=[m for m in matches if m != b'::']
        if matches: bad.append((path,category))
# With the no-commit workflow, scan the staged branch payload as well.
staged=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=ACMRT','-z']).decode(errors='surrogateescape').split('\0')
for path in filter(None,staged):
    inspect(path,subprocess.run(['git','show',':'+path],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL))
has_outgoing=False
for line in sys.argv[1].splitlines():
    if not line.strip(): continue
    has_outgoing=True
    local_ref, local_sha, remote_ref, remote_sha = line.strip().split()
    if set(local_sha) == {'0'}:
        continue
    if set(remote_sha) == {'0'}:
        base = subprocess.run(['git','merge-base',local_sha,'origin/main'],capture_output=True,text=True)
        if base.returncode:
            parent=subprocess.run(['git','rev-parse',f'{local_sha}^'],capture_output=True,text=True)
            if parent.returncode:
                print(f'FAIL: cannot find review base for {local_ref}',file=sys.stderr); sys.exit(1)
            remote_sha=parent.stdout.strip()
        else:
            remote_sha=base.stdout.strip()
    changed=subprocess.check_output(['git','diff','--name-only','--diff-filter=ACMRT',remote_sha,local_sha,'-z']).decode(errors='surrogateescape').split('\0')
    for path in filter(None,changed):
        blob=subprocess.run(['git','show',f'{local_sha}:{path}'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        inspect(path,blob)
if bad:
    print('Push rejected: outgoing content contains private identifiers or sensitive markers:',file=sys.stderr)
    for path,category in bad: print(f'  {path}: {category}',file=sys.stderr)
    sys.exit(1)
if has_outgoing:
    print('PASS: staged and outgoing file contents are publishable.')
else:
    print('PASS: staged content is publishable; no commit exists for outgoing-diff scanning.')
PY
