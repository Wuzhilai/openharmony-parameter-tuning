"""Create reviewable research overrides; leave upstream checkout unchanged."""
from pathlib import Path
import difflib,json,subprocess,hashlib
R=Path(__file__).resolve().parents[1];K=R/'research/kernel_liteos_m';O=R/'build/overrides';O.mkdir(parents=True,exist_ok=True)
patches=[]
def emit(rel,text):
 original=(K/rel).read_text();(O/Path(rel).name).write_text(text)
 patches.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
rel='kernel/src/los_sched.c';s=(K/rel).read_text()
s=s.replace('STATIC INT32 g_schedTimeSlice;', 'volatile UINT32 g_midProbeEnabled = 1;\nvolatile UINT32 g_midSwitches = 0;\nSTATIC INT32 g_schedTimeSlice;')
s=s.replace('isTaskSwitch = TRUE;', 'isTaskSwitch = TRUE;\n        if (g_midProbeEnabled) { g_midSwitches++; }')
s+='''
/* Research-only control API. Invoked between workloads while no worker exists. */
UINT32 MidSetSched(UINT32 quantumUs, UINT32 minimumUs)
{
    if (quantumUs < 1000 || quantumUs > 40000 || minimumUs < 50 || minimumUs > 500 || minimumUs >= quantumUs) return LOS_NOK;
    UINT32 state = LOS_IntLock();
    g_schedTimeSlice = (INT32)(((UINT64)g_sysClock * quantumUs) / OS_SYS_US_PER_SECOND);
    g_schedTimeSliceMin = (INT32)(((UINT64)g_sysClock * minimumUs) / OS_SYS_US_PER_SECOND);
    LOS_IntRestore(state);
    return LOS_OK;
}
'''
emit(rel,s)
rel='kernel/src/mm/los_memory.c';s=(K/rel).read_text()
s=s.replace('#define OS_MEM_MIN_LEFT_SIZE        sizeof(struct OsMemFreeNodeHead)', 'static UINT32 g_midSplitExtra = 0;\nstatic UINT32 g_midMinAlloc = 8;\n#define OS_MEM_MIN_LEFT_SIZE (sizeof(struct OsMemFreeNodeHead) + g_midSplitExtra)')
s=s.replace('#define OS_MEM_MIN_ALLOC_SIZE       8','#define OS_MEM_MIN_ALLOC_SIZE g_midMinAlloc')
s+='''
/* Defaults preserve the upstream split threshold and minimum allocation. */
UINT32 MidSetMemory(UINT32 minAlloc, UINT32 splitExtra)
{
    if ((minAlloc != 8 && minAlloc != 16 && minAlloc != 32 && minAlloc != 64) || splitExtra > 128 || (splitExtra & 3)) return LOS_NOK;
    UINT32 state = LOS_IntLock();
    g_midMinAlloc = minAlloc; g_midSplitExtra = splitExtra;
    LOS_IntRestore(state); return LOS_OK;
}
'''
emit(rel,s)
(R/'evidence/kernel_research.patch').write_text(''.join(patches))
lock=json.loads((R/'evidence/source_lock.json').read_text()) if (R/'evidence/source_lock.json').exists() else {}
for p in (R/'research').iterdir():
 if (p/'.git').exists():
  lock[p.name]={'commit':subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip(),'remote':subprocess.check_output(['git','-C',str(p),'remote','get-url','origin'],text=True).strip()}
(R/'evidence/source_lock.json').write_text(json.dumps(lock,indent=2))
print('Created overrides and source lock; upstream sources unchanged')
