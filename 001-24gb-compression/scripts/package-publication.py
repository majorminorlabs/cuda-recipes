#!/usr/bin/env python3
"""Build an explicit-allowlist archive containing only corrected paired-study materials."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'publication/nemotron-compression-publication.zip'
FILES=[
 'README.md','NOTICE.md','docs/REPRODUCE_PHASE2.md',
 'benchmark/tasks.json','benchmark/scoring.json','benchmark/config.json','benchmark/schedule.json','benchmark/freeze.json',
 'benchmark/make_suite.py','benchmark/make_schedule.py',
 'benchmark/rtx3090_v1/config.json','benchmark/rtx3090_v1/freeze.json','benchmark/rtx3090_v1/freeze.py',
 'benchmark/rtx5090_v1/config.json','benchmark/rtx5090_v1/execution-budget.json','benchmark/rtx5090_v1/freeze.json','benchmark/rtx5090_v1/freeze.py',
 'models/manifest.json','manifests/hardware.json','manifests/environment.json','manifests/rtx3090-public.json','manifests/rtx5090-corrected-public.json','manifests/llama-cpp.json',
 'src/__init__.py','src/freeze.py','src/run.py','src/run_v2.py','src/tools.py','src/validate.py','src/verify_freeze.py',
 'tests/test_benchmark.py','tests/test_run_v2_reasoning_history.py','tests/test_run_v2_telemetry.py',
 'scripts/analyze-rtx3090-rerun.py','scripts/build-llama-cpp.sh','scripts/download-models.sh','scripts/analyze-corrected-hardware-comparison.py','scripts/render-hardware-comparison-report.py','scripts/run-llama-server.sh','scripts/package-publication.py','scripts/summarize-paid-efficiency.py',
 'results/phase2_rtx3090/canonical-results.json','results/phase2_rtx3090/canonical-runs.csv','results/phase2_rtx3090/canonical-tasks.csv','results/phase2_rtx3090/category-success.svg','results/phase2_rtx3090/completion-time.svg','results/phase2_rtx3090/validation.json',
 'results/phase2_rtx5090_corrected/canonical-results.json','results/phase2_rtx5090_corrected/canonical-runs.csv','results/phase2_rtx5090_corrected/canonical-tasks.csv','results/phase2_rtx5090_corrected/validation.json',
 'results/phase2_hardware_comparison/canonical-results.json','results/phase2_hardware_comparison/paired-runs.csv','results/phase2_hardware_comparison/task-comparisons.csv','results/phase2_hardware_comparison/outcome-disagreements.csv','results/phase2_hardware_comparison/success-by-category.svg','results/phase2_hardware_comparison/completion-latency.svg','results/phase2_hardware_comparison/phase2-hardware-success.svg','results/phase2_hardware_comparison/phase2-hardware-latency.svg','results/phase2_hardware_comparison/validation.json','results/phase2_hardware_comparison/research-report.md',
 'publication/README.md','publication/research-report.md','publication/corrected-hardware-success.svg','publication/corrected-hardware-latency.svg',
]
def main():
 missing=[x for x in FILES if not (ROOT/x).is_file()]
 if missing: raise SystemExit('missing package input(s): '+', '.join(missing))
 sums=''.join(f'{hashlib.sha256((ROOT/x).read_bytes()).hexdigest()}  {x}\n' for x in FILES)
 manifest=ROOT/'publication/CONTENTS.sha256'; manifest.write_text(sums)
 with ZipFile(OUTPUT,'w',ZIP_DEFLATED,compresslevel=9) as z:
  for x in FILES:z.write(ROOT/x,arcname=x)
  z.write(manifest,arcname='publication/CONTENTS.sha256')
 (ROOT/'publication/SHA256SUMS').write_text(f"{hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}  publication/nemotron-compression-publication.zip\n")
 print(f'Wrote {OUTPUT} with {len(FILES)} allowlisted files')
if __name__=='__main__':main()
