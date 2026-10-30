#include "strata/kernels/cpu/tq_cpu.hpp"
#include <windows.h>
#include <intrin.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

namespace strata::kernels::cpu {
alignas(64) static int16_t state_table[32768*4];
const int16_t* tq_state_table() { return state_table; }
bool cpu_avxvnni_ok() { int c[4]; __cpuidex(c,7,1); return (c[0] & (1<<4)) != 0; }
namespace tq_detail {
#define DECL(N) void tq_rows_##N(int,const int16_t*,const uint8_t*,size_t,int,const TqAct* const*,int,float* const*,int,int);
DECL(r1) DECL(nt) DECL(vnni) DECL(ntvnni) DECL(ntinsert) DECL(ntvnnipf) DECL(ntbulk) DECL(ntbulkvnni) DECL(ntgather) DECL(r2)
}
}
static uint32_t rng=0x24650406;
static uint32_t next() { rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng; }
using namespace strata::kernels::cpu;
using namespace strata::kernels::cpu::tq_detail;
using Fn=decltype(&tq_rows_r1);
struct Variant {const char* name;Fn fn;};
Variant vars[]={{"r1",tq_rows_r1},{"r2",tq_rows_r2}};
constexpr int NV=sizeof(vars)/sizeof(vars[0]);
void fill_weights(std::vector<uint8_t>& w,int kb) {
    for(auto& b:w)b=(uint8_t)next();
    for(size_t i=0;i<w.size();i+=2+4*kb) {
        uint16_t h=(uint16_t)(next()%0x7c00u); // zeros, subnormals and every finite exponent
        if(next()&1)h|=0x8000;
        std::memcpy(w.data()+i,&h,2);
    }
}
int main() {
    for(auto& v:state_table)v=(int16_t)next();
    alignas(64) TqAct act[8];const TqAct* ap[8];
    for(int t=0;t<8;++t) {ap[t]=act+t;for(auto& q:act[t].q)q=(int16_t)((int)(next()%255)-127);for(auto& d:act[t].d)d=(float)(1+next()%257)/8192.0f;}
    int cases=0;
    for(int core:{0,16}) {
        if(!SetThreadAffinityMask(GetCurrentThread(),(DWORD_PTR)1<<core))return 3;
        int cp[4];__cpuidex(cp,7,1);bool vnni=(cp[0]&(1<<4))!=0;
        std::printf("CPU core=%d avx_vnni=%d\n",core,(int)vnni);std::fflush(stdout);
        if(!vnni)return 4;
        for(int kb:{4,5,6,7,8}) for(int n:{128,256,512,640,2048,2560,4096,5120}) {
            size_t row=(size_t)(2+4*kb)*(n/128);std::vector<uint8_t>w(17*row);fill_weights(w,kb);
            for(int nt=1;nt<=8;++nt) for(int start:{0,3}) {
                float ref[8][17],got[8][17];float* rp[8];float* gp[8];
                for(int t=0;t<8;++t){rp[t]=ref[t];gp[t]=got[t];}
                std::memset(ref,0x5a,sizeof ref);tq_rows_r1(kb,state_table,w.data(),row,n,ap,nt,rp,start,start?16:17);
                for(auto v:vars) {
                    std::memset(got,0x5a,sizeof got);v.fn(kb,state_table,w.data(),row,n,ap,nt,gp,start,start?16:17);
                    if(std::memcmp(ref,got,sizeof ref)){std::printf("FAIL %s core%d K%d n%d T%d start%d\n",v.name,core,kb,n,nt,start);return 1;}
                    ++cases;
                }
            }
        }
        std::printf("PARITY core=%d passed\n",core);std::fflush(stdout);
        // Interleaved repetitions of every variant; identical input and affinity.
        for(int kb:{6,7}) for(int nt:{1,2,3,4,6}) {
            int n=kb==6?2560:640;size_t row=(size_t)(2+4*kb)*(n/128);std::vector<uint8_t>w(256*row);fill_weights(w,kb);
            float output[8][256];float* op[8];for(int t=0;t<8;++t)op[t]=output[t];
            double times[NV][7]{};
            for(int pass=0;pass<8;++pass) for(int j=0;j<NV;++j) {
                int k=(j+pass)%NV;auto v=vars[k];
                auto t0=std::chrono::steady_clock::now();
                for(int rep=0;rep<100;++rep)v.fn(kb,state_table,w.data(),row,n,ap,nt,op,0,256);
                double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t0).count()/100;
                if(pass)times[k][pass-1]=ms;
            }
            for(int k=0;k<NV;++k){std::sort(times[k],times[k]+7);std::printf("BENCH core=%d K=%d T=%d variant=%s ms=%.6f\n",core,kb,nt,vars[k].name,times[k][3]);}
            std::fflush(stdout);
        }
    }
    std::printf("PASS: %d bitwise comparisons; all token counts 1..8, P/E cores, finite half scales and row boundaries.\n",cases);
    return 0;
}
