---
name: harmony-article-writing
description: 基于真实鸿蒙三方库适配证据整理征文素材、提纲、章节要点并进行局部改写/润色。适用于“根据这次真实适配整理文章结构”“把我的开发记录映射到文章章节”“帮我润色这一段适配说明”等任务。受活动 AI 使用规则约束，不一键代写全部或大部分正文，不虚构问题、实现、测试、真机或截图经历。
---

# Harmony Article Writing

## 目标

回答：**“如何把已经真实完成并验证的适配过程，整理成作者可以继续撰写的高质量技术文章？”**

本 Skill 的定位是：

- 整理真实证据；
- 形成文章素材包；
- 生成提纲和章节写作提示；
- 把作者已提供的内容做局部改写、压缩、扩展或润色；
- 检查章节是否有对应事实来源；
- 在写作过程中持续遵守活动规则。

本 Skill **不是整篇文章自动代写器**。

## AI 使用硬边界

活动规则读取：

```text
resources/article-rules.yaml
```

其中 `ai-not-majority-author` 是硬规则：AI 不得生成文章全部或大部分内容。

因此本 Skill 必须遵守：

1. 不从零生成完整 800+ 字参赛正文；
2. 不一次性补齐作者尚未提供的大部分实践叙述；
3. 不把提纲、占位提示扩写成伪装的完整参赛文章；
4. 可以对作者已经写出的具体段落做局部改写/润色；
5. 可以根据真实证据生成短小事实摘要、表格、章节要点和连接句；
6. 文章主体中的个人实践叙述、真实问题、失败尝试、关键技术取舍和经验总结必须由作者提供实质内容；
7. 如果用户要求“一键生成整篇参赛文章”，应说明活动 AI 规则边界，并改为提供素材包 + 提纲 + 分章节写作提示，而不是直接代写大部分正文。

## 前置门禁

进入文章写作辅助前，优先要求存在：

```text
Validation Gate:
phase = ARTICLE_PREP
decision = PROCEED
```

如果 Validation Gate 仍为 `VALIDATION/BLOCKED`：

- 不开始撰写适配成果文章；
- 先列出缺失的真实技术证据；
- 不用文字补全未完成的测试、真机或截图。

## 单一事实输入

文章事实应优先来自：

1. candidate qualification artifact；
2. Validation Gate artifact；
3. 实际代码 diff / commit；
4. 构建日志；
5. 测试报告；
6. Demo；
7. HarmonyOS/OpenHarmony 实体设备运行记录；
8. 真实截图；
9. 作者记录的问题、失败尝试、决策和 API 行为变化。

可以先运行：

```text
scripts/article/build_article_material_pack.py
```

生成统一 Article Material Pack。

## Article Material Pack

Material Pack 至少保留：

- `framework`
- `candidate`
- `qualification_status`
- `validation_status`
- `development_summary`
- `problems`
- `decisions`
- `api_changes`
- `source_refs`
- `validation_evidence`
- `section_plan`
- `material_gaps`
- `ai_boundary`

其中：

```text
ai_boundary.full_article_generation_allowed = false
```

必须保持为硬约束。

如果 `material_gaps` 非空：

- 明确告诉作者哪些内容需要补真实记录；
- 不为了让文章结构完整而自行编造。

## 推荐文章结构

以下是默认结构，不是必须逐字使用的模板：

### 1. 标题

标题必须明确框架/技术栈，例如：

```text
Flutter xxx 三方库 HarmonyOS 适配实践
RN xxx 三方库鸿蒙适配实战
ArkTS xxx 三方库迁移与适配实践
C/C++ xxx 库 OpenHarmony 适配记录
```

标题中的技术栈必须与实际 framework variant 一致。

### 2. 开头社区引导

从 `resources/frameworks.yaml` 获取：

```text
community.name
community.organization
```

使用：

```text
欢迎加入{community.name}：【{community.organization}】
```

不要硬编码过期社区链接。

### 3. 选库背景与必要性

来源：qualification。

作者应说明：

- 业务用途；
- 为什么值得适配；
- 如何确认确实需要适配；
- 如何完成活动 required 去重。

不要把评分模型或模型推荐理由当成作者实际选库经历。

### 4. 实际环境与适配范围

来源：真实开发环境和实现记录。

至少说明：

- 框架/技术栈；
- HarmonyOS/OpenHarmony SDK；
- 实际设备；
- 适配库版本；
- 本次适配覆盖和不覆盖什么。

版本遵守 `article-rules.yaml` 的 current/latest policy；发生兼容版本回退时必须说明原因。

### 5. 核心适配实现

来源：真实 diff/commit。

优先讲：

- 平台差异；
- API/接口映射；
- 生命周期、权限、线程、异步或系统能力差异；
- 行为对齐；
- 关键代码为什么这样改。

不得仅凭最终代码反推一个并未真实发生的开发过程。

### 6. 问题、尝试与技术取舍

这是必须高度依赖作者原始记录的章节。

只有在 `development_notes.problems` / `decisions` 或其他真实记录存在时才整理。

如果没有记录：

- 给作者问题清单，提示补充；
- 不生成“常见问题”冒充本次实际问题；
- 不编造错误日志、失败方案或调试过程。

### 7. Demo、测试和真机验证

来源：Validation Artifact。

只使用已经 `VERIFIED` 的事实。

文章应把：

- Demo 场景；
- 关键测试；
- 实体设备运行；
- 成功截图；

与对应证据关联起来。

截图存在本身不能由本 Skill推导出真机验证事实，必须以 Validation Gate 为准。

### 8. 总结

作者应自己提供主要经验和技术判断。

本 Skill可以：

- 帮助压缩作者已写总结；
- 组织要点；
- 检查是否与前文事实一致。

不得从零替作者生成大段“心得体会”。

### 9. 结尾社区引导

再次使用当前 framework community 的规范引导语。

## 局部写作模式

当用户提供自己已经写好的段落时，可以执行：

- 专业化表达；
- 技术术语统一；
- 消除口语/歧义；
- 调整篇章顺序；
- 压缩重复内容；
- 将已有事实整理成表格；
- 在不增加新事实的前提下补充必要连接句。

改写时不得增加原材料没有支持的：

- 错误现象；
- 性能数据；
- API 行为；
- 测试结果；
- 设备型号；
- 版本号；
- 截图描述；
- 官方结论。

## 缺失事实标记

缺少事实时使用明确占位提示，例如：

```text
[作者补充：实际使用的设备型号]
[作者补充：这里记录真实遇到的问题与错误日志]
[作者补充：对应 commit/diff]
[作者补充：真机截图]
```

占位提示不是最终文章内容，提交前必须由作者补齐或删除。

## 品牌与链接

写作过程持续遵守：

- 代码托管品牌使用 `AtomGit`；
- 最终文章禁止出现 `GitCode` 品牌或链接；
- 社区名/链接来自 `resources/frameworks.yaml`；
- CodeArts 仅作为活动推荐项处理；没有当前活动提供的推荐链接时，不自行编造。

## 与 Article Check 的闭环

每次形成一个可检查的草稿版本后，应交给：

```text
harmony-article-check
```

流程：

```text
作者真实素材
    ↓
harmony-article-writing
    ↓
草稿/局部修订
    ↓
harmony-article-check
    ↓
问题清单
    ↓
作者补充或 writing 局部修订
    ↓
重新检查
```

writing Skill 不能自己宣布“文章已经合规”。

## 输出模式

根据输入完整度选择以下一种，不默认输出整篇文章：

### `MATERIAL_GAPS`

真实资料不足时：

- 缺失事实；
- 为什么阻塞；
- 作者应该提供什么。

### `OUTLINE`

资料具备但作者尚未写正文：

- 标题候选；
- 章节结构；
- 每节证据引用；
- 作者写作提示；
- 截图放置建议。

### `SECTION_ASSIST`

用户正在写某一节：

- 对该节已有文本做局部改写；
- 保留事实边界；
- 标记缺失证据。

### `REVISION_PLAN`

已有完整草稿和 article-check 结果：

- 按 blocking/manual/external rule 分类；
- 只修改可由文本解决的问题；
- 外部指标和人工确认继续保留，不虚构通过。

## 红线

- 不一键生成全部或大部分参赛正文。
- 不虚构适配过程。
- 不虚构问题/失败尝试。
- 不虚构构建、测试和真机运行结果。
- 不虚构截图内容。
- 不为了达到 800 字而灌入没有事实依据的内容。
- 不预测重复率或 CSDN 质量分。
- 不把 AI 写作本身当成原创性证明。
- 不绕过 `harmony-article-check` 宣布文章可发布。
