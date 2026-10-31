# 配置文件

[返回首页](../README.md) · [参数说明](../docs/CONFIGURATION.md)

| 路径 | 用途 |
|---|---|
| [tuned.example.json](tuned.example.json) | 最终采用的 r2 + 8P8E16T 完整配置，已脱敏 |
| [archive/r2/](archive/r2) | r1 / r2 对照、任务数与 MTP 筛选配置 |
| [archive/r3/](archive/r3) | r3、PGO、线程、内存和推测筛选配置，也包含 r2 对照 |
| [archive/r3/r2-tuned16.json](archive/r3/r2-tuned16.json) | 正式轮中最终采用方案的历史配置 |

优先用 [配置生成工具](../scripts/make-tuned-config.py) 从已有可用 r2 配置生成新文件。完整示例中的 `${STRATA_ROOT}` 需自行替换，认证字段已经移除，不能当成直接可启动的安装包。

`archive/` 保留实验原貌：其中有已经弃用的引擎目录和不适合部署的候选。目录名 r3 表示实验阶段，不表示其中所有配置都使用 r3 引擎。具体候选与成绩的对应关系见 [数据索引](../data/README.md)。

实际路径和密钥保存在仓库之外，或根目录下 Git 忽略的 `local-configs/` 中。
