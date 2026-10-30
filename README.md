# Strata：i7-14650HX / RTX 4060 Laptop 调优记录

在一台 **i7-14650HX、RTX 4060 Laptop 8 GB、32 GB DDR5-5600、Windows** 电脑上，对 Strata 运行 Gyro-S abliterated 的源码、线程布局、内存方案和推测参数进行实测。最终使用 **r2 内核 + 8P8E16T**：在同一轮正式对照中，生成速度中位数由 **21.75 提高至 24.15 token/s（+11.0%）**。

**English:** Hardware-specific Windows tuning notes, opt-in CPU patches and complete sanitized measurements. The selected r2 engine with one participating thread per physical core measured 24.15 vs 21.75 decode tokens/s on this machine. The final ~11% gain is from scheduling settings, not a new GPU kernel. This is an independent experiment, not an official Strata release or a standard benchmark certification.

## 实测结果

测试日期：2026-10-30。每次重启后先生成 256 token 预热，再各生成 256 token 的中文说明、Python 代码和 JSON。短提示、单并发、temperature 0、seed 42、关闭思考、8192 上下文容量、FP16 KV。**8192 是容量，不是输入长度。**

| 正式候选 | 输出次数 | 生成速度中位数（TPS） | 含首字等待的整体速度（TPS） |
|---|---:|---:|---:|
| 原 r2，8P8E24T | 6 | 21.75 | 19.19 |
| **r2 调优，8P8E16T（采用）** | **6** | **24.15** | **20.63** |
| 普通 r3，同一组线程参数 | 12 | 23.85 | 20.17 |
| r3，延长 lookup chain | 6 | 23.80 | 20.88 |
| r3 PGO，延长 lookup chain | 6 | 22.35 | 19.79 |
| r3 PGO，原 lookup 参数 | 6 | 24.10 | 20.74 |

原 r2 与最终配置的首字延迟中位数为 1.793 → 1.803 秒，整体速度提高约 7.5%。选型指标沿用生成 TPS；含首字等待的整体速度不是所有候选中最高的。

普通 r3 在初次正式轮测得 24.40 TPS，追加复测后合并为 23.85 TPS，没有删除较慢的有效成绩。PGO 与调优 r2 相差约 0.2%，不足以证明稳定优势，因此保留已验证的 r2 内核。普通 r3 有 12 次输出，其他候选各 6 次；PGO 原参数来自追加的独立 ABBA 对照，不是所有候选同时交替的均衡试验。

此前独立一轮 r1/r2 内核比较为 **18.60 → 19.55 TPS（+5.1%）**。这组基线和上表来自不同时段，不能把 18.60 与 24.15 直接拼成内核提速比例。详见 [方法与限制](docs/METHODOLOGY.md)。

## 最终配置

这台机器的 P 核逻辑编号是 0–15（相邻两个属于同一物理核心），E 核为 16–23。主线程用 0，15 个工作线程用 `2,4,6,8,10,12,14,16-23`：8P+8E、每个物理核心一个参与线程。其他机器须先核对处理器编号。

```text
--pool-cores 2,4,6,8,10,12,14,16-23
--pool-workers 15
--pool-affinity all
--host-core first
--pool-tasks 0
STRATA_POOL_UMWAIT=10000
STRATA_POOL_UMWAIT_ESC=20000
```

保留 Gyro-S TQK6/TQK7、48 层 × 512 专家、FP16 KV，以及原 `--spec 4 --spec-min-p 0.5` MTP 设置；不重新量化、不剪枝、不跳过路由专家。运行时 lookup 可以扩展窗口，所以 `/metrics` 中的 `spec` 会显示 6；MTP cap 为 4。

- [完整脱敏配置](configs/tuned.example.json)：`${STRATA_ROOT}` 是待替换占位符，没有包含 API 密钥。
- [构建与使用](docs/BUILD.md)：固定上游提交、编译参数、配置生成方式。
- [原始正式结果](data/final-results.json) 与 [全部探索记录](data/r3/experiments)：保留失败、生成文本、资源采样和日志。
- [r2 完整补丁](patches/r2.patch)：从固定上游提交应用，包含 r1 的改动。
- [r3 实验补丁](patches/r3-experimental.patch)：从同一上游提交应用，未部署；用于记录没有稳定收益的尝试。
- [一致性验证](data/r3/parity.json)、[PGO 验证](data/r3/parity-r3pgo.json) 和 [r2 验证日志](data/r2/logs/integrated-check-640.log)。

## 范围

这是单台电脑、短提示、特定模型和编译器下的测量；没有长上下文、模型能力评分、AMD/HIP、Intel/SYCL、Linux 或其他 CPU/GPU 的验证。CPU 计算路径的逐位测试通过，不等于完整生成文本逐字相同，也不等于模型能力得分相同。磁盘补页、系统缓存、GPU 专家缓存与推测接受率会影响结果。

新代码默认关闭，通过 `STRATA_14650HX_4060=ON` 选择。它只针对本次硬件实验，不建议据此修改上游全局默认值。本轮没有对修改后的完整默认构建做二进制一致性证明，也没有跨后端构建验证。

仓库不含模型、可执行程序、CUDA/MSVC 工具链或运行密钥。实验大文件已在本机清理；PGO 的原始计数器也已删除，只有采样说明、验证与性能结果保留，不能保证逐字节重建当时的 PGO 二进制。

## 来源与许可

基于 [Niko1221/Strata](https://github.com/Niko1221/Strata)，固定提交 [`870aedd9e1ebe1c91f94da93b59af17729f6c5c0`](https://github.com/Niko1221/Strata/commit/870aedd9e1ebe1c91f94da93b59af17729f6c5c0)，tag v0.2.8、引擎 0.1.54。保留上游 [MIT 许可](LICENSE)。本仓库新增脚本与说明同样按 MIT 许可提供，Copyright (c) 2026 AshenJyy。

代码和文档由 AI 协助编写；测量来自实际本机运行。这里的测试没有使用上游草案标准 benchmark 协议，不宣称获得上游认可。数值汇总可离线核查：

```powershell
python scripts/verify-results.py
```
