# 历史资料

[返回首页](../README.md) · [数据索引](../data/README.md)

| 路径 | 保留原因 |
|---|---|
| [harness/r2/](harness/r2) | r2 内核检查、配置切换和实验调度原程序 |
| [harness/r3/](harness/r3) | r3 / PGO 检查、资源采样和实验调度原程序 |
| [harness/strata_abliterated_bench.py](harness/strata_abliterated_bench.py) | 原流式请求和监控工具，也含更早的能力测试逻辑 |
| [patches/r2-only-original.patch](patches/r2-only-original.patch) | r2 差量补丁的原始 CRLF 字节，用于哈希追溯 |

这些是实验记录，原本机路径已替换为 `${STRATA_ROOT}` / `${WORKSPACE}`。路径、构建产物和部署布局需要重新配置；其中切换脚本会操作服务，不作为当前安装入口。

本仓库 r2 / r3 数据只使用原工具中的流式请求和监控部分；工具存在能力测试代码，不代表本次执行过能力评测。一般复测使用 [scripts/](../scripts/README.md)，最终引擎构建使用 [r2 完整补丁](../patches/README.md)。

历史模型、二进制、工具链和 PGO 计数器不在仓库中。实验记录保留失败和未采用方案，以说明最终选择；不会因某次成绩更慢而删除。
