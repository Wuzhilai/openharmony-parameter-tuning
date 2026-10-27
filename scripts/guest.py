"""Persistent QEMU guest transport. Raw serial transcript retained per session."""
from pathlib import Path
import subprocess,select,os,time,json
R=Path(__file__).resolve().parents[1]
class Guest:
 def __init__(self,name='guest'):
  self.command=['qemu-system-arm','-M','mps2-an386','-cpu','cortex-m4','-nographic','-monitor','none','-serial','stdio','-kernel',str(R/'build/OHOS_Image'),'-icount','shift=0,align=off,sleep=off']
  self.p=subprocess.Popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0)
  self.buffer=b'';self.log=(R/'evidence'/f'{name}.serial.log').open('ab');self.read_until('MID_READY',20)
 def read_until(self,token,timeout=20):
  end=time.monotonic()+timeout;lines=[]
  while time.monotonic()<end:
   while b'\n' in self.buffer:
    line,self.buffer=self.buffer.split(b'\n',1);s=line.decode(errors='replace').strip();lines.append(s)
    if token in s:return lines
   if self.p.poll() is not None:raise RuntimeError('Guest exited: '+str(self.p.returncode))
   ready,_,_=select.select([self.p.stdout],[],[],min(1,max(.01,end-time.monotonic())))
   if ready:
    data=os.read(self.p.stdout.fileno(),65536);self.log.write(data);self.log.flush();self.buffer+=data
  raise TimeoutError('Guest timeout waiting for '+token+'; recent '+repr(lines[-4:]))
 def evaluate(self,kind,seed,a,b,x,y,probes=1):
  command=f'{kind} {seed} {a} {b} {x} {y} {probes}\n';self.log.write(('HOST_SEND '+command).encode());self.log.flush()
  start=time.monotonic();self.p.stdin.write(command.encode());self.p.stdin.flush();lines=self.read_until('MID_READY',30)
  expected='MID_SCHED ' if kind=='S' else 'MID_MEMORY '
  results=[s for s in lines if s.startswith(expected)]
  if len(results)!=1:raise RuntimeError('Missing or ambiguous guest result: '+repr(lines[-8:]))
  row={k:int(v) for k,v in (part.split('=',1) for part in results[0].split()[1:])}
  row['host_seconds']=time.monotonic()-start
  if kind=='M' and (row['corrupt'] or row['integrity'] or row['deinit']):raise RuntimeError('Memory integrity failure: '+repr(row))
  return row
 def close(self):
  if self.p.poll() is None:self.p.terminate()
  try:self.p.wait(timeout=3)
  except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
  self.log.close()
 def __enter__(self):return self
 def __exit__(self,*exc):self.close()
if __name__=='__main__':
 with Guest('protocol_smoke') as g:
  results=[]
  for q in [1000,20000,40000]:results.append(g.evaluate('S',42,8,5,q,50))
  for x,y in [(8,0),(64,128)]:results.append(g.evaluate('M',42,2000,1,x,y))
 print(json.dumps(results,indent=2));(R/'results/protocol_smoke.json').write_text(json.dumps(results,indent=2))
