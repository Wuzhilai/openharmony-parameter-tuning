from pathlib import Path
import subprocess,json,time
ROOT=Path(__file__).resolve().parents[1]
cmd=['qemu-system-arm','-M','mps2-an386','-cpu','cortex-m4','-nographic','-monitor','none','-serial','stdio','-kernel',str(ROOT/'build/OHOS_Image'),'-icount','shift=0,align=off,sleep=off']
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
try:
 out,_=p.communicate(timeout=4)
except subprocess.TimeoutExpired:
 p.terminate();out,_=p.communicate(timeout=5)
text=out.decode(errors='replace');print(text)
(ROOT/'evidence/boot_smoke.log').write_text(text)
(ROOT/'evidence/qemu_command.json').write_text(json.dumps(cmd,indent=2))
if 'MID_BOOT_OK' not in text:raise SystemExit('Boot smoke failed; inspect raw log')
