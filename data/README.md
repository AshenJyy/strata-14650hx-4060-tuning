# 数据与实验索引

[返回首页](../README.md) · [成绩解读](../docs/RESULTS.md) · [方法与限制](../docs/METHODOLOGY.md)

所有记录来自 2026-10-30 的同一台实验机器。下表按实验目录编号排列；目录时间是历史标识。筛选轮、分析计数器开启的轮次和正式对照各自保留，不混成同一组性能结论。

## 先看这些文件

| 文件 | 内容 |
|---|---|
| [final-results.json](final-results.json) | 主正式轮 + PGO 追加轮的合并视图，最终表格的数据来源 |
| [main-formal.json](main-formal.json) | 五组候选正序 / 逆序对照，每项 256 token |
| [pgo-confirmation.json](pgo-confirmation.json) | 普通 r3 与原 lookup 参数 PGO 的 ABBA 追加对照 |
| [r3/selection.json](r3/selection.json) | 最终采用 r2 调优配置的选择依据 |
| [export-manifest.json](export-manifest.json) | 299 项导出资料的原始 / 发布 SHA256 |

顶层正式文件是方便阅读的汇总入口，原始会话仍保存在下面的实验目录，构成可追溯关系。它们不是额外重复跑出来的样本。

## r2 阶段

| 原始结果 | 每项 token | 类型 / 内容 |
|---|---:|---|
| [124028](r2/experiments/20261030-124028/results.json) | 256 | r1 性能分析采样 |
| [124800](r2/experiments/20261030-124800/results.json) | 256 | r1 / r2、任务数和 MTP 筛选 |
| [125657](r2/experiments/20261030-125657/results.json) | 256 | **r1 / r2 正式 ABBA**：18.60 → 19.55 TPS |

## r3 阶段

| 原始结果 | 每项 token | 类型 / 内容 |
|---|---:|---|
| [131146](r3/experiments/20261030-131146/results.json) | 256 | r2 性能分析采样 |
| [132053](r3/experiments/20261030-132053/results.json) | 256 | r3 激活展开与复用筛选，包含分析版本 |
| [132659](r3/experiments/20261030-132659/results.json) | 256 | 驻留内存、直接读取与等待策略 |
| [134017](r3/experiments/20261030-134017/results.json) | 128 | P / E 核布局、超线程、主线程和 PGO 筛选 |
| [134656](r3/experiments/20261030-134656/results.json) | 128 | 任务数等筛选；**spec=0 加载失败，保留此前成功会话** |
| [135315](r3/experiments/20261030-135315/results.json) | 128 | MTP、spec、缓存和 r2 调优配置筛选 |
| [135735](r3/experiments/20261030-135735/results.json) | 128 | lookup chain、成本参数对照 |
| [140122](r3/experiments/20261030-140122/results.json) | 256 | **主正式轮**，五组候选正序 / 逆序 |
| [141256](r3/experiments/20261030-141256/results.json) | 256 | **PGO 追加轮**，ABBA |

每个实验目录还保留启动切换日志与引擎日志。`results.json` 内包含提示、生成内容、使用量、耗时和资源采样；候选名称对应 [历史配置](../configs/README.md)。128 token 的高值不能代替 256 token 正式成绩。

## 构建与一致性证据

| 资料 | 内容 |
|---|---|
| [builds/](builds) | r1、r2、r3 与 PGO 的历史构建和文件哈希清单 |
| [r2/model-integrity.json](r2/model-integrity.json)、[r3/model-integrity.json](r3/model-integrity.json) | 模型文件大小与完整哈希 |
| [r2/logs/integrated-check-640.log](r2/logs/integrated-check-640.log) | r2 集成逐位检查 |
| [r3/parity.json](r3/parity.json)、[r3/parity-r3pgo.json](r3/parity-r3pgo.json) | r3 / PGO 数值验证结果 |
| [r3/pgo-training.json](r3/pgo-training.json) | PGO 采样与中断说明 |
| [r3/rejected-configs.json](r3/rejected-configs.json) | spec=0 失败原因和后续测试方案 |
| [r2/logs/](r2/logs)、[r3/logs/](r3/logs) | 构建、筛选、性能分析及验证日志 |

## 脱敏与核查

认证字段已移除，私有目录替换为 `${STRATA_ROOT}` / `${WORKSPACE}`；数值、提示、生成文本、失败和顺序保留。历史构建状态不表示其他机器已经通过验证。

在仓库根目录运行 `python scripts/verify-results.py` 可离线核对哈希与统计。清单覆盖导入资料，不覆盖新写的说明和辅助脚本；它用于检测内容变化，不提供外部签名认证。原始 PGO 计数器已清理，不能逐字节复现当时的 PGO 二进制。
