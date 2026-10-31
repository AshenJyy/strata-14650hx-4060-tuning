# 构建和使用

[返回首页](../README.md) · [配置说明](CONFIGURATION.md) · [补丁关系](../patches/README.md)

此仓库发布补丁和记录，不提供模型或预编译程序。已有可用 Strata 安装的人可以先比较线程配置；要复现本次 r2 成绩，需要相同源码和编译设置。

## 源码与依赖

使用 x64 MSVC 开发者 PowerShell，确保 `cl`、Git、CMake、Ninja 可用，并安装完整 CUDA Toolkit。原实验为 MSVC 14.44.35207 / CUDA 13.0.48，其他版本没有验证。以下 `E:\StrataBuild` 是示例工作目录，不要覆盖现有部署。

```powershell
git clone https://github.com/AshenJyy/strata-14650hx-4060-tuning.git E:\StrataBuild\tuning
git clone https://github.com/Niko1221/Strata.git E:\StrataBuild\source
git -C E:\StrataBuild\source checkout --detach 870aedd9e1ebe1c91f94da93b59af17729f6c5c0
git -C E:\StrataBuild\source apply --check E:\StrataBuild\tuning\patches\r2.patch
git -C E:\StrataBuild\source apply E:\StrataBuild\tuning\patches\r2.patch
git clone https://github.com/ggml-org/llama.cpp.git E:\StrataBuild\llama.cpp
git -C E:\StrataBuild\llama.cpp checkout --detach 3cf03257f219afbe7334045ff7c6a06ac68c627d

cmake -S E:\StrataBuild\source -B E:\StrataBuild\build -G Ninja `
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl `
  "-DCMAKE_CUDA_COMPILER=$env:CUDA_PATH/bin/nvcc.exe" "-DCUDAToolkit_ROOT=$env:CUDA_PATH" `
  -DCMAKE_CUDA_ARCHITECTURES=89 -DSTRATA_ENABLE_CUDA=ON `
  -DSTRATA_14650HX_4060=ON -DSTRATA_PORTABLE=ON `
  -DSTRATA_BUILD_TESTS=OFF -DSTRATA_WINDOW_MAX_T=8 `
  -DSTRATA_GGML_DIR=E:/StrataBuild/llama.cpp
cmake --build E:\StrataBuild\build --target strata --parallel 6
```

`r2.patch` 是完整补丁，已包含 r1；`r2-only.patch` 才是在 r1 上继续应用的差量。`r3-experimental.patch` 也是从干净上游提交开始的完整补丁；不是 r2 的追加补丁。完整对应关系见 [补丁索引](../patches/README.md)。实验 PGO 数据已经清理，需要重新采样，不能照搬旧路径声称复现了原 PGO 二进制。

将新的 `strata.exe`、同一次构建产生的 `strata_kq.dll` 和对应 CUDA 13 运行 DLL 放入独立发布目录，再从已有可用安装配置中指定 `exe`、`cwd`、`lib_dirs`。原部署使用已有 CUDA 13 cuBLAS 运行库；不要从这个仓库寻找 DLL。使用原有 Strata Terminal/Python 服务、模型、tokenizer、expert profile 与 MTP rt 目录。

## 生成调优配置

先按 [配置说明](CONFIGURATION.md) 核对 CPU 的逻辑编号。此脚本按本次 8P+8E、24 逻辑处理器布局设置亲和性，不能直接适用于所有同品牌 CPU。下面的 Python 命令在本调优仓库根目录执行。

```powershell
python scripts/make-tuned-config.py --base E:\Strata\install\working-r2.json --out E:\Strata\install\tuned-r2.json
```

输入必须是你已有的、可运行的 r2 配置。脚本保留模型路径、引擎路径、认证和其他模型参数，仅修改工作线程/主线程选项及 UMWAIT 等待策略，写入新文件；不切换正在运行的服务。使用 Strata 的配置管理选择生成的新配置，先验证加载与响应，再测速。

[configs/tuned.example.json](../configs/tuned.example.json) 是此次完整配置的脱敏副本；`${STRATA_ROOT}` 必须替换为实际目录。[configs/archive/](../configs/archive) 记录所有候选，包含已经弃用的路径和参数，不是安装器。

## 性能复测

离线检查保存结果：`python scripts/verify-results.py`。这不会启动模型。

独立复测脚本使用已启动的本机服务，密钥从 `STRATA_API_KEY` 环境变量读取，可通过 `STRATA_BASE_URL` 修改地址（不附加 `/v1`）。脚本不切换配置，也不执行模型返回的代码；完整参数见 [脚本说明](../scripts/README.md)。

```powershell
# 在当前会话中设置你自己的 STRATA_API_KEY，不要将密钥写入仓库。
python scripts/benchmark.py --label baseline --output local-results/baseline-1.json
```

比较两套配置时采用 A → B → B → A；每组先重启到目标配置，然后运行脚本。脚本在每组内部完成一次预热和三项正式请求，默认每项 256 token。保持电源、背景程序、输入和模型设置一致。更多轮次可以评估波动，但不要将新测量冒充仓库中的历史结果。
