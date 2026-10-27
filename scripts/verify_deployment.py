import json,pickle,subprocess,math,random,time
import numpy as np
from guest import Guest,R
from run_study import features,score
models=pickle.loads((R/'results/models.pkl').read_bytes())
def predict(kind,f):
 m=models[kind];v=np.array(f);bounds=m['bounds'];span=np.maximum(bounds[1]-bounds[0],.01)
 ood=not np.all(np.isfinite(v)) or bool(np.any(v<bounds[0]-.25*span)|np.any(v>bounds[1]+.25*span))
 return (*m['default'],1) if ood else (*m['space'][int(m['tree'].predict(v.reshape(1,-1))[0])],0)
def parse(line):return {k:int(v) for k,v in (x.split('=',1) for x in line.split()[1:])}
checks=[]
for row in json.loads((R/'results/test_results.json').read_text()):
 if row['method']!='context':continue
 kind=row['kind'];f=row['features'];got=tuple(map(int,subprocess.check_output([str(R/'build/model_cli'),'0' if kind=='S' else '1',*map(str,f)],text=True).split()))
 assert got==predict(kind,f),(got,predict(kind,f));checks.append(dict(kind=kind,features=f,prediction=got))
for kind in ['S','M']:
 for f in [[math.nan]*5,[math.inf]*5,[-1e10]*5,[1e10]*5]:
  got=tuple(map(int,subprocess.check_output([str(R/'build/model_cli'),'0' if kind=='S' else '1',*map(str,f)],text=True).split()));assert got==predict(kind,f);checks.append(dict(kind=kind,features=[str(x) for x in f],prediction=got))
closed=[];repro=[]
with Guest('deployed_model') as g:
 for kind,contexts in [('S',[[2,1],[8,8],[16,10],[6,3],[10,6],[18,8]]),('M',[[2000,0],[4000,1],[4000,2],[6000,0],[6000,1],[6000,3]])]:
  for ci,context in enumerate(contexts):
   for rep in range(5):
    seed=70000+ci*100+rep;pilotSeed=80000+ci*100+rep
    g.p.stdin.write(f"{'A' if kind=='S' else 'B'} {seed} {context[0]} {context[1]} {pilotSeed} 0 1\n".encode());g.p.stdin.flush()
    lines=g.read_until('MID_READY',30);rec=parse(next(x for x in lines if x.startswith('MID_RECOMMEND')))
    vals=[parse(x) for x in lines if x.startswith('MID_SCHED ' if kind=='S' else 'MID_MEMORY ')]
    assert len(vals)==2
    pilot,actual=vals;f=features(kind,context,pilot);expected=predict(kind,f)
    assert (rec['a'],rec['b'],rec['fallback'])==expected,(kind,context,rec,expected)
    assert actual.get('q',actual.get('minalloc'))==rec['a']
    assert actual.get('floor',actual.get('split'))==rec['b']
    default=models[kind]['default'];base=g.evaluate(kind,seed,*context,*default)
    if kind=='M':assert actual['corrupt']==actual['integrity']==actual['deinit']==actual['restored_used']==0
    closed.append(dict(kind=kind,context=context,rep=rep,pilot=pilot,recommendation=rec,actual=actual,default=base,score=score(kind,actual),default_score=score(kind,base),pilot_score=score(kind,pilot)))
   print('Verified guest model',kind,context,flush=True)
 # Repeat across identical workloads while retaining timer-phase variability.
 for kind,context,default in [('S',[8,5],[20000,50]),('M',[4000,1],[8,0])]:
  for rep in range(5):repro.append(dict(kind=kind,rep=rep,measurement=g.evaluate(kind,90001,*context,*default)))
(R/'results/model_consistency.json').write_text(json.dumps({'case_count':len(checks),'cases':checks},indent=2))
(R/'results/closed_loop.json').write_text(json.dumps(closed,indent=2))
(R/'results/repeatability.json').write_text(json.dumps(repro,indent=2))
print('Verified',len(checks),'host model cases and',len(closed),'actual-kernel closed loops')
