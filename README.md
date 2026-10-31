<p align="center"><strong>⚠️ 注意：本项目使用的 Qwen3.8-Flash-Next Gyro-S abliterated 模型在实测中会出现基础算术错误，请核验计算结果。</strong></p>

# Strata · i7-14650HX / RTX 4060 Laptop 调优

面向 **Windows、i7-14650HX、RTX 4060 Laptop 8 GB、32 GB DDR5-5600** 的 Strata 补丁与实测记录。测试模型为 **Qwen3.8-Flash-Next Gyro-S abliterated**，保留原 TQK6/TQK7 精度，不重新量化、不剪枝、不跳过路由专家。

**最终采用：r2 引擎 + 8P8E16T 线程配置。** 同一轮正式对照中，生成速度中位数从 **21.75 → 24.15 token/s（+11.0%）**；含首字等待的整体速度提高约 **7.5%**。这次增益来自同一 r2 引擎的调度设置。r3 和 PGO 的实验结果均保留，但没有证明稳定优势，未用于最终部署。

> 本仓库提供补丁、配置示例和实验记录，不含模型、预编译程序或工具链；属于独立调优实验，并非 Strata 官方发行版。结果来自单台电脑的短提示测试，不代表其他硬件、长上下文或模型能力评分。

**English:** Opt-in CPU patches and reproducible tuning records for Strata on an i7-14650HX / RTX 4060 Laptop. The selected r2 engine with one participating thread per physical core measured 24.15 vs 21.75 decode tokens/s in the same comparison. The ~11% gain is from scheduling settings, not a new GPU kernel. Original Gyro-S precision is preserved. No model weights or binaries are distributed.

## 从这里开始

| 你想做什么 | 入口 |
|---|---|
| 查看成绩、对照条件和选型理由 | [性能结果](docs/RESULTS.md) |
| 构建最终采用的 r2 引擎 | [构建与使用](docs/BUILD.md) |
| 在已有 r2 安装上设置线程 | [配置说明](docs/CONFIGURATION.md) |
| 了解测试方法、失败尝试和限制 | [方法与可复现范围](docs/METHODOLOGY.md) |
| 查找原始结果、日志、配置和历史补丁 | [仓库导览](docs/README.md) |

## 正式结果概览

| 方案 | 正式输出次数 | 生成速度中位数 | 含首字等待的整体速度 |
|---|---:|---:|---:|
| 原 r2 · 8P8E24T | 6 | 21.75 TPS | 19.19 TPS |
| **采用：r2 · 8P8E16T** | **6** | **24.15 TPS** | **20.63 TPS** |
| 普通 r3 · 相同线程配置 | 12 | 23.85 TPS | 20.17 TPS |
| r3 PGO · 原 lookup 参数 | 6 | 24.10 TPS | 20.74 TPS |

每次重启后先预热，再各生成 256 token 的中文说明、Python 代码和 JSON；单并发、temperature 0、seed 42、关闭思考、FP16 KV。**8192 是上下文容量，不是输入长度。**

普通 r3 合并两轮记录，PGO 原参数来自追加 ABBA 对照，各候选并非完全均衡；24.15 与 24.10 的差距不足以证明稳定快慢。选择指标是生成 TPS，整体速度并非所有候选中最高。完整六组成绩、首字延迟和独立 r1/r2 对照见 [性能结果](docs/RESULTS.md)。

## 使用入口

已有可用 r2 安装：先按 [配置说明](docs/CONFIGURATION.md) 核对核心编号，再生成独立配置文件：

```powershell
python scripts/make-tuned-config.py --base E:\Strata\install\working-r2.json --out E:\Strata\install\tuned-r2.json
```

脚本保留模型、引擎路径和认证，只调整调度设置；不会切换服务。没有 r2 引擎时，先阅读 [构建步骤](docs/BUILD.md)。完整脱敏示例见 [configs/](configs/README.md)。

只核查仓库中的历史结果，无需 GPU 或模型：

```powershell
python scripts/verify-results.py
```

它会核对 299 项导出资料的哈希并重新计算性能汇总。重新测速使用 [脚本说明](scripts/README.md) 中的独立命令。

## 目录

| 目录 | 内容 |
|---|---|
| [docs/](docs/README.md) | 构建、配置、成绩与方法 |
| [patches/](patches/README.md) | r2 完整补丁、r1 历史补丁和 r3 实验补丁；有明确应用顺序 |
| [configs/](configs/README.md) | 最终配置示例与全部候选配置 |
| [scripts/](scripts/README.md) | 离线核查、配置生成和独立测速工具 |
| [data/](data/README.md) | 正式结果、筛选记录、数值验证、日志与哈希清单 |
| [archive/](archive/README.md) | 原实验程序与原始差量补丁，仅供追溯 |

## 来源与许可

基于 [Niko1221/Strata](https://github.com/Niko1221/Strata)，固定提交 [`870aedd9e1ebe1c91f94da93b59af17729f6c5c0`](https://github.com/Niko1221/Strata/commit/870aedd9e1ebe1c91f94da93b59af17729f6c5c0)，tag v0.2.8、引擎 0.1.54。保留上游 [MIT 许可](LICENSE)，新增脚本与说明同样采用 MIT，详见 [NOTICE](NOTICE)。

代码和文档由 AI 协助编写；测量来自实际本机运行。测试未采用上游草案标准 benchmark 协议，不宣称获得上游认可。CPU 逐位验证不等于完整生成逐字相同或模型能力得分不变；验证范围见 [方法文档](docs/METHODOLOGY.md)。
