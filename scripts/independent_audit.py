"""Read-only checks on published evidence. Does not trust the previous PASS file."""
from pathlib import Path
from collections import Counter, defaultdict
import json, hashlib, gzip, math, statistics, sys

R=Path(__file__).resolve().parents[1]
def read(name): return json.loads((R/name).read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def score(r):
    if r['kind']=='S': return r['mean_turn']+0.5*r['p95_response']
    return (r['elapsed']-r['probe_cycles'])/r['ops']+0.0002*r['live_used']+5000*r['fails']/r['allocs']
def main():
    rows=[json.loads(x) for x in (R/'results/measurements.jsonl').read_text().splitlines()]
    tests=read('results/test_results.json'); manifest=read('results/study_manifest.json')
    checks={}; details={}
    checks['row_count']=len(rows)==manifest['measurements']==3144
    checks['test_is_exact_journal_subset']=[x for x in rows if x['stage']=='test']==tests and len(tests)==600
    checks['recomputed_scores']=all(math.isclose(score(r),r['score'],rel_tol=1e-12) for r in rows)
    checks['protocol_hash']=digest(R/'protocol.json')==manifest['protocol_sha256']
    checks['study_image_hash']=digest(R/'images/study/OHOS_Image')==manifest['image_sha256']
    for phase in ['study','deployment']:
        bm=read('images/'+phase+'/build_manifest.json')
        checks[phase+'_image_hash']=digest(R/'images'/phase/'OHOS_Image')==bm['image_sha256']
        # Research overrides are deterministically re-created from the patch below.
        checks[phase+'_archived_sources']=all(digest(R/'images'/phase/p if p.startswith('product/') else R/p)==h for p,h in bm['sources'].items() if not p.startswith('build/'))
    checks['memory_integrity']=all(all(r[k]==0 for k in ['corrupt','integrity','restored_used','deinit']) for r in rows if r['kind']=='M')
    cells=Counter((r['kind'],tuple(r['context']),r['method']) for r in tests)
    checks['test_cells']=len(cells)==60 and set(cells.values())=={10}
    stages=['train','pilot_train','validation','pilot_test','test']
    seeds={s:{r['seed'] for r in rows if r['stage']==s} for s in stages}
    checks['seed_partitions']=all(not seeds[a]&seeds[b] for i,a in enumerate(stages) for b in stages[i+1:])
    raw=Counter();fields={}
    with gzip.open(R/'evidence/main_study_final.serial.log.gz','rt') as f:
        for line in f:
            if line.startswith(('MID_SCHED ','MID_MEMORY ')):
                items=line.split();kind='S' if items[0]=='MID_SCHED' else 'M'
                m={k:int(v) for k,v in (x.split('=') for x in items[1:])}
                fields[kind]=list(m);raw[(kind,tuple(sorted(m.items())))]+=1
    expected=Counter((r['kind'],tuple(sorted((k,r[k]) for k in fields[r['kind']]))) for r in rows)
    checks['raw_record_multiplicity']=not (expected-raw)
    checks['compressed_raw_hashes']=all(hashlib.sha256(gzip.decompress((R/x['file']).read_bytes())).hexdigest()==x['uncompressed_sha256'] for x in read('evidence/raw_manifest.json'))
    from scipy.stats import t
    summary=read('results/summary.json');summary_ok=True
    for s in summary:
        selected=[r for r in tests if r['kind']==s['kind'] and str(tuple(r['context']))==s['context']]
        base={r['rep']:r for r in selected if r['method']=='default'}
        selected=[r for r in selected if r['method']==s['method']]
        vals=[100*(base[r['rep']]['score']-r['score'])/base[r['rep']]['score'] for r in selected]
        mean=statistics.mean(vals);half=t.ppf(.975,len(vals)-1)*statistics.stdev(vals)/math.sqrt(len(vals))
        summary_ok &= all(math.isclose(a,b,abs_tol=1e-10) for a,b in [(mean,s['improvement_pct']),(mean-half,s['ci_low']),(mean+half,s['ci_high'])])
    checks['independent_paired_intervals']=bool(summary_ok)
    trace=read('results/search_trace.json'); groups=defaultdict(list)
    for r in trace:groups[(r['kind'],tuple(r['context']),r['rep'],r['method'])].append(r)
    checks['equal_candidate_budgets']=len(groups)==120 and all(len(v)==8 and len({tuple(x['param']) for x in v})==8 for v in groups.values())
    trace_ok=True
    for key,seq in groups.items():
        prior=[]
        for s in seq:
            rr=[r for r in rows if r['stage']=='train' and (r['kind'],tuple(r['context']),r['rep'],r['method'])==key and r['step']==s['step']-1]
            value=statistics.mean(r['score'] for r in rr);prior.append(value)
            trace_ok &= len(rr)==2 and all(r['parameters']==s['param'] for r in rr) and math.isclose(value,s['mean_score']) and math.isclose(min(prior),s['best_score'])
    checks['trace_matches_measurements']=trace_ok
    details['stage_counts']=dict(Counter(r['stage'] for r in rows))
    details['same_global_parameters']={k:v['global_search_parameters'] for k,v in read('results/model_export.json').items()}
    # Existing closed loops supply a direct estimate of pilot cost, not physical runtime.
    loops=read('results/closed_loop.json'); overhead=[]
    for kind in ['S','M']:
        for context in sorted({tuple(x['context']) for x in loops if x['kind']==kind}):
            rs=[x for x in loops if x['kind']==kind and tuple(x['context'])==context]
            ratio=[(x['pilot']['elapsed']+x['recommendation']['inference_cycles']+x['actual']['elapsed'])/x['default']['elapsed'] for x in rs]
            overhead.append({'kind':kind,'context':context,'mean_pilot_plus_actual_elapsed_ratio':statistics.mean(ratio)})
    details['one_shot_inner_elapsed_cost']=overhead
    # Identify parameter-dependent request streams for equal seeds in existing tests.
    adaptive=[]
    for kind,context,rep in sorted({(r['kind'],tuple(r['context']),r['rep']) for r in tests if r['kind']=='M'}):
        rs=[r for r in tests if r['kind']==kind and tuple(r['context'])==context and r['rep']==rep]
        if len({(r['allocs'],r['requested']) for r in rs})>1:adaptive.append({'context':context,'rep':rep})
    details['memory_cells_with_different_request_streams']=adaptive
    result={'passed':all(checks.values()),'checks':checks,'details':details,'scope':'Data integrity and arithmetic only; scientific limitations are in docs/AUDIT.md.'}
    out=Path(sys.argv[1]) if len(sys.argv)>1 else R/'audit/independent_checks.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'checks':checks,'details':details},indent=2))
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
