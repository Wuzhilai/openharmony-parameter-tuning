"""Build a reproducible OpenHarmony LiteOS-M kernel research product for MPS2.

Uses upstream kernel and QEMU board startup/linker; custom UART/product workload.
This is a kernel research image, not a complete OpenHarmony userspace distribution.
"""
from pathlib import Path
import subprocess, json, hashlib, concurrent.futures, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
K=ROOT/'research/kernel_liteos_m'; B=ROOT/'research/device_qemu/arm_mps2_an386/liteos_m/board'
O=ROOT/'build'; P=ROOT/'product'; O.mkdir(exist_ok=True);P.mkdir(exist_ok=True)
def run(cmd):
 r=subprocess.run([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 return r.returncode,r.stdout
def main():
 subprocess.run([sys.executable,str(ROOT/'scripts/prepare_instrumentation.py')],check=True)
 config='''#ifndef MID_TARGET_CONFIG_H
#define MID_TARGET_CONFIG_H
#include "soc.h"
#define OS_SYS_CLOCK SYSCLK_FREQ
#define LOSCFG_BASE_CORE_TICK_PER_SECOND 100UL
#define LOSCFG_BASE_CORE_TICK_PER_SECOND_MINI 1000UL
#define LOSCFG_BASE_CORE_TICK_RESPONSE_MAX 0xFFFFFFUL
#define LOSCFG_PLATFORM_HWI 1
#define LOSCFG_USE_SYSTEM_DEFINED_INTERRUPT 1
#define LOSCFG_PLATFORM_HWI_LIMIT 128
#define LOSCFG_BASE_CORE_TSK_LIMIT 40
#define LOSCFG_BASE_CORE_TSK_IDLE_STACK_SIZE 2048
#define LOSCFG_BASE_CORE_TSK_DEFAULT_STACK_SIZE 8192
#define LOSCFG_BASE_CORE_TSK_MIN_STACK_SIZE 512
#define LOSCFG_BASE_CORE_TIMESLICE 1
#define LOSCFG_BASE_CORE_TIMESLICE_TIMEOUT 20000
#define LOSCFG_BASE_CORE_TSK_MONITOR 1
#define LOSCFG_BASE_CORE_EXC_TSK_SWITCH 1
#define LOSCFG_BASE_IPC_SEM_LIMIT 48
#define LOSCFG_BASE_IPC_MUX_LIMIT 24
#define LOSCFG_BASE_IPC_QUEUE_LIMIT 24
#define LOSCFG_BASE_CORE_SWTMR_LIMIT 24
#define LOSCFG_SYS_EXTERNAL_HEAP 1
extern unsigned int __heap_start, __heap_size;
#define LOSCFG_SYS_HEAP_ADDR ((void *)&__heap_start)
#define LOSCFG_SYS_HEAP_SIZE ((unsigned int)&__heap_size)
#define LOSCFG_MEM_MUL_POOL 1
#define LOSCFG_MEM_FREE_BY_TASKID 1
#define LOSCFG_MEMORY_BESTFIT 1
#define LOSCFG_KERNEL_PRINTF 1
#define LOSCFG_USE_SHELL 0
#define LOSCFG_LIBC_NEWLIB 1
#endif
'''
 (O/'target_config.h').write_text(config)
 # Explicit, audited source selection: all minimum-kernel C modules, target arch,
 # common interrupt and utility implementations. Middleware is outside product scope.
 sources=list((K/'kernel/src').glob('*.c'))+list((K/'kernel/src/mm').glob('*.c'))
 arch=K/'arch/arm/cortex-m4/gcc'
 sources+=list(arch.glob('*.c'))+list(arch.glob('*.S'))
 sources+=[K/'arch/arm/common/los_common_interrupt.c',K/'components/signal/los_signal.c']+list((K/'utils').glob('*.c'))
 sources+=list((ROOT/'research/bounds_checking_function/src').glob('*.c'))
 sources+=[B/'startup.s',P/'main.c']
 if (P/'model.cpp').exists():sources.append(P/'model.cpp')
 sources=[O/'overrides'/s.name if s.name in ['los_sched.c','los_memory.c'] else s for s in sources]
 inc=[O,P,arch,K/'arch/arm/common',K/'arch/include',K/'kernel/include',K/'utils',B/'include',ROOT/'research/cmsis/CMSIS/Core/Include',ROOT/'research/bounds_checking_function/include']
 inc+=sorted({p.parent for p in (K/'components').rglob('*.h')})
 flags=['-mcpu=cortex-m4','-mthumb','-mfloat-abi=soft','-O2','-g3','-ffunction-sections','-fdata-sections','-fno-common','-D__LITEOS__','-D__LITEOS_M__','-D__FPU_PRESENT=1','-Wall','-Wno-pointer-sign']
 flags+=[v for p in inc for v in ['-I',str(p)]]
 commands=[];objects=[]
 for i,src in enumerate(sources):
  obj=O/f'{i:03d}_{src.stem}.o';objects.append(obj)
  compiler='arm-none-eabi-g++' if src.suffix=='.cpp' else 'arm-none-eabi-gcc'
  commands.append([compiler,*flags,'-c',src,'-o',obj])
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(run,commands))
 log='\n'.join(' '.join(map(str,c))+'\n'+r[1] for c,r in zip(commands,results))
 (O/'compile.log').write_text(log)
 failures=[(c,r) for c,r in zip(commands,results) if r[0]]
 if failures:
  print('\n'.join(str(c[-3])+'\n'+r[1][-3000:] for c,r in failures[:8]));return 1
 cmd=['arm-none-eabi-gcc','-mcpu=cortex-m4','-mthumb','-mfloat-abi=soft','-nostartfiles','--specs=nosys.specs',*objects,'-Wl,--gc-sections','-Wl,-Map='+str(O/'kernel.map'),'-T',B/'liteos.ld','-o',O/'OHOS_Image','-lc','-lm','-lgcc']
 code,out=run(cmd);(O/'link.log').write_text(out);print(out)
 if code:return code
 print(run(['arm-none-eabi-size',O/'OHOS_Image'])[1])
 manifest={'image_sha256':hashlib.sha256((O/'OHOS_Image').read_bytes()).hexdigest(),'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'compiler':run(['arm-none-eabi-gcc','--version'])[1].splitlines()[0],'commands':[list(map(str,c)) for c in commands]+[list(map(str,cmd))]}
 (O/'build_manifest.json').write_text(json.dumps(manifest,indent=2));return 0
if __name__=='__main__':sys.exit(main())
