// Generated from results/models.pkl; do not edit by hand.
#include <float.h>
static int predict_0(const double *f) {
  if ((float)f[1] <= 3) {
    if ((float)f[1] <= 1.5) {
      return 12;
    } else {
      if ((float)f[2] <= 0.17651549726724625) {
        return 10;
      } else {
        return 12;
      }
    }
  } else {
    if ((float)f[2] <= 0.46424399316310883) {
      if ((float)f[3] <= 0.69081950187683105) {
        return 2;
      } else {
        return 1;
      }
    } else {
      if ((float)f[2] <= 1.6837770342826843) {
        return 2;
      } else {
        return 0;
      }
    }
  }
}
static const double low_0[5] = {-1.5,-1.25,-0.44501225,-0.80841700000000005,-0.054999999999999993};
static const double high_0[5] = {19.5,12.25,2.32554325,4.0931690000000005,0.57499999999999996};
static const unsigned space_0[][2] = {{1000,50},{1000,200},{1000,500},{2000,50},{2000,200},{2000,500},{5000,50},{5000,200},{5000,500},{10000,50},{10000,200},{10000,500},{20000,50},{20000,200},{20000,500},{40000,50},{40000,200},{40000,500}};
static int predict_1(const double *f) {
  if ((float)f[4] <= 0.060419999063014984) {
    return 0;
  } else {
    if ((float)f[3] <= 0.212005615234375) {
      if ((float)f[2] <= 0.54662498831748962) {
        return 13;
      } else {
        return 0;
      }
    } else {
      if ((float)f[0] <= 3) {
        return 7;
      } else {
        return 1;
      }
    }
  }
}
static const double low_1[5] = {1.5,-0.22936237362654388,0.49837499999999996,-0.11186981201171875,-0.22880498040273087};
static const double high_1[5] = {4.5,1.2899484960396961,0.5891249999999999,1.1767807006835938,1.1528784338029661};
static const unsigned space_1[][2] = {{8,0},{8,16},{8,32},{8,64},{8,128},{16,0},{16,16},{16,32},{16,64},{16,128},{32,0},{32,16},{32,32},{32,64},{32,128},{64,0},{64,16},{64,32},{64,64},{64,128}};
extern "C" int MidRecommend(unsigned kind, const double *f, unsigned *a, unsigned *b) {
 if (kind>1 || !f || !a || !b) return -1;
 *a=kind==0?20000:8;*b=kind==0?50:0;
 const double *lo=kind==0?low_0:low_1,*hi=kind==0?high_0:high_1;
 for(unsigned i=0;i<5;i++) if (!(f[i]<=DBL_MAX && f[i]>=-DBL_MAX) || f[i]<lo[i] || f[i]>hi[i]) return 1;
 int n=kind==0?predict_0(f):predict_1(f);
 *a=kind==0?space_0[n][0]:space_1[n][0];*b=kind==0?space_0[n][1]:space_1[n][1];return 0;
}
