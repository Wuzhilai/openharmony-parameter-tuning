# 第三方来源与发布说明

本仓库包含 OpenHarmony 上游代码和研究修改。公开不表示企业合作、官方背书或商业 HarmonyOS 产品适配。

| 目录 | 来源 | 保留的许可 |
|---|---|---|
| `research/kernel_liteos_m` | OpenHarmony/kernel_liteos_m | 目录内 LICENSE 及文件头，BSD 三条款 |
| `research/device_qemu` | OpenHarmony/device_qemu | 目录内 LICENSE 及各组件文件头，含 Apache-2.0 等 |
| `research/cmsis` | OpenHarmony/third_party_cmsis | LICENSE.txt、README.OpenSource 及文件头 |
| `research/bounds_checking_function` | OpenHarmony/third_party_bounds_checking_function | LICENSE、README.OpenSource 及文件头 |

准确提交和仓库地址见 `evidence/source_lock.json`。源码快照未包含各仓库 `.git` 历史，版权与许可证文件保留。内核研究修改通过 `evidence/kernel_research.patch` 展示。

ARM 镜像含工具链运行库，相关安装包版权信息保存在 `third_party_licenses/`。各文件遵循其自身许可，不用项目统一声明覆盖第三方权利。

本次发布没有为项目自编部分新增 MIT/Apache 等统一授权。该部分的后续使用和再许可由项目权利人决定。团队需要正式开源许可时，应先确定学校、成员和资助方的权利安排。

公开内容不含原申报表、通讯录、签名、经费底表、WSL 磁盘、下载缓存、旧仿真包或过时申报 PPT。审计对技术事实负责，成员历史贡献、行政批准和资金执行以实际材料为准。
