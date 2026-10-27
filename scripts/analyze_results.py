import json,collections,statistics,math,csv
import numpy as np
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from guest import R
O=R/'results';F=R/'figures';F.mkdir(exist_ok=True)
rows=json.loads((O/'test_results.json').read_text());summary=[]
for kind in ['S','M']:
 contexts=sorted({tuple(x['context']) for x in rows if x['kind']==kind})
 for context in contexts:
  selected=[x for x in rows if x['kind']==kind and tuple(x['context'])==context]
  baseline={x['rep']:x for x in selected if x['method']=='default'}
  for method in ['default','heuristic','random','bo','context']:
   a=sorted([x for x in selected if x['method']==method],key=lambda x:x['rep']);improvement=[100*(baseline[x['rep']]['score']-x['score'])/baseline[x['rep']]['score'] for x in a]
   mean=statistics.mean(improvement);half=float(t.ppf(.975,len(a)-1))*statistics.stdev(improvement)/math.sqrt(len(a))
   summary.append(dict(kind=kind,context=str(context),method=method,n=len(a),score=statistics.mean(x['score'] for x in a),improvement_pct=mean,ci_low=mean-half,ci_high=mean+half,fallbacks=sum(x['ood'] for x in a) if method=='context' else 0))
with (O/'summary.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=summary[0].keys());w.writeheader();w.writerows(summary)
(O/'summary.json').write_text(json.dumps(summary,indent=2))
for kind,title in [('S','Actual LiteOS-M scheduler'),('M','Actual LiteOS-M TLSF allocator')]:
 a=[x for x in summary if x['kind']==kind and x['method']=='context'];b=[x for x in summary if x['kind']==kind and x['method']=='bo']
 fig,ax=plt.subplots(figsize=(8.5,4.7));y=np.arange(len(a));ax.axvline(0,color='#777777',linewidth=.8)
 for group,off,color,label in [(a,-.12,'#205875','Context model'),(b,.12,'#A96330','Global BO selection')]:
  ax.errorbar([x['improvement_pct'] for x in group],y+off,xerr=np.array([[x['improvement_pct']-x['ci_low'] for x in group],[x['ci_high']-x['improvement_pct'] for x in group]]),fmt='o',capsize=3,color=color,label=label)
 ax.set_yticks(y,[x['context'] for x in a]);ax.set_xlabel('Paired score reduction vs default (%) with 95% t interval');ax.set_ylabel('Workload input context');ax.set_title(title+' on QEMU');ax.legend();ax.grid(axis='x',alpha=.2);fig.tight_layout()
 fig.savefig(F/(kind+'_paired_results.png'),dpi=180);fig.savefig(F/(kind+'_paired_results.svg'));plt.close(fig)
trace=json.loads((O/'search_trace.json').read_text());fig,axes=plt.subplots(1,2,figsize=(10,4))
for ax,kind in zip(axes,['S','M']):
 for method,color in [('random','#A96330'),('bo','#205875')]:
  curves=[]
  groups=collections.defaultdict(list)
  for x in trace:
   if x['kind']==kind and x['method']==method:groups[(tuple(x['context']),x['rep'])].append(x)
  for values in groups.values():
   values.sort(key=lambda x:x['step']);base=values[0]['best_score'];curves.append([x['best_score']/base for x in values])
  ax.plot(range(1,9),np.mean(curves,axis=0),marker='o',label=method,color=color)
 ax.set_title('Scheduler' if kind=='S' else 'Memory');ax.set_xlabel('Candidate evaluations (2 guest runs each)');ax.set_ylabel('Training best / default');ax.legend();ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(F/'search_curves.png',dpi=180);fig.savefig(F/'search_curves.svg');plt.close(fig)
over=json.loads((O/'probe_overhead.json').read_text());over_summary={}
for kind in ['S','M']:
 pairs={}
 for x in over:
  if x['kind']==kind:pairs.setdefault(x['seed'],{})[x['probes']]=x
 rates=[100*(v[1]['elapsed']-v[0]['elapsed'])/v[0]['elapsed'] for v in pairs.values()]
 over_summary[kind]={'mean_elapsed_overhead_pct':statistics.mean(rates),'min_pct':min(rates),'max_pct':max(rates),'n':len(rates)}
(O/'probe_summary.json').write_text(json.dumps(over_summary,indent=2))
print(json.dumps({'context_results':[x for x in summary if x['method']=='context'],'probe_overhead':over_summary},indent=2))
