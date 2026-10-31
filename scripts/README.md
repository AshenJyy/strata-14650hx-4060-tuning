# 工具使用

[返回首页](../README.md) · [配置说明](../docs/CONFIGURATION.md) · [测试方法](../docs/METHODOLOGY.md)

以下命令在仓库根目录执行，使用 Python 3 标准库，无需安装第三方 Python 包。

| 工具 | 需要运行模型 | 作用 |
|---|---|---|
| [verify-results.py](verify-results.py) | 否 | 核对导出哈希、正式汇总、数值验证与失败记录 |
| [make-tuned-config.py](make-tuned-config.py) | 否 | 从可用 r2 配置生成新的线程调优配置 |
| [benchmark.py](benchmark.py) | 是，服务需已启动 | 一次预热 + 三项流式生成测速 |

## 离线核查

```powershell
python scripts/verify-results.py
```

核查 299 项导出资料的哈希，重新计算正式生成 TPS、首字延迟和整体速度，核对 r2 补丁及保留的数值验证和失败记录。这是资料一致性检查，不是重新运行模型或 CPU 数值测试。哈希清单仅覆盖原导入资料，不含后来编写的文档和辅助脚本。

## 生成配置

```powershell
python scripts/make-tuned-config.py --base E:\Strata\install\working-r2.json --out E:\Strata\install\tuned-r2.json
```

输出必须是新文件；脚本只改变调度字段，不切换或启动服务。它不验证 CPU 编号和引擎版本，使用前阅读 [配置前提](../docs/CONFIGURATION.md)。生成文件会保留自己的认证，请放在仓库之外或 `local-configs/`。

## 独立测速

先启动待测的 Strata 服务。脚本读取环境变量：

| 变量 | 默认值 / 用法 |
|---|---|
| `STRATA_BASE_URL` | `http://127.0.0.1:8082`，不要附加 `/v1`；脚本同时访问 `/metrics` 和 `/v1/chat/completions` |
| `STRATA_API_KEY` | 本地服务启用认证时设置为自己的密钥；不写入仓库 |

```powershell
python scripts/benchmark.py --label baseline --output local-results/baseline-1.json
```

默认每项 256 token，先预热，再生成中文说明、Python 代码、JSON；脚本**不执行生成的代码**，也不切换配置。服务需为 8192 上下文容量、FP16 KV；输出路径不能已存在。`--tokens` 可设为 32–1024，改变长度后应单独报告，不能混入历史 256 token 对照。

按 A → B → B → A 比较时，每组先重启到相应配置，再分别运行一次脚本，使用独立结果文件。保持模型、输入、电源和背景程序一致；运行中不要让其他客户端调用同一服务，以免请求统计串入。

`local-results/` 已加入 Git 忽略规则。原实验程序位于 [archive/harness/](../archive/harness)，保留了当时环境的占位符；一般复测使用这里的独立工具。
