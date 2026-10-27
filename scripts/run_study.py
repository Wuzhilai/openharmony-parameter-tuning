"""Sequential actual-kernel experiments; no analytic/synthetic response surface."""
from pathlib import Path
import json,itertools,random,time,statistics,math,csv,pickle,hashlib,shutil
import numpy as np
from scipy.special import ndtr
from sklearn.tree import DecisionTreeClassifier
from guest import Guest,R
PROTOCOL=json.loads((R/'protocol.json').read_text());OUT=R/'results';OUT.mkdir(exist_ok=True)
JOURNAL=OUT/'measurements.jsonl'
def score(kind,r):
 if kind=='S':return r['mean_turn']+.5*r['p95_response']
 return (r['elapsed']-r['probe_cycles'])/r['ops']+.0002*r['live_used']+5000*r['fails']/r['allocs']
def features(kind,context,p):
 if kind=='S':return [context[0],context[1],p['mean_turn']/1e6,p['p95_response']/1e6,p['switches']/100]
 return [context[0]/1000,p['requested']/p['allocs']/1000,p['allocs']/p['ops'],p['free']/131072,1-p['maxfree']/max(1,p['free'])]
def ei(xs,ys,candidates,space):
 x=np.array(xs,float);z=np.array(candidates,float);ranges=np.ptp(space,axis=0);x=(x-np.min(space,axis=0))/ranges;z=(z-np.min(space,axis=0))/ranges
 y=np.array(ys);y=(y-y.mean())/max(y.std(),1e-9)
 kernel=lambda a,b:np.exp(-.5*np.sum(((a[:,None,:]-b[None,:,:])/.35)**2,axis=2))
 k=kernel(x,x)+np.eye(len(x))*1e-5;c=kernel(z,x);mu=c@np.linalg.solve(k,y)
 sd=np.sqrt(np.maximum(1-np.sum(c*np.linalg.solve(k,c.T).T,axis=1),1e-12));imp=y.min()-mu-.01;u=imp/sd
 return imp*ndtr(u)+sd*np.exp(-u*u/2)/math.sqrt(2*math.pi)
class Study:
 def __init__(self):self.g=Guest('main_study');self.rows=[];self.f=JOURNAL.open('w');self.trace=[]
 def measure(self,kind,context,param,seed,stage,**meta):
  row=self.g.evaluate(kind,int(seed),*map(int,context),*map(int,param));row.update(kind=kind,stage=stage,context=list(context),parameters=list(param),score=score(kind,row),**meta)
  self.rows.append(row);self.f.write(json.dumps(row)+'\n');self.f.flush();return row
 def close(self):self.g.close();self.f.close()
 def search(self,kind,context,space,default,rep,method):
  randomizer=random.Random(110+rep);initial=[tuple(default)]+randomizer.sample([p for p in space if p!=tuple(default)],2)
  xs=[];ys=[]
  for step in range(8):
   available=[p for p in space if p not in xs]
   param=initial[step] if step<3 else randomizer.choice(available) if method=='random' else available[int(np.argmax(ei(xs,ys,available,np.array(space))))]
   # Same two training traces for each candidate and both search methods.
   values=[self.measure(kind,context,param,10000+rep*100+j,'train',method=method,rep=rep,step=step)['score'] for j in range(2)]
   xs.append(param);ys.append(statistics.mean(values));self.trace.append(dict(kind=kind,context=list(context),rep=rep,method=method,step=step+1,param=list(param),mean_score=ys[-1],best_score=min(ys)))
  i=int(np.argmin(ys));return xs[i],ys[i]

def main():
 snapshot=R/'images/study';snapshot.mkdir(parents=True,exist_ok=True)
 for name in ['OHOS_Image','build_manifest.json','kernel.map','target_config.h']:
  shutil.copy2(R/'build'/name,snapshot/name)
 (snapshot/'product').mkdir(exist_ok=True)
 for p in (R/'product').iterdir():
  if p.is_file():shutil.copy2(p,snapshot/'product'/p.name)
 start=time.monotonic();study=Study();models={};selections=[];tests=[]
 try:
  for kind,key in [('S','scheduler'),('M','memory')]:
   cfg=PROTOCOL[key];space=list(itertools.product(*cfg['space'].values()));default=cfg['default'];training=[];winners={'random':[],'bo':[]}
   for ci,context in enumerate(cfg['train_contexts']):
    for rep in range(5):
     pilot=study.measure(kind,context,default,20000+ci*100+rep,'pilot_train',rep=rep)
     win={}
     for method in ['random','bo']:
      param,value=study.search(kind,context,space,default,rep,method);win[method]=param;winners[method].append(param)
      selections.append(dict(kind=kind,context=context,rep=rep,method=method,param=param,training_score=value))
     training.append((features(kind,context,pilot),space.index(win['bo'])))
    print(f'Completed {kind} training context {context}; measurements={len(study.rows)}',flush=True)
   # Global non-context baseline selected using separate validation contexts/seeds.
   globals={}
   for method in ['random','bo']:
    candidates=sorted(set(winners[method]));validation=[]
    for param in candidates:
     vals=[]
     for context in cfg['validation_contexts']:
      for rep in range(3):
       seed=30000+rep;base=study.measure(kind,context,default,seed,'validation_default',method=method)
       got=study.measure(kind,context,param,seed,'validation',method=method)
       vals.append(got['score']/base['score'])
     validation.append(statistics.mean(vals))
    globals[method]=candidates[int(np.argmin(validation))]
   x=np.array([r[0] for r in training]);y=np.array([r[1] for r in training])
   tree=DecisionTreeClassifier(max_depth=3,min_samples_leaf=2,random_state=42).fit(x,y)
   bounds=np.array([x.min(axis=0),x.max(axis=0)])
   models[kind]=dict(tree=tree,space=space,bounds=bounds,globals=globals,default=tuple(default),feature_names=['n','scale','pilot_mean_turn_mcycle','pilot_p95_mcycle','pilot_switches_hundred'] if kind=='S' else ['operations_thousand','pilot_mean_request_kbyte','pilot_alloc_fraction','pilot_free_fraction','pilot_fragmentation'])
   for ci,context in enumerate(cfg['test_contexts']):
    for rep in range(10):
     pilot=study.measure(kind,context,default,40000+ci*100+rep,'pilot_test',rep=rep)
     f=np.array(features(kind,context,pilot));span=np.maximum(bounds[1]-bounds[0],.01)
     ood=bool(np.any(f<bounds[0]-.25*span)|np.any(f>bounds[1]+.25*span))
     context_param=tuple(default) if ood else space[int(tree.predict(f.reshape(1,-1))[0])]
     heuristic=(5000,50) if kind=='S' else (16,32)
     methods=[('default',default),('heuristic',heuristic),('random',globals['random']),('bo',globals['bo']),('context',context_param)]
     random.Random(900+ci*100+rep).shuffle(methods)
     for method,param in methods:
      row=study.measure(kind,context,param,50000+ci*100+rep,'test',method=method,rep=rep,ood=ood,features=f.tolist());tests.append(row)
    print(f'Completed {kind} test context {context}; measurements={len(study.rows)}',flush=True)
  # Probe overhead and repeated-run stability; do not mix with held-out testing.
  extra=[]
  for kind,context,param in [('S',[8,5],[20000,50]),('M',[4000,1],[8,0])]:
   for seed in range(60000,60010):
    for on in [0,1]:
     row=study.g.evaluate(kind,seed,*context,*param,on);row.update(kind=kind,stage='probe_overhead',score=score(kind,row));extra.append(row)
  (OUT/'probe_overhead.json').write_text(json.dumps(extra,indent=2))
  # Domain/CLI validation: unsafe values must be rejected without mutation or hang.
  for kind,args in [('S',[1,8,5,0,50]),('S',[1,8,5,20000,900]),('M',[1,1000,1,7,0]),('M',[1,1000,1,8,129])]:
   try:study.g.evaluate(kind,*args)
   except RuntimeError as exc:
    if 'invalid_' not in str(exc):raise
   else:raise AssertionError('Invalid parameters were accepted')
  (OUT/'validation_rejections.json').write_text(json.dumps({'rejected_cases':4,'guest_recovered':study.g.evaluate('M',777,1000,0,8,0)['integrity']==0},indent=2))
 finally:study.close()
 with (OUT/'models.pkl').open('wb') as f:pickle.dump(models,f)
 for name,value in [('search_trace',study.trace),('selections',selections),('test_results',tests)]:
  (OUT/(name+'.json')).write_text(json.dumps(value,indent=2))
 result={'measurements':len(study.rows),'tests':len(tests),'duration_seconds':time.monotonic()-start,'protocol_sha256':hashlib.sha256((R/'protocol.json').read_bytes()).hexdigest(),'image_sha256':hashlib.sha256((R/'build/OHOS_Image').read_bytes()).hexdigest()}
 (OUT/'study_manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
