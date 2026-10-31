# 补丁关系与应用顺序

[返回首页](../README.md) · [构建步骤](../docs/BUILD.md)

所有完整补丁均基于固定上游提交 `870aedd9e1ebe1c91f94da93b59af17729f6c5c0`。**复现最终部署只需 `r2.patch`。**

| 文件 | 应用起点 | 包含内容 | 状态 |
|---|---|---|---|
| [r2.patch](r2.patch) | 干净的固定上游提交 | r1 + r2 全部改动 | **最终部署的引擎** |
| [r1.patch](r1.patch) | 干净的固定上游提交 | 初版 trellis 整数解码与混合核心任务分配 | 历史基线 |
| [r2-only.patch](r2-only.patch) | 上游提交已应用 r1 | r1 → r2 差量 | 仅用于已有 r1 工作树 |
| [r3-experimental.patch](r3-experimental.patch) | 干净的固定上游提交 | r1 + r2 + r3 / PGO 实验改动 | 未用于最终部署 |

`r2.patch` 与 `r3-experimental.patch` 都是完整补丁，不能叠加到 r1 或 r2 完整补丁之上。先在独立源码目录中运行 `git apply --check`，具体命令见 [构建文档](../docs/BUILD.md)。

新代码默认关闭，通过 `STRATA_14650HX_4060=ON` 选择；本次使用 CUDA 架构目标 89。r2 的 CPU 优化包括有界 64 位状态读取、固定 1–8 token 模板和 AVX-VNNI 整数点积，保留浮点缩放、FMA 与归约顺序。它不是新编写的 RTX 4060 GPU 内核。

完整补丁保持原始字节。`r2-only.patch` 仅将 CRLF 统一为 LF，以修复 Git 应用问题；原始版本保存在 [archive/patches/r2-only-original.patch](../archive/patches/r2-only-original.patch)。

r3 的固定 PGO 路径属于原实验环境，需自行调整和重新采样；原 PGO 计数器已删除。原始哈希、构建清单与数值验证见 [数据索引](../data/README.md)。
