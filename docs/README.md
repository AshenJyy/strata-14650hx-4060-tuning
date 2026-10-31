# 仓库导览

[返回首页](../README.md)

## 阅读顺序

| 目的 | 阅读顺序 |
|---|---|
| 看结论 | [性能结果](RESULTS.md) → [测试方法和限制](METHODOLOGY.md) |
| 复现部署 | [构建](BUILD.md) → [配置](CONFIGURATION.md) → [脚本使用](../scripts/README.md) |
| 审阅代码 | [补丁关系](../patches/README.md) → [r2 完整补丁](../patches/r2.patch) → [验证资料](../data/README.md) |
| 追溯实验 | [数据索引](../data/README.md) → [历史配置](../configs/README.md) → [原测试程序](../archive/README.md) |

## 资料结构

```text
README.md                       项目概览与最终结论
docs/
  BUILD.md                      固定源码版本与构建步骤
  CONFIGURATION.md              核心编号、线程参数、精度和服务设置
  RESULTS.md                    完整正式成绩与选型理由
  METHODOLOGY.md                 测量定义、失败尝试、验证边界
patches/                        完整补丁与差量补丁
configs/
  tuned.example.json            最终配置的脱敏副本
  archive/r2/、archive/r3/       当时所有候选的配置
scripts/                        可独立使用的 Python 工具
data/
  final-results.json            两轮正式结果的合并视图
  main-formal.json              主正式轮
  pgo-confirmation.json         PGO 追加轮
  builds/                       历史构建清单
  r2/、r3/                      原始会话、日志和验证记录
  export-manifest.json          299 项导出资料的哈希
archive/
  harness/                      原实验程序
  patches/                      换行修正前的 r2 差量补丁
```

## 文件的使用范围

- **使用入口**：`scripts/` 与构建、配置文档。脚本的作用和前提见 [脚本说明](../scripts/README.md)。
- **脱敏示例**：`configs/tuned.example.json` 中的 `${STRATA_ROOT}` 需要替换；认证字段已移除。优先从自己已有的可用配置生成新配置。
- **历史证据**：`data/`、`configs/archive/` 和 `archive/` 保留当时的路径占位符、失败与未采用方案。构建清单中的验证状态只描述原实验。

历史资料的路径和内容保持稳定，便于原链接和哈希核查继续工作。新增结果应放到独立实验目录，注明硬件、模型、配置与测试顺序，不覆盖原结果。个人复测默认写入 Git 忽略的 `local-results/`。
