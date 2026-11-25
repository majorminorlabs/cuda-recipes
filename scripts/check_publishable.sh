#!/bin/sh
# Check staged paths and content before committing. Install with:
# git config core.hooksPath .githooks
set -eu
cd "$(git rev-parse --show-toplevel)"
exec python3 - <<'PY'
import re
import subprocess
import sys

# Read reviewed research-data exceptions from the index, so unstaged edits
# cannot silently change what this commit allows.
entry = subprocess.run(
    ['git', 'show', ':scripts/publishable-data-paths.txt'],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
)
allowed = set(entry.stdout.splitlines()) if entry.returncode == 0 else set()
paths = subprocess.check_output([
    'git', 'diff', '--cached', '--name-only', '--diff-filter=ACMRT', '-z',
]).decode('utf-8', errors='surrogateescape').split('\0')
operational = re.compile(
    r'(?i)(?:^|/)(?:social|_internal|responses|scratch|preview|dist|build|__pycache__)(?:/|$)'
    r'|_internal|' + 'hand' + 'off|' + r'social[-_]drafts|(?:^|/)[^/]*(?:og[-_]share|x[-_]share|reddit[-_]share)[^/]*$'
    r'|\.pyc$'
)
# ARTICLE.md / ARTICLE-METADATA.json and *-METADATA.json belong on the site.
# Keep case-sensitive *-METADATA.json consistent with .gitignore; lowercase
# run-metadata.json files remain frozen scientific run records.
article_files = re.compile(r'(?i)(?:^|/)ARTICLE(?:\.md|-METADATA\.json)$')
publication_metadata = re.compile(r'(?:^|/)[^/]+-METADATA\.json$')
data_names = re.compile(r'(?i)prompt|responses')
allowed_article_sources = {'005-ornith-122b-offload/ARTICLE.md', '006-edge0-145b/ARTICLE.md'}
blocked = [path for path in paths if path and (
    operational.search(path)
    or (article_files.search(path) and path not in allowed_article_sources)
    or publication_metadata.search(path)
    or (data_names.search(path) and path not in allowed)
)]
if blocked:
    print('Commit rejected: staged files that belong outside research repositories:', file=sys.stderr)
    for path in blocked:
        print('  ' + path, file=sys.stderr)
    print('Keep publication assets on the site. Review scientific-data exceptions explicitly.', file=sys.stderr)
    sys.exit(1)

# Scan staged file content without ever printing matching text (which could
# expose a credential in hook output). Binary files are skipped.
patterns = {
    'credential/token': re.compile(rb'(?i)(?:sk-[A-Za-z0-9_-]{20,}|(?:gh[pousr])_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{16,}|AKIA[0-9A-Z]{16}|(?:[A-Z0-9_]*(?:API_?KEY|ACCESS_TOKEN|SECRET|TOKEN|AUTHKEY|KEY)\s*[:=]\s*[^\s]{8,}|Bearer\s+[A-Za-z0-9._~+/-]{16,}))'),
    'private path': re.compile(rb'(?i)(?:/' + b'Vol' + b'umes/|/' + b'Us' + b'ers/|/' + b'ho' + b'me/[^\s]+)'),
    'private marker': re.compile(rb'(?i)\b(?:' + b'in' + b'ternal|' + b'hand' + b'off)\b'),
    'pod identifier': re.compile(rb'(?i)\bpod[_ -]?id\b\s*[:=]?\s*[a-z0-9][a-z0-9-]{7,}'),
    'IP address': re.compile(rb'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])'),
    'IPv6 address': re.compile(rb'(?i)(?<![0-9a-f:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:]{0,4}(?![0-9a-f:])'),
    'email address': re.compile(rb'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'),
}
content_failures = []
for path in paths:
    if not path:
        continue
    item = subprocess.run(['git', 'show', ':' + path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if item.returncode:
        continue
    data = item.stdout
    if b'\0' in data[:8192]:
        continue
    for category, pattern in patterns.items():
        matches = pattern.findall(data)
        if category == 'IPv6 address': matches = [m for m in matches if m != b'::']
        if matches:
            content_failures.append((path, category))
if content_failures:
    print('Commit rejected: staged content contains private identifiers or sensitive markers:', file=sys.stderr)
    for path, category in content_failures:
        print(f'  {path}: {category}', file=sys.stderr)
    sys.exit(1)
print('PASS: staged paths and content are publishable.')
PY
