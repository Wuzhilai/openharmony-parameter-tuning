/* Research product workload for the real OpenHarmony LiteOS-M kernel. */
#include <stdio.h>
#include <stdarg.h>
#include <stdint.h>
#include <sys/stat.h>
#include <errno.h>
#include "los_config.h"
#include "los_task.h"
#include "los_memory.h"
#include "los_tick.h"
#include "los_sched.h"
#include "los_sem.h"
#include "research_api.h"

#define REG(a) (*(volatile uint32_t *)(a))
static void uart_put(char c) { while(REG(0x40004004)&1U){} REG(0x40004000)=(unsigned char)c; }
int _write(int fd,char *buf,int len){(void)fd;for(int i=0;i<len;i++)uart_put(buf[i]);return len;}
int _read(int fd,char *buf,int len){(void)fd;if(len<1)return 0;while(!(REG(0x40004004)&2U)){}buf[0]=(char)REG(0x40004000);return 1;}
int _close(int fd){(void)fd;return -1;} int _fstat(int fd,struct stat *st){(void)fd;st->st_mode=S_IFCHR;return 0;}
int _isatty(int fd){(void)fd;return 1;} int _lseek(int fd,int p,int d){(void)fd;(void)p;(void)d;return 0;}
void *_sbrk(int incr){static char area[65536];static int pos;int old=pos;if(pos+incr<0||pos+incr>(int)sizeof(area)){errno=ENOMEM;return (void*)-1;}pos+=incr;return area+old;}
void _exit(int code){(void)code;while(1){__asm volatile("wfi");}}
void HalPrint(const char *fmt,...){va_list ap;va_start(ap,fmt);vprintf(fmt,ap);va_end(ap);}
void HalDisplayOutput(const char *str,unsigned int len){_write(1,(char*)str,(int)len);}
static void smoke(void){
 printf("MID_SMOKE task_started tick=%u\n",(unsigned)LOS_TickCountGet());
 void *p=LOS_MemAlloc(m_aucSysMem0,128);
 printf("MID_SMOKE allocation=%s\n",p?"ok":"failed");
 if(p)LOS_MemFree(m_aucSysMem0,p);
 LOS_TaskDelay(2);
 printf("MID_BOOT_OK actual_liteos_m=1 tick=%u\n",(unsigned)LOS_TickCountGet());
}
static unsigned rng(unsigned *state){unsigned x=*state;x^=x<<13;x^=x>>17;x^=x<<5;*state=x;return x;}
static unsigned long long cycles(void){return LOS_SysCycleGet();}
static unsigned doneSem;
static unsigned long long origin,firstTime[24],finishTime[24];
static unsigned iterations[24];
static volatile unsigned sink;
static double lastFeatures[5];
extern int MidRecommend(unsigned,const double*,unsigned*,unsigned*);
static void worker(unsigned index){
 firstTime[index]=cycles();
 unsigned x=index+1;
 for(unsigned i=0;i<iterations[index];i++){x=x*1664525U+1013904223U; __asm volatile("" : "+r"(x));}
 sink=x;finishTime[index]=cycles();LOS_SemPost(doneSem);
}
static void sched_bench(unsigned seed,unsigned count,unsigned scale,unsigned q,unsigned floor,unsigned probes){
 if(count<2||count>20||scale<1||scale>20||MidSetSched(q,floor)){printf("MID_ERROR invalid_sched\n");return;}
 LOS_SemCreate(0,&doneSem);g_midProbeEnabled=probes;g_midSwitches=0;
 unsigned state=seed?seed:1,ret=0,ids[24];
 for(unsigned i=0;i<count;i++){
  iterations[i]=(50000U+(rng(&state)%300000U))*scale;
  TSK_INIT_PARAM_S t={0};t.pfnTaskEntry=(TSK_ENTRY_FUNC)worker;t.usTaskPrio=6;t.uwStackSize=4096;t.pcName="mid_worker";t.uwArg=i;
  ret|=LOS_TaskCreate(&ids[i],&t);
 }
 origin=cycles();
 if(ret){printf("MID_ERROR create=%u\n",ret);return;}
 for(unsigned i=0;i<count;i++)LOS_SemPend(doneSem,LOS_WAIT_FOREVER);
 unsigned long long end=cycles(),sum=0,max=0,min=~0ULL;
 unsigned long long responses[24];
 for(unsigned i=0;i<count;i++){
  responses[i]=firstTime[i]-origin;sum+=finishTime[i]-origin;
  if(finishTime[i]>max)max=finishTime[i];
  if(finishTime[i]<min)min=finishTime[i];
 }
 for(unsigned i=0;i<count;i++)for(unsigned j=i+1;j<count;j++)if(responses[j]<responses[i]){unsigned long long x=responses[i];responses[i]=responses[j];responses[j]=x;}
 lastFeatures[0]=count;lastFeatures[1]=scale;lastFeatures[2]=(double)(sum/count)/1e6;
 lastFeatures[3]=(double)responses[(95*count+99)/100-1]/1e6;lastFeatures[4]=(double)g_midSwitches/100;
 printf("MID_SCHED seed=%u n=%u scale=%u q=%u floor=%u probes=%u mean_turn=%llu p95_response=%llu elapsed=%llu switches=%u spread=%llu\n",seed,count,scale,q,floor,probes,sum/count,responses[(95*count+99)/100-1],end-origin,(unsigned)g_midSwitches,max-min);
 LOS_TaskDelay(1); /* Let signalled workers return and kernel reclaim detached TCBs. */
 LOS_SemDelete(doneSem);g_midProbeEnabled=1;MidSetSched(20000,50);
}
static unsigned char arena[131072] __attribute__((aligned(16)));
static void *slots[256];static unsigned sizes[256];
static void mem_bench(unsigned seed,unsigned ops,unsigned mode,unsigned minalloc,unsigned split,unsigned probes){
 if(ops<100||ops>100000||mode>3||MidSetMemory(minalloc,split)){printf("MID_ERROR invalid_memory\n");return;}
 for(unsigned i=0;i<256;i++){slots[i]=0;sizes[i]=0;}
 if(LOS_MemInit(arena,sizeof(arena))){printf("MID_ERROR pool_init\n");return;}
 unsigned state=seed?seed:1,fail=0,corrupt=0,peak=0,allocs=0,requested=0;
 unsigned long long start=cycles(),probeCycles=0;LOS_MEM_POOL_STATUS stat={0};
 for(unsigned i=0;i<ops;i++){
  unsigned index=rng(&state)%256;
  if(slots[index]){
   unsigned char *b=slots[index];if(b[0]!=(unsigned char)index||b[sizes[index]-1]!=(unsigned char)index)corrupt++;
   LOS_MemFree(arena,slots[index]);slots[index]=0;
  }else{
   unsigned size=1+rng(&state)%(mode==0?48:mode==1?512:mode==2?2048:8192);
   allocs++;requested+=size;slots[index]=LOS_MemAlloc(arena,size);sizes[index]=size;
   if(!slots[index])fail++;else{unsigned char *b=slots[index];b[0]=(unsigned char)index;b[size-1]=(unsigned char)index;}
  }
  if(probes&&!(i%1024)){
   unsigned long long p=cycles();LOS_MemInfoGet(arena,&stat);probeCycles+=cycles()-p;
   if(stat.totalUsedSize>peak)peak=stat.totalUsedSize;
  }
 }
 unsigned long long elapsed=cycles()-start;LOS_MemInfoGet(arena,&stat);
 unsigned freeBytes=stat.totalFreeSize,maxFree=stat.maxFreeNodeSize,freeNodes=stat.freeNodeNum,liveUsed=stat.totalUsedSize;
 unsigned integrity=LOS_MemIntegrityCheck(arena);
 for(unsigned i=0;i<256;i++)if(slots[i]){unsigned char *b=slots[i];if(b[0]!=(unsigned char)i||b[sizes[i]-1]!=(unsigned char)i)corrupt++;LOS_MemFree(arena,slots[i]);}
 LOS_MEM_POOL_STATUS restored={0};LOS_MemInfoGet(arena,&restored);unsigned deinit=LOS_MemDeInit(arena);
 lastFeatures[0]=(double)ops/1000;lastFeatures[1]=(double)requested/allocs/1000;lastFeatures[2]=(double)allocs/ops;
 lastFeatures[3]=(double)freeBytes/131072;lastFeatures[4]=1-(double)maxFree/(freeBytes?freeBytes:1);
 printf("MID_MEMORY seed=%u ops=%u mode=%u minalloc=%u split=%u probes=%u elapsed=%llu probe_cycles=%llu allocs=%u requested=%u fails=%u corrupt=%u sampled_peak=%u live_used=%u free=%u maxfree=%u free_nodes=%u integrity=%u restored_used=%u deinit=%u\n",seed,ops,mode,minalloc,split,probes,elapsed,probeCycles,allocs,requested,fail,corrupt,peak,liveUsed,freeBytes,maxFree,freeNodes,integrity,restored.totalUsedSize,deinit);
 MidSetMemory(8,0);
}
static void automatic(unsigned kind,unsigned seed,unsigned a,unsigned b,unsigned pilotSeed,unsigned probes){
 if((kind==0&&(a<2||a>20||b<1||b>20))||(kind==1&&(a<100||a>100000||b>3))){printf("MID_ERROR invalid_automatic\n");return;}
 if(kind==0)sched_bench(pilotSeed,a,b,20000,50,probes);else mem_bench(pilotSeed,a,b,8,0,probes);
 unsigned x,y;unsigned long long t=cycles();int fallback=MidRecommend(kind,lastFeatures,&x,&y);unsigned long long cost=cycles()-t;
 printf("MID_RECOMMEND kind=%u a=%u b=%u fallback=%d inference_cycles=%llu\n",kind,x,y,fallback,cost);
 if(kind==0)sched_bench(seed,a,b,x,y,probes);else mem_bench(seed,a,b,x,y,probes);
}
static void controller(void){
 smoke();printf("MID_READY protocol=1 clock_hz=%u\n",(unsigned)OS_SYS_CLOCK);
 char line[160];unsigned used=0;
 while(1){
  if(!(REG(0x40004004)&2U)){LOS_TaskDelay(1);continue;}
  char c=(char)REG(0x40004000);
  if(c=='\n'){
   line[used]=0;used=0;char kind;unsigned a,b,d,e,f,g;
   if(sscanf(line,"%c %u %u %u %u %u %u",&kind,&a,&b,&d,&e,&f,&g)==7){
    if(kind=='S')sched_bench(a,b,d,e,f,g);
    else if(kind=='M')mem_bench(a,b,d,e,f,g);
    else if(kind=='A')automatic(0,a,b,d,e,g);
    else if(kind=='B')automatic(1,a,b,d,e,g);
    else printf("MID_ERROR unknown_kind\n");
   }else printf("MID_ERROR invalid_command\n");
   printf("MID_READY protocol=1\n");
  }else if(c!='\r'){
   if(used<sizeof(line)-1)line[used++]=c;else{used=0;printf("MID_ERROR line_overflow\n");}
  }
 }
}
int main(void){
 REG(0x40004008)=3; /* UART TX/RX enable; polled transport, no measurement IRQ. */
 setvbuf(stdout,NULL,_IONBF,0);
 printf("MID_BOOT OpenHarmony LiteOS-M QEMU mps2-an386\n");
 unsigned ret=LOS_KernelInit();printf("MID_INIT ret=%u\n",ret);if(ret)_exit(1);
 TSK_INIT_PARAM_S t={0};unsigned id;t.pfnTaskEntry=(TSK_ENTRY_FUNC)controller;t.usTaskPrio=5;t.uwStackSize=16384;t.pcName="mid_controller";
 ret=LOS_TaskCreate(&id,&t);printf("MID_TASK_CREATE ret=%u\n",ret);if(ret)_exit(2);
 LOS_Start();_exit(3);return 0;
}
