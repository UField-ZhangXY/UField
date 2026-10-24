# 来源登记

## SRC-001：UField Production Runtime

- 类型：结构化 MCP 响应。
- 工具：ufield_runtime_get_ufield_runtime_core。
- 读取日期：2026-10-24（Asia/Shanghai）。
- 结果：成功返回 runtime_core、north_star、shared_runtime_dna。
- 对应条目：knowledge/ufield-core.md。
- 边界：只读接口；不提供共享知识库文件写入能力。

## SRC-002：UFieldGPT 主技能

- 类型：UField 本地实践与 AI 协作指导。
- 版本：Skill 0.15.2；内核 UField Core 0.1。
- 读取位置：skill://plugin_a64f92ff527c81918dd5694cf63fcec3/instructions/SKILL.md。
- 读取日期：2026-10-24（Asia/Shanghai）。
- 边界：技能地址仅在有对应插件访问权的环境中可读；未将其全部原文或附带资料复制到本仓库。

## SRC-003：UField PPT 技能（ufield-ppt）

- 类型：UField 本地实践——技能文档全文（SKILL.md + references×4 + scripts×3 + templates/v2×16）。
- 作者/发布者：张小永 / UField（技能由 AI 协助创建，agent_created 标记）。
- 版本：无显式版本号；SKILL.md 最后修改 2026-10-12。
- 稳定标识：本机用户级技能目录 `~/.workbuddy/skills/ufield-ppt/`。
- 读取日期：2026-10-24（Asia/Shanghai）。
- 实际读取范围：全部文本文件逐字节复制入库并 sha256 校验一致；SKILL.md 全文通读。
- 引用位置：fulltext/SRC-003-ufield-ppt/。
- 授权边界：创建者本人授权全文公开。13 项图片资产（logo、视觉底图等，约 14MB）**未随库**，保留于本地原路径。

## SRC-004：UField 微信公众号内容技能（ufield-wechat-article-codex-v1，Codex 版）

- 类型：UField 本地实践——技能文档全文（SKILL.md + references×4 + scripts×1 + agents×1）。
- 作者/发布者：张小永 / UField（Codex 版本，整理自原技能与编辑边界档案）。
- 版本：v1；SKILL.md 最后修改 2026-09-26。
- 稳定标识：E 盘归档 `E:\Z-UField｜AI\01-ChatGPT+Codex\02-技能与模板\skills\ufield-wechat-article-codex-v1\`。
- 读取日期：2026-10-24（Asia/Shanghai）。
- 实际读取范围：全部 7 个文本文件逐字节复制入库并 sha256 校验一致；SKILL.md 全文通读。
- 引用位置：fulltext/SRC-004-ufield-wechat-article/。
- 授权边界：创建者本人授权全文公开。references/sensitive-words.md 为编辑偏好（避敏指南），非平台官方规则，原文已自带此声明。

## SRC-005：进化教练方法论技能（evocoach-neigong，教练内功 v0.1）

- 类型：UField 本地实践——技能文档全文（SKILL.md + references×5）。
- 作者/发布者：张小永 / UField（agent_created 标记）。
- 版本：v0.1 垂直切片（第一练「核稳修炼」完整）；SKILL.md 最后修改 2026-10-15。
- 稳定标识：本机用户级技能目录 `~/.workbuddy/skills/evocoach-neigong/`。
- 读取日期：2026-10-24（Asia/Shanghai）。
- 实际读取范围：全部 6 个文本文件逐字节复制入库并 sha256 校验一致；SKILL.md 全文通读。
- 引用位置：fulltext/SRC-005-evocoach-neigong/。
- 授权边界：创建者本人授权全文公开。⚠️ 方法论蒸馏自「创问·进化教练第 55 期」课程（讲师 Zoran、Lisa），**非本人原创体系**；引用其概念时应注明课程来源，不得归于 Otto Scharmer 或 UField 创建者。教练方法不替代心理咨询与医疗。

新增来源需登记：稳定标识、作者或发布者、版本/日期、类型、实际读取范围、引用位置、公开授权边界。无法读取的来源标记“待核验”。
