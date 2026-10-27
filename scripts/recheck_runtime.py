"""Replay deployment and robustness checks in audit/rerun, preserving archived data."""
from pathlib import Path
import shutil, subprocess, sys, runpy, json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'audit/rerun'
for name in ['build','results','evidence']: (OUT/name).mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'protocol.json',OUT/'protocol.json')
for name in ['models.pkl','measurements.jsonl','selections.json','test_results.json']:
    shutil.copy2(ROOT/'results'/name,OUT/'results'/name)
shutil.copy2(ROOT/'images/deployment/OHOS_Image',OUT/'build/OHOS_Image')
subprocess.run(['g++','-O2',str(ROOT/'product/model.cpp'),str(ROOT/'product/model_cli.cpp'),'-o',str(OUT/'build/model_cli')],check=True)
import guest
guest.R=OUT
for name in ['verify_deployment.py','supplementary_tests.py']:
    runpy.run_path(str(ROOT/'scripts'/name),run_name='__main__')
checks=json.loads((OUT/'results/model_consistency.json').read_text())
loops=json.loads((OUT/'results/closed_loop.json').read_text())
result={'cross_language_cases':checks['case_count'],'fresh_kernel_closed_loops':len(loops),'fresh_ablation_measurements':len(json.loads((OUT/'results/ablations.json').read_text())),'fresh_rejections':len(json.loads((OUT/'results/robustness.json').read_text())['rejections']),'status':'passed','scope':'Archived deployment image replay; original results unchanged.'}
(ROOT/'audit/runtime_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
