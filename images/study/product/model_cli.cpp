#include <cstdio>
#include <cstdlib>
extern "C" int MidRecommend(unsigned,const double*,unsigned*,unsigned*);
int main(int argc,char **argv){
 if(argc!=7)return 2;
 char *end;unsigned kind=(unsigned)strtoul(argv[1],&end,10);if(*end||kind>1)return 2;
 double f[5];for(int i=0;i<5;i++){f[i]=strtod(argv[i+2],&end);if(end==argv[i+2]||*end)return 2;}
 unsigned a,b;int mode=MidRecommend(kind,f,&a,&b);printf("%u %u %d\n",a,b,mode);return 0;
}
