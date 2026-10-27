"""Fetch exact locked upstream commits when source snapshots are not included."""
from pathlib import Path
import json,subprocess
R=Path(__file__).resolve().parents[1]
for name,entry in json.loads((R/'evidence/source_lock.json').read_text()).items():
 p=R/'research'/name
 if p.exists():
  print('Preserving existing source directory:',p);continue
 subprocess.run(['git','init',str(p)],check=True)
 subprocess.run(['git','-C',str(p),'remote','add','origin',entry['remote']],check=True)
 subprocess.run(['git','-C',str(p),'fetch','--depth','1','origin',entry['commit']],check=True)
 subprocess.run(['git','-C',str(p),'checkout','--detach','FETCH_HEAD'],check=True)
