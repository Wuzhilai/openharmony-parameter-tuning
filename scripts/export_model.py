"""Export fitted Python trees and identical domain checks to freestanding C++."""
import pickle,json
import numpy as np
from guest import R
models=pickle.loads((R/'results/models.pkl').read_bytes());text=['// Generated from results/models.pkl; do not edit by hand.\n#include <float.h>\n']
export={}
for ki,kind in enumerate(['S','M']):
 m=models[kind];t=m['tree'].tree_;space=m['space'];bounds=m['bounds'];span=np.maximum(bounds[1]-bounds[0],.01)
 text.append(f'static int predict_{ki}(const double *f) {{\n')
 def branch(node,indent):
  if t.children_left[node]==t.children_right[node]:
   label=int(m['tree'].classes_[int(np.argmax(t.value[node][0]))]);return indent+f'return {label};\n'
  feat=int(t.feature[node]);return indent+f'if ((float)f[{feat}] <= {t.threshold[node]:.17g}) {{\n'+branch(t.children_left[node],indent+'  ')+indent+'} else {\n'+branch(t.children_right[node],indent+'  ')+indent+'}\n'
 text.append(branch(0,'  '));text.append('}\n')
 text.append(f'static const double low_{ki}[5] = {{'+','.join(f'{x:.17g}' for x in bounds[0]-.25*span)+'};\n')
 text.append(f'static const double high_{ki}[5] = {{'+','.join(f'{x:.17g}' for x in bounds[1]+.25*span)+'};\n')
 text.append(f'static const unsigned space_{ki}[][2] = {{'+','.join('{'+str(a)+','+str(b)+'}' for a,b in space)+'};\n')
 export[kind]={'features':m['feature_names'],'bounds':bounds.tolist(),'default':m['default'],'global_search_parameters':m['globals'],'nodes':int(t.node_count),'depth':int(t.max_depth),'candidate_space':space}
text.append('''extern "C" int MidRecommend(unsigned kind, const double *f, unsigned *a, unsigned *b) {
 if (kind>1 || !f || !a || !b) return -1;
 *a=kind==0?20000:8;*b=kind==0?50:0;
 const double *lo=kind==0?low_0:low_1,*hi=kind==0?high_0:high_1;
 for(unsigned i=0;i<5;i++) if (!(f[i]<=DBL_MAX && f[i]>=-DBL_MAX) || f[i]<lo[i] || f[i]>hi[i]) return 1;
 int n=kind==0?predict_0(f):predict_1(f);
 *a=kind==0?space_0[n][0]:space_1[n][0];*b=kind==0?space_0[n][1]:space_1[n][1];return 0;
}
''')
(R/'product/model.cpp').write_text(''.join(text));(R/'results/model_export.json').write_text(json.dumps(export,indent=2))
print(json.dumps(export,indent=2))
