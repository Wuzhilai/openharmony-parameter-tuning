# 环境与复现

运行环境为 Ubuntu 22.04，ARM Cortex-M4 交叉工具链、QEMU 6.2、Python 3.10、NumPy 1.21.5、SciPy 1.8.0、scikit-learn 0.23.2。完整原始包版本在 `evidence/environment.json`。Ubuntu/WSL 版本不同应记录差异，不保证 ELF 文件逐字节相同。

## 安装与只读核验

在独立 Ubuntu 环境克隆仓库后进入根目录。以下安装会修改该 Linux 环境，建议使用专门的研究环境：

```bash
sudo apt-get update
sudo apt-get install -y build-essential gcc-arm-none-eabi libnewlib-arm-none-eabi qemu-system-arm git python3-numpy python3-scipy python3-sklearn python3-matplotlib
python3 scripts/independent_audit.py
```

该检查直接读取 gzip 原始日志，对应次数和散列、每条分数、统计区间、种子分离、搜索预算、源文件和镜像逐项核验。只生成/更新 `audit/independent_checks.json`，不重新训练。仓库含四份必要上游源码及许可证，不必先联网拉取源码。

## 演示与归档镜像复测

```bash
python3 scripts/demo.py
python3 scripts/recheck_runtime.py
```

演示和复测使用 `images/deployment/OHOS_Image`，在 `audit/rerun/` 建立独立运行目录。后一个命令重新编译主机端 C++ 模型，运行 128 组一致性检查、60 组自动闭环、120 条消融及异常恢复测试。通过才写 `audit/runtime_checks.json`。它依赖本仓库原始 `models.pkl`，不要用来源不明的 pickle 文件替换，版本变更可能需要重训。

## 从公开源码构建

```bash
python3 scripts/build_kernel.py
python3 scripts/smoke_boot.py
```

期待 `MID_BOOT_OK actual_liteos_m=1`。产物位于忽略提交的 `build/`。研究补丁通过 `prepare_instrumentation.py` 从上游源文件生成覆盖文件，上游源码不原地修改。当前两份历史镜像只供复核，不被重新构建覆盖。

手动串口启动：

```bash
qemu-system-arm -M mps2-an386 -cpu cortex-m4 -nographic -monitor none -serial stdio -kernel build/OHOS_Image -icount shift=0,align=off,sleep=off
```

出现 `MID_READY` 后输入一行命令：

```text
S 42 8 8 1000 500 1
M 42 4000 1 8 0 1
A 50000 8 8 40000 0 1
B 50000 4000 1 40000 0 1
```

S/M 为固定参数；A/B 让客体执行默认预采样、C++ 推荐及正式运行。最后一列为探针开关。q/floor 为微秒控制值，minalloc/split 为字节。QEMU 可用 Ctrl-A 后 X 退出。

## 完整重新训练

**在另一个克隆目录运行以下流程**：它会覆盖该目录中的 results、模型和快照。不要将新结果与本次归档数字混合。它复现的是历史 v1 负载，包括审计指出的内存序列局限；修正生成器必须提升协议版本并重新做整个评估。

```bash
python3 scripts/build_kernel.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -u scripts/run_study.py
python3 scripts/export_model.py
g++ -O2 product/model.cpp product/model_cli.cpp -o build/model_cli
python3 scripts/build_kernel.py
python3 scripts/verify_deployment.py
python3 scripts/supplementary_tests.py
python3 scripts/analyze_results.py
python3 scripts/finalize_evidence.py
python3 scripts/audit_delivery.py
```

原 `audit_delivery.py` 用于这一完整流程生成的未压缩日志和构建覆盖文件。公开包的快速检查以 `independent_audit.py` 为入口。更新归档时需重新生成 gzip 原始日志清单和发布清单，不能沿用旧审计的 PASS。

## 证据层次

- `research/`：四个上游固定提交的源码快照，保留各自许可。`source_lock.json` 另记录两个仅用于早期阅读的仓库，它们不参与构建。
- `images/study/`：正式采集时的产品源码、镜像及源文件散列。
- `images/deployment/`：模型导出后的部署源码、镜像及散列。
- `results/`：原始阶段数据与历史核验，供复算。
- `evidence/*.gz`：完整日志的无损 gzip，未删分配失败输出；解压散列见 `raw_manifest.json`。
- `audit/`：本次独立审计与新运行核验；`audit/rerun/` 是本地重跑区，不上传 Git。

原构建清单的绝对编译命令和 map 文件未发布，源文件、协议和 ELF 散列保留。ELF 内调试信息可能仍含研究目录名称；没有把原始二进制重新标记成脱敏后同哈希文件。项目代码和报告不包含成员手机号、个人邮箱、签名和财务凭证。
