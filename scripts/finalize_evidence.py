from pathlib import Path
import json,hashlib,shutil,csv
from guest import R
# Keep a complete final-session transcript; earlier development sessions remain outside the package.
for name in ['main_study','deployed_model','protocol_smoke']:
 p=R/'evidence'/f'{name}.serial.log'
 if p.exists():
  content=p.read_bytes();start=content.rfind(b'MID_BOOT OpenHarmony')
  assert start>=0
  (R/'evidence'/f'{name}_final.serial.log').write_bytes(content[start:])
snap=R/'images/deployment';snap.mkdir(parents=True,exist_ok=True)
for name in ['OHOS_Image','build_manifest.json','kernel.map','target_config.h']:shutil.copy2(R/'build'/name,snap/name)
(snap/'product').mkdir(exist_ok=True)
for p in (R/'product').iterdir():
 if p.is_file():shutil.copy2(p,snap/'product'/p.name)
rows=[json.loads(x) for x in (R/'results/measurements.jsonl').read_text().splitlines()]
for kind in ['S','M']:
 selected=[r for r in rows if r['kind']==kind];fields=list(dict.fromkeys(k for r in selected for k in r))
 with (R/'results'/f'measurements_{kind}.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in selected:w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})
print('Saved canonical raw transcripts, deployment snapshot and CSV data')
