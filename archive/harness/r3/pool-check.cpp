#include "strata/kernels/cpu/pool.hpp"
#include "strata/kernels/cpu/tq_cpu.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <vector>
namespace cpu=strata::kernels::cpu;
int main(int argc,char** argv) {
    if(argc!=3) return 2;
    cpu::NativeFmt f;std::string err;
    if(!cpu::native_fmt(145,146,cpu::H,cpu::FF,f,err)) return 3;
    std::vector<uint8_t> blob(f.bytes*3);
    std::ifstream weights("${STRATA_ROOT}/data/packs/gyro-s-abliterated/experts.bin",std::ios::binary);
    if(!weights.read((char*)blob.data(),blob.size())) return 4;
    std::ofstream result(argv[2],std::ios::binary);
    if(!result) return 5;
    const bool perf=std::strcmp(argv[1],"perf")==0;
    int checks=0;size_t values=0;
    std::vector<float> gs(cpu::H),ds(cpu::FF),x(cpu::H);
    for(int i=0;i<cpu::H;++i)gs[i]=(i%7<3)?-1.f:1.f;
    for(int i=0;i<cpu::FF;++i)ds[i]=(i%11<5)?-1.f:1.f;
    // Addresses deliberately stay fixed as their contents and Hadamard mode change.
    std::vector<std::vector<uint8_t>> acts(17,std::vector<uint8_t>(cpu::kNativeActBytes));
    const auto started=std::chrono::steady_clock::now();
    const std::vector<int> workers=perf?std::vector<int>{23}:std::vector<int>{1,3,23};
    for(int nw:workers) for(int tasks:perf?std::vector<int>{144}:std::vector<int>{1,41,144,256}) {
        cpu::ExpertPool pool(nw,true,true,cpu::PoolAffinity::All,tasks);
        for(int scenario=0;scenario<(perf?5:6);++scenario) {
            const int ns[]={1,7,17,97,9,7};const int n=perf?24:ns[scenario];
            std::vector<cpu::ExpertJobMulti> jobs(n);
            std::vector<float> out((size_t)n*cpu::MAXT*cpu::H);
            for(int rep=0;rep<(perf?8:2);++rep) {
                f.had_block=rep?128:0;f.had_gu=f.had_d=(rep!=0);f.gu_signs=gs.data();f.d_signs=ds.data();
                for(int t=0;t<17;++t) {
                    for(int i=0;i<cpu::H;++i)x[i]=0.4f*std::sin((float)(i+13*t+17*rep)*0.031f);
                    cpu::native_quant_act(f,x.data(),acts[t].data());
                }
                std::fill(out.begin(),out.end(),0.f);
                for(int e=0;e<n;++e) {
                    jobs[e].blob=blob.data()+(e%3)*f.bytes;
                    jobs[e].nt=perf?(1+e%5):(1+(e+scenario)%8);
                    jobs[e].fmt=(e%2)?&f:nullptr;
                    for(int t=0;t<jobs[e].nt;++t) {
                        int ai=(scenario==4)?((e+t)%17):t; // >8 distinct inputs exercises fallback
                        jobs[e].nact[t]=acts[ai].data();
                        jobs[e].out[t]=out.data()+((size_t)e*cpu::MAXT+t)*cpu::H;
                        std::fill(jobs[e].out[t],jobs[e].out[t]+cpu::H,std::numeric_limits<float>::quiet_NaN());
                    }
                }
                pool.run_split_multi_native(f,jobs.data(),n,scenario==5?cpu::NativeArithmetic::WindowInvariant:cpu::NativeArithmetic::Default);
                for(float v:out)if(!std::isfinite(v)){std::fprintf(stderr,"nonfinite output\n");return 6;}
                if(!perf)result.write((char*)out.data(),out.size()*sizeof(float));
                ++checks;values+=out.size();
            }
        }
        std::printf("workers=%d tasks=%d GU=%.3f quant=%.3f down=%.3f ms\n",nw,tasks,pool.ms_multi_gu,pool.ms_multi_q,pool.ms_multi_down);
        std::fflush(stdout);
    }
    double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    std::printf("PASS finite: %d batches, %zu floats, %.3f sec; reference comparison is external\n",checks,values,elapsed);
    return 0;
}
