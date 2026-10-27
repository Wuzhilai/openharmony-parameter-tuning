"""Short automatic-parameter demonstration using the immutable deployed image."""
from pathlib import Path
import shutil
import guest
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'audit/rerun/demo'
for name in ['build','evidence']:(OUT/name).mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'images/deployment/OHOS_Image',OUT/'build/OHOS_Image')
guest.R=OUT
with guest.Guest('demo') as g:
    for command in ['A 50000 8 8 40000 0 1\n','B 50000 4000 1 40000 0 1\n']:
        print('COMMAND',command.strip())
        g.p.stdin.write(command.encode());g.p.stdin.flush()
        for line in g.read_until('MID_READY'):
            if line.startswith(('MID_SCHED','MID_MEMORY','MID_RECOMMEND','MID_ERROR','MID_READY')):print(line)
