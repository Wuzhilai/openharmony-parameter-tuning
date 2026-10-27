#ifndef MID_RESEARCH_API_H
#define MID_RESEARCH_API_H
#include "los_compiler.h"
UINT32 MidSetSched(UINT32 quantumUs,UINT32 minimumUs);
UINT32 MidSetMemory(UINT32 minAlloc,UINT32 splitExtra);
extern volatile UINT32 g_midProbeEnabled,g_midSwitches;
#endif
