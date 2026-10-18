#!/usr/bin/env python3
"""Add cgroup CPU and NUMA allocation details to the existing host capture."""
import json, pathlib, re, subprocess

root=pathlib.Path(__file__).resolve().parents[1]
path=root/"DATA"/"host.json"
h=json.loads(path.read_text())
def cmd(*args):
    try:return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=10).strip()
    except Exception:return ""
nproc=cmd("nproc")
cpu_max_path=pathlib.Path("/sys/fs/cgroup/cpu.max")
if cpu_max_path.exists():
    cpu_max=cpu_max_path.read_text().strip()
    q,p=cpu_max.split()[:2]
    quota=None if q=="max" else round(int(q)/int(p),3)
else:
    q=pathlib.Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    p=pathlib.Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if q.exists() and p.exists():
        qv,pv=int(q.read_text()),int(p.read_text())
        cpu_max=f"{qv} {pv} (cgroup v1 cpu.cfs_quota_us/cpu.cfs_period_us)"
        quota=None if qv < 0 else round(qv/pv,3)
    else:
        cpu_max="unavailable"
        quota=None
numa=cmd("numactl","--hardware")
if numa:
    m=re.search(r"available:\s*(\d+) nodes?",numa)
    nodes=int(m.group(1)) if m else None
    numa_lines=[x for x in numa.splitlines() if x.startswith(("available:","node "))]
else:
    lscpu=cmd("lscpu")
    m=re.search(r"NUMA node\(s\):\s*(\d+)",lscpu)
    nodes=int(m.group(1)) if m else None
    numa_lines=[x for x in lscpu.splitlines() if x.startswith("NUMA node")]
speed=None
dm=cmd("dmidecode","-t","memory")
if dm:
    vals=re.findall(r"Speed:\s*(\d+)\s+MT/s",dm)
    if vals:speed=max(map(int,vals))
h.update({"nproc":int(nproc) if nproc.isdigit() else None,"cpu_max":cpu_max,
          "cpu_quota_vcpus":quota,"numa_nodes":nodes,"numa_details":numa_lines,
          "ram_speed_mts":speed if speed is not None else h.get("ram_speed_mts")})
path.write_text(json.dumps(h,indent=2)+"\n")
print(json.dumps({k:h[k] for k in ("nproc","cpu_max","cpu_quota_vcpus","numa_nodes","ram_speed_mts","numa_details")},indent=2))
