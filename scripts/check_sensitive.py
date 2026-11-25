#!/usr/bin/env python3
"""Check index blobs and proposed commit history before publication."""
import gzip,hashlib,ipaddress,json,pathlib,re,subprocess,sys

def git(*args,check=True):
    return subprocess.run(['git',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=check).stdout

RULES={
 'machine path':re.compile(rb'/(?:Volu[m]es|Use[r]s)/'),
 'private marker':re.compile(rb'_arti[f]acts|_inter[n]al'),
 'personal email':re.compile(rb'(?i)[a-z0-9_.+-]+@(?:gmail|hotmail|outlook|yahoo|icloud)\.[a-z.]+'),
 'provider wording':re.compile(rb'(?i)\brun[p]od\b|\brent[e]d\b'),
 'personal detail':re.compile(rb'(?i)\bdi[p]po\b|\bevoof[f]ice\b'),
 'credential':re.compile(rb'(?:s[k]-[A-Za-z0-9_-]{16,}|h[f]_[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKI[A][A-Z0-9]{16}|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----)'),
 'credential assignment':re.compile(rb'''(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key)["\x27 \t]*[:=][ \t]*["\x27]([A-Za-z0-9_./+=-]{24,})["\x27]'''),
 'SSH public identity':re.compile(rb'ssh-(?:ed25519|rsa) AAAA[A-Za-z0-9+/=]{30,}'),
 'allocation identifier':re.compile(rb'(?i)(?:pod|droplet)[ _-]?(?:id)?[\s"\x27:=]+["\x27]?(?:[a-z0-9]{13}|[0-9]{8,12})\b'),
}
IP=re.compile(rb'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?![\w.])')
PATH=re.compile(r'(?i)(?:^|/)(?:_pri[v]ate|_inter[n]al|responses)(?:/|$)|hand[o]ff|\.(?:pem|key)$|(?:^|/)config\.env$')

def reasons(data):
    if data.startswith(b'\x1f\x8b'):
        try:data=gzip.decompress(data)
        except Exception:return ['unreadable compressed evidence']
    if b'\0' in data:return []
    found=[name for name,p in RULES.items() if p.search(data)]
    for m in IP.finditer(data):
        before=data[max(0,m.start()-32):m.start()];after=data[m.end():m.end()+22]
        # The logger can concatenate records without a newline between timestamps.
        if re.match(rb' [DIWEF] ',after):continue
        if before.endswith((b'==',b'v')):continue
        if re.search(rb"(?i)\bversion\s*=\s*[\"']$",before):continue
        value=m[0].split(b':')[0].decode()
        try:address=ipaddress.ip_address(value)
        except ValueError:continue
        if address.is_loopback or address.is_unspecified or address in ipaddress.ip_network('192.0.2.0/24'):continue
        found.append('network address');break
    return sorted(set(found))

def exceptions(ref):
    result=git('show',ref+':scripts/reviewed-content.json',check=False)
    try:return json.loads(result)
    except (ValueError,TypeError):return {}

def scan_blob(path,blob,allow,cache,failures,label):
    if PATH.search(path):failures.add((label,path,'private path'))
    if blob not in cache:
        data=git('cat-file','blob',blob)
        cache[blob]=(hashlib.sha256(data).hexdigest(),reasons(data))
    digest,issues=cache[blob]
    item=allow.get(path,{})
    if isinstance(item,list):item=next((x for x in item if x.get('sha256')==digest),{})
    if item.get('sha256')==digest:
        issues=[x for x in issues if x not in item.get('allowed_rules',[])]
    for issue in issues:failures.add((label,path,issue))

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'staged';failures=set();cache={};seen=set();commits=set()
    if mode=='staged':
        allow=exceptions('')
        paths=git('diff','--cached','--name-only','--diff-filter=ACMRT','-z').decode(errors='surrogateescape').split('\0')
        for path in filter(None,paths):
            blob=git('rev-parse',':'+path).decode().strip()
            scan_blob(path,blob,allow,cache,failures,'index')
    else:
        if mode=='history':commits=set(git('rev-list','--all').decode().split())
        elif mode=='push':
            push_allow={}
            for line in sys.stdin:
                local_ref,local,remote_ref,remote=line.split()
                if set(local)=={'0'}:continue
                git('cat-file','-e',local+'^{commit}')
                push_allow.update(exceptions(local))
                known=bool(set(remote)!={'0'} and subprocess.run(['git','cat-file','-e',remote+'^{commit}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0)
                args=[local]+(['^'+remote] if known else [])
                commits.update(git('rev-list',*args).decode().split())
        else:raise SystemExit('Expected staged, history or push')
        for commit in sorted(commits):
            allow=exceptions('') if mode=='history' else push_allow
            meta=git('show','-s','--format=%B%n%ae%n%ce',commit)
            for issue in reasons(meta):failures.add((commit,'commit metadata',issue))
            for entry in git('ls-tree','-rz','--full-tree',commit).split(b'\0'):
                if not entry:continue
                info,path=entry.split(b'\t',1);file_mode,kind,blob=info.decode().split()
                if kind!='blob':continue
                path=path.decode(errors='surrogateescape');key=(path,blob,json.dumps(allow.get(path),sort_keys=True))
                if key in seen:continue
                seen.add(key);scan_blob(path,blob,allow,cache,failures,commit)
    for label,path,issue in sorted(failures):print(f'BLOCK {label} {path}: {issue}')
    print(f'{"FAIL" if failures else "PASS"}: {mode}; {len(commits)} commits; {len(cache)} unique blobs; {len(failures)} findings')
    return bool(failures)
if __name__=='__main__':sys.exit(main())
