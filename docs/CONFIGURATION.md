# 最终配置说明

[返回首页](../README.md) · [构建步骤](BUILD.md) · [配置文件索引](../configs/README.md)

本次部署采用 **r2 引擎 + 8P8E16T**。配置以已有、可运行的 r2 安装为前提；模型、tokenizer、专家包、MTP rt 与运行库需已就绪。

## 核心与线程

这台 i7-14650HX 的 P 核逻辑编号是 0–15，相邻两个编号属于同一物理核心；E 核为 16–23。

| 用途 | 逻辑编号 | 线程数 |
|---|---|---:|
| 主线程 | `0` | 1 |
| 其余 P 核工作线程 | `2,4,6,8,10,12,14` | 7 |
| E 核工作线程 | `16-23` | 8 |

合计 15 个工作线程 + 1 个主线程，即 8P+8E、每个物理核心一个参与线程。**`--pool-workers 15` 不表示总共只用 15 个线程。** 其他机器须先核对逻辑编号；不能仅按 CPU 品牌照搬。

```text
--pool-cores 2,4,6,8,10,12,14,16-23
--pool-workers 15
--pool-affinity all
--host-core first
--pool-tasks 0
STRATA_POOL_UMWAIT=10000
STRATA_POOL_UMWAIT_ESC=20000
```

## 保持的模型设置

| 项目 | 设置 |
|---|---|
| 模型 | `Qwen3.8-Flash-Next-Gyro-S-abliterated-TQ1_0.gguf` |
| 专家量化 | GU=TQK6、down=TQK7；文件名的 TQ1_0 不替代实际类型说明 |
| 层与专家 | 48 层 × 512 专家，不剪枝、不跳过路由专家 |
| 路由选项 | `STRATA_ROUTE_TAIL_SKIP=0`、`STRATA_ROUTE_PRIOR=0` |
| 上下文 / KV / 并发 | 8192 / FP16 / 1 |
| 推测设置 | `--spec 4 --spec-min-p 0.5`，保留原 MTP rt |

运行时 lookup 可扩展窗口，所以 `/metrics` 中的 `spec` 可能显示 6；MTP cap 为 4。这与配置中的 `--spec 4` 并不矛盾。

这份完整配置和实测只覆盖上述 Gyro-S 模型。Qwen3.6-35B-A3B 等模型的加载、MTP 和量化路径需要单独配置；不能直接套用该示例或假定有同样收益。

## 从已有安装生成配置

在仓库根目录执行：

```powershell
python scripts/make-tuned-config.py --base E:\Strata\install\working-r2.json --out E:\Strata\install\tuned-r2.json
```

脚本保留模型、认证、引擎路径与其他参数，只替换线程 / 主线程选项和两项 UMWAIT 环境设置。输出文件必须尚不存在；脚本不会覆盖输入，不会启动或切换服务，也不会自动检查 CPU 编号或输入引擎版本。

使用 Strata 的配置管理选择新文件。新构建的 `exe`、`cwd`、`lib_dirs` 必须指向同一套运行库，具体见 [构建说明](BUILD.md)。

## 路径、端口与认证

[完整示例](../configs/tuned.example.json) 是当时配置的脱敏副本。`${STRATA_ROOT}` 是文档占位符，需要替换成实际根目录（本次为 `E:\Strata`）；脚本不会替你展开示例中的占位符。模型、专家包、MTP 和构建文件可继续放在 E 盘。

示例监听 `127.0.0.1:8082`，OpenAI 兼容接口基址为 `http://127.0.0.1:8082/v1`，模型 ID 为 `qwen3.8-flash-next-gyro-s-abliterated`。端口需按本机占用情况配置。ECPA 等客户端使用同一基址、模型 ID 和本地服务的认证值。

示例已移除 API 密钥。已启用认证时，这个密钥用于客户端访问本地服务，并不意味着需要购买云端 API；从已有配置生成新文件会保留自己的认证。实际配置可能含密钥，应保存在部署目录或 Git 忽略的 `local-configs/`。

## 核查与复测

核对启动后的核心布局、模型、上下文、KV 和推测设置。历史资料可用 `python scripts/verify-results.py` 离线核查；实际性能复测另见 [脚本说明](../scripts/README.md)，不会由配置生成脚本自动触发。
