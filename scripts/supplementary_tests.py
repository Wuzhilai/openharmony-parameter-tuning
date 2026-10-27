"""Feature ablation and controlled guest restart; disjoint supplementary seeds."""
import json,pickle,subprocess
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from guest import Guest,R
from run_study import features,score
models=pickle.loads((R/'results/models.pkl').read_bytes());rows=[json.loads(x) for x in (R/'results/measurements.jsonl').read_text().splitlines()]
selected=json.loads((R/'results/selections.json').read_text());out=[]
with Guest('supplementary') as g:
 for kind in ['S','M']:
  m=models[kind];x=[];y=[]
  for r in rows:
   if r['kind']==kind and r['stage']=='pilot_train':
    label=next(v['param'] for v in selected if v['kind']==kind and v['context']==r['context'] and v['rep']==r['rep'] and v['method']=='bo')
    x.append(features(kind,r['context'],r));y.append(m['space'].index(tuple(label)))
  x=np.array(x);y=np.array(y);trees={}
  for name,cols in [('input_only',[0,1]),('state_only',[2,3,4])]:trees[name]=(DecisionTreeClassifier(max_depth=3,min_samples_leaf=2,random_state=42).fit(x[:,cols],y),cols)
  contexts=[[4,3],[10,5],[16,8]] if kind=='S' else [[2500,0],[3500,1],[4500,2]]
  for ci,c in enumerate(contexts):
   for rep in range(5):
    pilot=g.evaluate(kind,91000+ci*100+rep,*c,*m['default']);f=np.array(features(kind,c,pilot));span=np.maximum(m['bounds'][1]-m['bounds'][0],.01)
    ood=bool(np.any(f<m['bounds'][0]-.25*span)|np.any(f>m['bounds'][1]+.25*span))
    for name in ['default','full','input_only','state_only']:
     if name=='default' or ood:param=m['default']
     elif name=='full':param=m['space'][int(m['tree'].predict(f.reshape(1,-1))[0])]
     else:tree,cols=trees[name];param=m['space'][int(tree.predict(f[cols].reshape(1,-1))[0])]
     got=g.evaluate(kind,92000+ci*100+rep,*c,*param);got.update(kind=kind,context=c,rep=rep,method=name,score=score(kind,got),features=f.tolist(),ood=ood);out.append(got)
 # Confirm invalid input leaves subsequent valid workloads operable.
 rejects=[]
 for cmd in ['X 1 2 3 4 5 1\n','S 1 1 2 1000 50 1\n','M 1 1000 4 8 0 1\n','A 1 30 2 123 0 1\n','B 1 1000 8 123 0 1\n','garbage\n']:
  g.p.stdin.write(cmd.encode());g.p.stdin.flush();lines=g.read_until('MID_READY');assert any('MID_ERROR' in x for x in lines);rejects.append({'command':cmd.strip(),'response':lines})
 recovered=g.evaluate('M',93000,1000,0,8,0)
# Simulate a terminated guest and verify restoration from the same immutable image.
g=Guest('forced_restart_before');g.p.kill();g.close()
with Guest('forced_restart_after') as g:
 after=g.evaluate('S',94000,8,5,20000,50);memory=g.evaluate('M',94000,2000,1,8,0)
(R/'results/ablations.json').write_text(json.dumps(out,indent=2))
(R/'results/robustness.json').write_text(json.dumps({'rejections':rejects,'recovered':recovered,'forced_guest_restart':{'scheduler':after,'memory':memory},'scope':'Parameter boundary rejection, transport recovery and isolated process restart. Not kernel fault injection or production safety certification.'},indent=2))
print('Completed',len(out),'actual-kernel feature-ablation measurements, six rejections, and guest restart')
