"""Evidence-level technical audit; document visual checks are recorded separately."""
import json,hashlib,collections,math
from guest import R
def get(f):return json.loads((R/f).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks={};rows=[json.loads(x) for x in (R/'results/measurements.jsonl').read_text().splitlines()]
manifest=get('results/study_manifest.json');tests=get('results/test_results.json');trace=get('results/search_trace.json')
checks['measurement_count']=len(rows)==manifest['measurements']
checks['study_image']=digest(R/'images/study/OHOS_Image')==manifest['image_sha256']
checks['protocol_hash']=digest(R/'protocol.json')==manifest['protocol_sha256']
checks['deployment_image']=digest(R/'images/deployment/OHOS_Image')==get('images/deployment/build_manifest.json')['image_sha256']
checks['deployment_sources_match']=all((R/p).is_file() and digest(R/p)==expected for p,expected in get('images/deployment/build_manifest.json')['sources'].items())
checks['study_sources_match']=all(digest((R/'images/study'/p) if p.startswith('product/') else R/p)==expected for p,expected in get('images/study/build_manifest.json')['sources'].items())
checks['heldout_test_count']=len(tests)==600
checks['all_test_cells']=all(v==10 for v in collections.Counter((r['kind'],tuple(r['context']),r['method']) for r in tests).values()) and len({(r['kind'],tuple(r['context']),r['method']) for r in tests})==60
groups=collections.defaultdict(list)
for r in trace:groups[(r['kind'],tuple(r['context']),r['rep'],r['method'])].append(r)
checks['equal_search_budget']=len(groups)==120 and all(len(v)==8 and len({tuple(a['param']) for a in v})==8 for v in groups.values())
training={r['seed'] for r in rows if r['stage']=='train'};testing={r['seed'] for r in rows if r['stage']=='test'}
checks['disjoint_training_test_seeds']=not (training&testing)
checks['memory_integrity']=all(r['corrupt']==r['integrity']==r['deinit']==r['restored_used']==0 for r in rows if r['kind']=='M')
checks['finite_scores']=all(math.isfinite(r['score']) and r['score']>0 for r in rows)
checks['cross_language_cases']=get('results/model_consistency.json')['case_count']==128
closed=get('results/closed_loop.json');checks['actual_kernel_closed_loops']=len(closed)==60 and all((r['recommendation']['a'],r['recommendation']['b'])==(r['actual'].get('q',r['actual'].get('minalloc')),r['actual'].get('floor',r['actual'].get('split'))) for r in closed)
checks['feature_ablations']=len(get('results/ablations.json'))==120
checks['boundary_rejection_and_restart']=len(get('results/robustness.json')['rejections'])==6 and get('results/validation_rejections.json')['guest_recovered']
checks['raw_transcript_present']=(R/'evidence/main_study_final.serial.log').stat().st_size>1000
# Match every structured row to its exact raw guest record. Repeated equal records are allowed.
rawset=set();fieldsets={}
with (R/'evidence/main_study_final.serial.log').open(errors='replace') as f:
 for line in f:
  if line.startswith(('MID_SCHED ','MID_MEMORY ')):
   parts=line.split();kind='S' if parts[0]=='MID_SCHED' else 'M';metrics={k:int(v) for k,v in (x.split('=',1) for x in parts[1:])}
   fieldsets[kind]=list(metrics);rawset.add((kind,tuple(sorted(metrics.items()))))
checks['all_records_in_raw_transcript']=all((r['kind'],tuple(sorted((k,r[k]) for k in fieldsets[r['kind']]))) in rawset for r in rows)
result={'checks':checks,'passed':all(checks.values()),'scope':'Technical evidence audit; formal school signatures and physical hardware validation are outside this package.'}
(R/'results/technical_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['passed']
